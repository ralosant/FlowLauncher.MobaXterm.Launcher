# -*- coding: utf-8 -*-
"""
MabaXterm session launcher.

This plugin launches your bookmark sessions in MobaXterm from FlowLauncher
"""

import os
import sys

# add plugin to local PATH
parent_folder_path = os.path.abspath(os.path.dirname(__file__))
sys.path.append(parent_folder_path)
sys.path.append(os.path.join(parent_folder_path, 'lib'))
sys.path.append(os.path.join(parent_folder_path, 'plugin'))
sys.path.append(os.path.join(parent_folder_path, 'config'))

from plugin.MobaXtermLaunch import MobaLauncher

if __name__ == "__main__":
    MobaLauncher()
