# encoding=utf8
"""
MabaXterm session launcher.

This plugin launches your bookmark sessions in MobaXterm from Flow.Launcher
"""
import os
import sys
from winreg import HKEY_CURRENT_USER
import winreg as reg
import subprocess
import json
from os.path import isfile
from flowlauncher import FlowLauncher
# from flox import Flox

# class Get_conf(Flox):
    # def __init__(self):
        # return self.settings.get("MOBA_PATH")


class MobaLauncher(FlowLauncher):
    """MabaXterm session launcher."""
        
    def mobaxterm_manifests(self, MobaXterm_folder_path):
        """Locate .ini file with the sessions."""
        # Read from registry
        try:
            DEFAULT_MOBA_INI = r'Software\Mobatek\MobaXterm'
            with reg.OpenKey(HKEY_CURRENT_USER, DEFAULT_MOBA_INI) as key:
                return reg.QueryValueEx(key, "LastIniPath")[0]
        except:
            DEFAULT_MOBA_INI = os.path.join(MobaXterm_folder_path, 'MobaXterm.ini')
            return DEFAULT_MOBA_INI

    def find_MobaXterm_path(self, MobaXterm_folder_path):
        """Return the full path to the user's MobaXterm executable."""
        for exe_name in os.listdir(MobaXterm_folder_path):
            if exe_name.endswith('.exe') and exe_name.startswith('MobaXterm'):
                attempted_MobaXterm_exe = os.path.join(
                    MobaXterm_folder_path, exe_name)
        if isfile(attempted_MobaXterm_exe):
            return attempted_MobaXterm_exe
        raise Exception("Could not find MobaXterm executable in %s" %
                        MobaXterm_folder_path)

    def read_sessions(self, Session_File, sessions):
        """Read sessions from Bookmarks."""
        sessions = sessions
        with open(Session_File) as inif:
            lines = list(inif.read().splitlines())
        for i in range(100):
            if i == 0:
                n0_line = lines.index('[Bookmarks]')
            else:
                try:
                    n0_line = lines.index(f'[Bookmarks_{i}]')
                except ValueError:
                    break
            subrep = lines[n0_line+1].split('=')[-1]
            for j in range(100):
                name_session = (lines[n0_line+3+j].split('='))[0]
                if not name_session:
                    break
                if i == 0:
                    sessions.append(name_session)
                else:
                    sessions.append(f"{subrep}\\{name_session}")
        return sessions

    def load_sessions(self, MobaXterm_folder_path):
        """Read user saved sessions."""
        sessions = []
        # Check shared sessions
        with open(self.mobaxterm_manifests(MobaXterm_folder_path)) as inif:
            lines = list(inif.read().splitlines())
        for i in range(100):
            try:
                n0_line = lines.index(f'[SharedSessions{i}]')
                file_shared_session = (lines[n0_line+5].split('='))[-1]
            except ValueError:
                break
            self.read_sessions(file_shared_session, sessions)
        # Check bookmark sessions
        self.read_sessions(self.mobaxterm_manifests(MobaXterm_folder_path), sessions)
        # Remove useless duplicates
        unique_sessions = set(sessions)
        sessions = list(unique_sessions)
        return json.dumps(sessions)
        
    def query(self, query):
        """Autocompletion."""
        # with open(os.path.join(os.path.dirname(__file__), "config.json"), "r") as content_file:
            # config = json.loads(content_file.read())
        # MobaXterm_folder_path = os.path.expandvars(config["MobaXtermPath"])
        MobaXterm_folder_path = os.path.expandvars(self.rpc_request['settings']['moba_path'])
        MobaXterm_path = self.find_MobaXterm_path(MobaXterm_folder_path)
        session_list = self.load_sessions(MobaXterm_folder_path)
        result = []
        for session_name in json.loads(session_list):
            if query.lower() in session_name.lower():
                result.append({"Title": session_name, "IcoPath": "MobaXterm.ico",
                               "JsonRPCAction": {"method": "open_session", "parameters": [MobaXterm_path, session_name]}})
        return result

    def open_session(self, MobaXterm_path, selected_session_name):
        """Launch MobaXterm Session."""
        subprocess.Popen('{} -bookmark "{}"'.format(MobaXterm_path, selected_session_name))


if __name__ == "__main__":
    MobaLauncher()
