# -*- coding: utf-8 -*-
"""
MobaXterm session launcher.

This plugin launches your MobaXterm bookmark sessions from Flow Launcher.
"""

import os
import re
import subprocess

from flowlauncher import FlowLauncher, FlowLauncherAPI

try:
    import winreg
except ImportError:  # Allows importing the module outside Windows (tests)
    winreg = None


ICON = "images/MobaXterm.ico"
DEFAULT_MOBA_FOLDERS = [
    r"%ProgramFiles(x86)%\Mobatek\MobaXterm",
    r"%ProgramFiles%\Mobatek\MobaXterm",
]
DEFAULT_INI_LOCATIONS = [
    r"%APPDATA%\MobaXterm\MobaXterm.ini",
    r"%USERPROFILE%\Documents\MobaXterm\MobaXterm.ini",
]
BOOKMARK_SECTION = re.compile(r"^Bookmarks(_\d+)?$", re.IGNORECASE)
SHARED_SECTION = re.compile(r"^SharedSessions\d*$", re.IGNORECASE)
RESERVED_KEYS = {"subrep", "imgnum"}


class MobaXtermError(Exception):
    """Error with a user friendly title and subtitle."""

    def __init__(self, title, subtitle=""):
        super().__init__(f"{title}: {subtitle}")
        self.title = title
        self.subtitle = subtitle


def expand(path):
    """Expand environment variables and strip quotes/whitespace."""
    return os.path.expandvars(str(path or "").strip().strip('"'))


def read_ini_lines(path):
    """Read an ini file trying the encodings MobaXterm may use."""
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            with open(path, encoding=encoding) as ini_file:
                return ini_file.read().splitlines()
        except UnicodeDecodeError:
            continue
    with open(path, encoding="latin-1") as ini_file:
        return ini_file.read().splitlines()


def parse_ini(path):
    """Parse a MobaXterm ini as an ordered list of (section, [(key, value)]).

    configparser is not used because MobaXterm files contain duplicated keys,
    '%' characters and other content it does not handle.
    """
    sections = []
    current = None
    for line in read_ini_lines(path):
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = (line[1:-1].strip(), [])
            sections.append(current)
        elif current is not None:
            key, _, value = line.partition("=")
            current[1].append((key.strip(), value.strip()))
    return sections


def describe_session(value):
    """Extract 'user@host:port' from a session definition when possible."""
    fields = value.split("%")
    if len(fields) < 2 or not fields[0].startswith("#"):
        return ""
    host = fields[1].strip()
    port = fields[2].strip() if len(fields) > 2 else ""
    user = fields[3].strip() if len(fields) > 3 else ""
    if not host:
        return ""
    target = f"{user}@{host}" if user else host
    return f"{target}:{port}" if port.isdigit() else target


def read_sessions(path, source="local"):
    """Return the bookmark sessions found in a MobaXterm ini/mxtsessions file."""
    sessions = []
    for section, entries in parse_ini(path):
        if not BOOKMARK_SECTION.match(section):
            continue
        folder = ""
        for key, value in entries:
            if key.lower() == "subrep":
                folder = value
                break
        for key, value in entries:
            if not key or key.lower() in RESERVED_KEYS:
                continue
            sessions.append({
                "name": key,
                "folder": folder,
                "bookmark": f"{folder}\\{key}" if folder else key,
                "target": describe_session(value),
                "source": source,
            })
    return sessions


def shared_session_files(sections):
    """Locate the shared session files referenced in MobaXterm.ini."""
    files = []
    for section, entries in sections:
        if not SHARED_SECTION.match(section):
            continue
        candidates = [expand(v) for _, v in entries
                      if v.lower().endswith((".mxtsessions", ".ini"))]
        # Fallback to the historical position (5th entry of the section)
        if not candidates and len(entries) > 4:
            candidates = [expand(entries[4][1])]
        files.extend(c for c in candidates if os.path.isfile(c))
    return files


