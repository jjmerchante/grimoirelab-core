# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Contributors
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

import subprocess
import sys
from typing import List

from cleo.events.console_events import COMMAND
from cleo.events.console_command_event import ConsoleCommandEvent
from poetry.console.application import Application
from poetry.console.commands.build import BuildCommand
from poetry.console.commands.install import InstallCommand
from poetry.plugins.application_plugin import ApplicationPlugin


class PreHookPlugin(ApplicationPlugin):
    """Plugin to execute pre-hooks before install and build commands."""

    def activate(self, application: Application) -> None:
        """Activate the plugin by registering event listeners."""

        application.event_dispatcher.add_listener(COMMAND, self.on_command)

    def on_command(self, event: ConsoleCommandEvent, event_name: str, dispatcher) -> None:
        """Handle command events to execute pre-hooks before install/build."""

        command = event.command

        if isinstance(command, (InstallCommand, BuildCommand)):
            self._execute_pre_hooks(command, event)

    def _execute_pre_hooks(self, command, event: ConsoleCommandEvent) -> None:
        """Execute pre-hooks based on the command type."""

        command_name = command.name
        poetry = command.poetry
        pyproject_data = poetry.pyproject.data

        prehook_config = pyproject_data.get("tool", {}).get("poetry-prehook", {})

        if not prehook_config:
            return

        scripts = []

        if command_name == "install":
            scripts = prehook_config.get("pre-install", [])
        elif command_name == "build":
            scripts = prehook_config.get("pre-build", [])

        if scripts:
            event.io.write_line(f"<info>Running pre-{command_name} hooks...</info>")
            self._run_scripts(scripts, event.io, poetry.file.path.parent)

    def _run_scripts(self, scripts: List[str], io, cwd) -> None:
        """Execute a list of scripts."""

        for script in scripts:
            io.write_line(f"<comment>Executing: {script}</comment>")

            try:
                result = subprocess.run(
                    script, shell=True, cwd=cwd, capture_output=True, text=True, check=True
                )

                if result.stdout:
                    io.write_line(result.stdout.strip())

            except subprocess.CalledProcessError as e:
                io.write_error_line(f"<error>Script failed with exit code {e.returncode}</error>")
                if e.stdout:
                    io.write_error_line(f"STDOUT: {e.stdout.strip()}")
                if e.stderr:
                    io.write_error_line(f"STDERR: {e.stderr.strip()}")

                sys.exit(e.returncode)

            except Exception as e:
                io.write_error_line(f"<error>Failed to execute script '{script}': {e}</error>")
                sys.exit(1)

        io.write_line("<info>Pre-hooks completed successfully.</info>")
