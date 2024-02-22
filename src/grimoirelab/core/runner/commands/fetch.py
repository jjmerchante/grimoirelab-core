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
#     Santiago Dueñas <sduenas@bitergia.com>
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import logging
import os

import click

from django.core.wsgi import get_wsgi_application


logger = logging.getLogger('main')


@click.group()
@click.option('--config', 'cfg', envvar='GRIMOIRELAB_CONFIG',
              help="Config module in Python path syntax,"
                   "e.g. grimoirelab.core.config.settings.")
def fetch_task(cfg: str):
    """Command to create new tasks

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


@fetch_task.command()
@click.argument('repository')
def git_repository(repository: str):
    """Run a task to fetch a Git repository

    It will create a FetchTask to fetch the data for the given Git
    repository and store the results in a Redis Queue.
    """
    from grimoirelab.core.scheduler.scheduler import schedule_task

    backend = 'git'
    category = 'commit'

    base_path = os.path.expanduser('~/.perceval/repositories/')
    processed_uri = repository.lstrip('/')
    git_path = os.path.join(base_path, processed_uri) + '-git'

    backend_args = {
        "gitpath": git_path,
        "uri": repository
    }

    schedule_task(backend=backend,
                  category=category,
                  backend_args=backend_args)
