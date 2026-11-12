# -*- coding: utf-8 -*-
"""
OwnCode Standalone Executable Builder (PyInstaller Helper)

Note: OwnCode already includes a ready-to-use native `OwnCode.exe` desktop
application in the project root with the custom "OC" icon embedded.
This script is provided in case you ever want to freeze Python + PySide6
into a standalone bundle using PyInstaller.
"""
import subprocess
import sys
from pathlib import Path


def build_standalone_exe() -> int:
    project_root = Path(__file__).resolve().parent.parent
    icon_path = project_root / "docs & resources" / "owncode_logo.ico"
    main_script = project_root / "main.py"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name=OwnCode",
        f"--icon={icon_path}",
        f"--add-data={project_root / 'docs & resources'};docs & resources",
        f"--add-data={project_root / 'config'};config",
        str(main_script),
    ]
    print("Running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(project_root))


if __name__ == "__main__":
    raise SystemExit(build_standalone_exe())