class MobaLauncher(FlowLauncher):
    """MobaXterm session launcher."""

    # ----------------------------------------------------------------- settings
    @property
    def settings(self):
        if hasattr(self, "rpc_request") and isinstance(self.rpc_request, dict):
            return self.rpc_request.get("settings") or {}
        return {}

    def get_setting(self, name):
        value = self.settings.get(name, "")
        return value.strip() if isinstance(value, str) else ""

    # -------------------------------------------------------------- discovery
    def find_executable(self):
        """Return the MobaXterm executable (installed or portable)."""
        configured = expand(self.get_setting("moba_path"))
        if configured.lower().endswith(".exe") and os.path.isfile(configured):
            return configured

        folders = [configured] if configured else []
        folders += [expand(f) for f in DEFAULT_MOBA_FOLDERS]
        for folder in folders:
            if not os.path.isdir(folder):
                continue
            preferred = os.path.join(folder, "MobaXterm.exe")
            if os.path.isfile(preferred):
                return preferred
            for name in sorted(os.listdir(folder)):
                if name.lower().startswith("mobaxterm") and name.lower().endswith(".exe"):
                    return os.path.join(folder, name)

        raise MobaXtermError(
            "MobaXterm executable not found",
            f"Check the MobaXterm path in the plugin settings ({configured or 'empty'})",
        )

    def find_ini(self, exe_path):
        """Return the MobaXterm.ini path used by the user."""
        candidates = [expand(self.get_setting("ini_path"))]
        if winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                    r"Software\Mobatek\MobaXterm") as key:
                    candidates.append(expand(winreg.QueryValueEx(key, "LastIniPath")[0]))
            except OSError:
                pass
        candidates.append(os.path.join(os.path.dirname(exe_path), "MobaXterm.ini"))
        candidates += [expand(p) for p in DEFAULT_INI_LOCATIONS]

        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise MobaXtermError(
            "MobaXterm.ini not found",
            "Set the MobaXterm.ini path in the plugin settings",
        )

    def load_sessions(self, ini_path):
        """Read local and shared sessions, removing duplicates."""
        sections = parse_ini(ini_path)
        sessions = read_sessions(ini_path)
        for shared_file in shared_session_files(sections):
            try:
                sessions += read_sessions(shared_file, source="shared")
            except OSError:
                continue  # A missing network share must not break the plugin

        unique, seen = [], set()
        for session in sessions:
            key = session["bookmark"].lower()
            if key not in seen:
                seen.add(key)
                unique.append(session)
        return unique

    # ------------------------------------------------------------------ query
    @staticmethod
    def message(title, subtitle=""):
        return {"Title": title, "SubTitle": subtitle, "IcoPath": ICON}

    @staticmethod
    def score(session, terms):
        """Return a score (or None if it does not match all the terms)."""
        haystack = f"{session['bookmark']} {session['target']}".lower()
        if not all(term in haystack for term in terms):
            return None
        name = session["name"].lower()
        text = " ".join(terms)
        if name == text:
            return 100
        if name.startswith(text):
            return 80
        if text in name:
            return 60
        return 40

    def query(self, query):
        try:
            exe_path = self.find_executable()
            sessions = self.load_sessions(self.find_ini(exe_path))
        except MobaXtermError as e:
            return [self.message(e.title, e.subtitle)]
        except Exception as e:
            return [self.message("Error reading MobaXterm sessions", str(e))]

        if not sessions:
            return [self.message("No sessions found",
                                 "Save some bookmarks in MobaXterm first")]

        terms = query.lower().split()
        matches = []
        for session in sessions:
            score = self.score(session, terms) if terms else 50
            if score is not None:
                matches.append((score, session))
        matches.sort(key=lambda m: (-m[0], m[1]["bookmark"].lower()))

        if not matches:
            return [self.message(f"No sessions match '{query.strip()}'",
                                 f"{len(sessions)} sessions available")]

        results = []
        for score, session in matches:
            details = [session["folder"] or "Root", session["target"]]
            if session["source"] == "shared":
                details.append("shared")
            results.append({
                "Title": session["name"],
                "SubTitle": " · ".join(d for d in details if d),
                "IcoPath": ICON,
                "Score": score,
                "ContextData": [exe_path, session["bookmark"]],
                "JsonRPCAction": {
                    "method": "open_session",
                    "parameters": [exe_path, session["bookmark"]],
                },
            })
        return results

    def context_menu(self, data):
        if not isinstance(data, list) or len(data) != 2:
            return []
        exe_path, bookmark = data
        return [
            {
                "Title": "Open session",
                "SubTitle": bookmark,
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "open_session", "parameters": [exe_path, bookmark]},
            },
            {
                "Title": "Copy session name",
                "SubTitle": bookmark,
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "copy", "parameters": [bookmark]},
            },
            {
                "Title": "Open MobaXterm",
                "SubTitle": exe_path,
                "IcoPath": ICON,
                "JsonRPCAction": {"method": "open_mobaxterm", "parameters": [exe_path]},
            },
        ]

    # ---------------------------------------------------------------- actions
    def open_session(self, exe_path, bookmark):
        """Launch a MobaXterm session (arguments as a list: no shell parsing)."""
        try:
            subprocess.Popen([exe_path, "-bookmark", bookmark],
                             cwd=os.path.dirname(exe_path))
        except Exception as e:
            FlowLauncherAPI.show_msg("Could not open session", str(e))

    def open_mobaxterm(self, exe_path):
        try:
            subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
        except Exception as e:
            FlowLauncherAPI.show_msg("Could not open MobaXterm", str(e))

    def copy(self, text):
        """Copy text to the clipboard using UTF-16 for non-ASCII names."""
        try:
            subprocess.run(["clip"], input=text.strip().encode("utf-16le"), check=True)
            FlowLauncherAPI.show_msg("Copied to clipboard", text)
        except Exception as e:
            FlowLauncherAPI.show_msg("Clipboard Error", str(e))


if __name__ == "__main__":
    MobaLauncher()
