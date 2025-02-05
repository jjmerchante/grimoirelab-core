# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Developers
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import pathlib
import subprocess
import sys


def yarn(*args):
    retcode = subprocess.call(["yarn", *list(args)])

    if retcode != 0:
        sys.exit(retcode)


def build_ui():
    ui_dir = pathlib.Path(__file__).parent.parent.joinpath("ui")

    sys.stderr.write(f"\nBuilding UI in {ui_dir}\n")
    yarn("--cwd", ui_dir.as_posix(), "install")
    yarn("--cwd", ui_dir.as_posix(), "build")
    sys.stderr.write(f"UI built in {ui_dir}\n\n")


if __name__ == "__main__":
    build_ui()
