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

from __future__ import annotations

import logging
import os

import click

from django.conf import settings
from django.core import management
from django.core.wsgi import get_wsgi_application


logger = logging.getLogger('main')


@click.group()
@click.option('--config', 'cfg', envvar='GRIMOIRELAB_CONFIG',
              help="Config module in Python path syntax,"
                   "e.g. grimoirelab.core.config.settings.")
def config(cfg: str):
    """GrimoireLab administration tool.

    This swiss army knife tool allows to run administrative tasks to
    configure, initialize, or update the service.

    To run the tool you will need to pass a configuration file module
    using Python path syntax (e.g. grimoirelab.core.config.settings).
    Take into account the module should be accessible by your PYTHON_PATH.
    """
    env = os.environ

    if cfg:
        env['DJANGO_SETTINGS_MODULE'] = cfg
    else:
        raise click.ClickException(
            "Configuration file not given. "
            "Set it with '--config' option "
            "or 'GRIMOIRELAB_CONFIG' env variable."
        )

    _ = get_wsgi_application()


@config.command()
def setup():
    """Run initialization tasks to configure GrimoireLab.

    It will set up the database.
    """
    _setup()


def _setup():
    _create_database()
    _setup_database()

    click.secho("\nGrimoirelab configuration completed", fg='bright_cyan')


def _create_database(database: str = 'default', db_name: str | None = None):
    """Create an empty database."""

    import MySQLdb

    db_params = settings.DATABASES[database]
    db_name = db_name if db_name else db_params['NAME']

    click.secho("## GrimoireLab database creation\n", fg='bright_cyan')

    try:
        cursor = MySQLdb.connect(
            user=db_params['USER'],
            password=db_params['PASSWORD'],
            host=db_params['HOST'],
            port=int(db_params['PORT'])
        ).cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {db_name} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci;"
        )
    except MySQLdb.DatabaseError as exc:
        msg = f"Error creating database '{db_name}' for '{database}': {exc}."
        raise click.ClickException(msg)

    click.echo(f"GrimoireLab database '{db_name}' for '{database}' created.\n")


def _setup_database(database: str = 'default'):
    """Apply migrations and fixtures to the database."""

    click.secho(f"## GrimoireLab database setup for {database}\n", fg='bright_cyan')

    management.call_command('migrate', database=database)

    click.echo()
