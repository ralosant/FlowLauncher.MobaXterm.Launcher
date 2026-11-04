# MobaXterm Launcher

This plugin lets you launch [MobaXterm](https://mobaxterm.mobatek.net/) bookmark sessions from [Flow Launcher](https://www.flowlauncher.com/).

## How to use it

1. Install this plugin via `pm install MobaXterm Launcher`
2. Usage examples:
  - `moba`: Lists all your saved sessions.
  - `moba <text>`: Searches sessions by name, folder, host or user.
    - Example: `moba web01`
  - `moba <word> <word>`: Every word must match (in any order).
    - Example: `moba prod db` finds `Production\db-server`
    - Example: `moba root@10.0` finds sessions by user and host

Select a result or press Enter to open the session in MobaXterm.

Press `Shift+Enter` (context menu) on a result to:
  - Open the session
  - Copy the session name to the clipboard
  - Open MobaXterm without a session

Sessions stored in subfolders and shared sessions (`.mxtsessions` files) are also supported.

## Settings

- `moba_path`: Folder or `.exe` of MobaXterm. Works with the installed and the portable edition (default: `C:\Program Files (x86)\Mobatek\MobaXterm\`). If it is not valid, the default install folders are tried.
- `ini_path` (optional): Path to your `MobaXterm.ini`. If empty, it is detected automatically from the registry, the MobaXterm folder or `%APPDATA%\MobaXterm`.

Environment variables such as `%USERPROFILE%` are allowed in both settings.
