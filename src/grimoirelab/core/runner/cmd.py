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

from __future__ import annotations

import typing
import os

import click
import django.core.wsgi

from .commands.admin import admin
from .commands.run import run

if typing.TYPE_CHECKING:
    from click import Context


@click.group()
@click.option('--config', 'cfg',
              envvar='GRIMOIRELAB_CONFIG',
              default='grimoirelab.core.config.settings',
              show_default=True,
              help="Configuration module in Python path syntax")
@click.pass_context
def grimoirelab(ctx: Context, cfg: str):
    """Toolset for software development analytics.

    GrimoireLab is a set of tools and a platform to retrieve, analyze,
    and provide insights about data coming from software development
    repositories. With this command, you'll be able to configure and
    run its different services.

    It requires to pass a configuration file module using
    the Python path syntax (e.g. grimoirelab.core.config.settings).
    Take into account the configuration should be accessible by your
    PYTHON_PATH. You can also use the environment variable
    GRIMOIRELAB_CONFIG to define the config location.
    """
    env = os.environ

    if cfg:
        env['DJANGO_SETTINGS_MODULE'] = cfg
        ctx.ensure_object(dict)
        ctx.obj["cfg"] = cfg
    else:
        raise click.ClickException(
            "Configuration file not given. "
            "Set it with '--config' option "
            "or 'GRIMOIRELAB_CONFIG' env variable."
        )

    _ = django.core.wsgi.get_wsgi_application()


grimoirelab.add_command(admin)
grimoirelab.add_command(run)
