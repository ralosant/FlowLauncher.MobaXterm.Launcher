# encoding=utf8
"""
MabaXterm session launcher.

This plugin launches your bookmark sessions in MobaXterm from Flow.Launcher
Written the 23/09/2022 by Raul Losantos
"""

import os
import sys
# add plugin to local PATH
parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, 'lib'))
sys.path.append(os.path.join(parent_folder_path, 'plugin'))
from flowlauncher import FlowLauncher

from os.path import isfile
import json
import subprocess
import winreg as reg
from winreg import HKEY_CURRENT_USER

class MobaLauncher(FlowLauncher):
    """MabaXterm session launcher."""

    def mobaxterm_manifests(self):
        """Locate .ini file with the sessions."""
        DEFAULT_MOBA_INI = r'Software\Mobatek\MobaXterm'
        with reg.OpenKey(HKEY_CURRENT_USER, DEFAULT_MOBA_INI) as key:
            return reg.QueryValueEx(key, "LastIniPath")[0]

    def load_sessions(self):
        """Read user saved sessions in Bookmarks."""
        sessions = []
        with open(self.mobaxterm_manifests()) as inif:
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
        return json.dumps(sessions)

    def query(self, query):
        """Autocompletion."""
        with open(os.path.join(os.path.dirname(__file__),
                               "config.json"), "r") as content_file:
            config = json.loads(content_file.read())
        MobaXterm_folder_path = os.path.expandvars(config["MobaXtermPath"])
        MobaXterm_path = self.find_MobaXterm_path(MobaXterm_folder_path)
        session_list = self.load_sessions()
        res = []
        for session_name in json.loads(session_list):
            if query.lower() in session_name.lower():
                res.append({"Title": session_name, "IcoPath": "MobaXterm.ico",
                            "JsonRPCAction": {
                                "method": "open_session",
                                "parameters": [MobaXterm_path, session_name]}})
        return res

    def open_session(self, MobaXterm_path, selected_session_name):
        """Launch MobaXterm Session."""
        subprocess.Popen(
            '{} -bookmark "{}"'.format(MobaXterm_path, selected_session_name))

    def find_MobaXterm_path(self, MobaXterm_folder_path):
        """Return the full path to the user's MobaXterm executable."""
        attempted_MobaXterm_exe = os.path.join(MobaXterm_folder_path)
        if isfile(attempted_MobaXterm_exe):
            return attempted_MobaXterm_exe


if __name__ == "__main__":
    MobaLauncher()
