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
# Authors:
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#


import click

from .utils import import_string


@click.group()
def grimoirelab():
    """CHAOSS toolset for software development analytics"""


for cmd in map(
    import_string,
    (
        'grimoirelab.core.runner.commands.run.run',
        'grimoirelab.core.runner.commands.config.config',
        'grimoirelab.core.runner.commands.queues.queues',
        'grimoirelab.core.runner.commands.fetch.fetch_task',
    )
):
    grimoirelab.add_command(cmd)
