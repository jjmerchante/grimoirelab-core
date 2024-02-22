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

import os
import pickle
import time

import click
import django_rq

from django.core.wsgi import get_wsgi_application
from django.core import management

from grimoirelab.core.scheduler.common import Q_STORAGE_ITEMS


@click.group()
@click.option('--config', 'cfg', envvar='GRIMOIRELAB_CONFIG',
              help="Configuration module in Python path syntax,"
                   "e.g. grimoirelab.core.config.settings")
def run(cfg: str):
    """Run a service.

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


@run.command()
@click.argument('queues', nargs=-1)
def scheduler_worker(queues: list):
    """Starts a GrimoireLab worker.

    Workers get jobs from the list of queues, executing one job at a time.
    This list of queues are passed as a list of arguments to this command,
    and they need to be defined in the configuration file. If the list is
    not given, workers will listen for jobs on all the queues defined in
    the configuration.

    The configuration is defined by a configuration file module using
    Python path syntax (e.g. grimoirelab.core.config.settings). Take into
    account the module should be accessible by your PYTHONPATH env variable.

    QUEUES: read jobs from this list; if empty, reads from all the
    defined queues in the configuration file.
    """
    try:
        management.call_command('rqworker', *queues, with_scheduler=True)
    except KeyError as e:
        raise click.ClickException(f"Queue '{e.args[0]}' not found")


@run.command()
def test_perceval_consumer():
    """Consume Perceval items from the queue and prints them."""

    connection = django_rq.get_connection()
    while True:
        data = connection.lpop(Q_STORAGE_ITEMS)
        if not data:
            time.sleep(5)
            continue
        print(pickle.loads(data))
