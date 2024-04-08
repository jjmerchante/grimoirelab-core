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

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import os
import time

import click
import django_rq
from django.conf import settings

from django.core.wsgi import get_wsgi_application
from django.core import management

if TYPE_CHECKING:
    from click import Context


@click.group()
@click.option('--config', 'cfg', envvar='GRIMOIRELAB_CONFIG',
              default='grimoirelab.core.config.settings', show_default=True,
              help="Configuration module in Python path syntax")
@click.pass_context
def run(ctx: Context, cfg: str):
    """Run a service.

    To run the tool you will need to pass a configuration file module
    using Python path syntax (e.g. grimoirelab.core.config.settings).
    Take into account the module should be accessible by your PYTHON_PATH.
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
@click.option('--num-workers', default=10, show_default=True,
              help="Number of workers to run in the pool.")
def workerpool(num_workers: int):
    """Starts a GrimoireLab worker pool.

    Workers get jobs from the list of queues, executing one job at a time.
    This list of queues are passed as a list of arguments to this command,
    and they need to be defined in the configuration file. If the list is
    not given, workers will listen for jobs on all the queues defined in
    the configuration.

    The configuration is defined by a configuration file module using
    Python path syntax (e.g. grimoirelab.core.config.settings). Take into
    account the module should be accessible by your PYTHONPATH env variable.
    """
    try:
        management.call_command('rqworker-pool', num_workers=num_workers)
    except KeyError as e:
        raise click.ClickException(f"Queue '{e.args[0]}' not found")


@click.option(
    "--dev",
    "devel",
    is_flag=True,
    default=False,
    help="Run the service in developer mode.",
)
@run.command()
@click.pass_context
def server(ctx: Context, devel: bool):
    """Starts the GrimoireLab core server.

    GrimoireLab allows to schedule tasks and fetch data from software
    repositories. The server provides an API to perform all the operations.

    To run the server, you will need to pass a configuration file module
    using Python path syntax (e.g. grimoirelab.core.config.settings). Take into
    account the module should be accessible by your PYTHON_PATH.

    By default, the server runs a WSGI app because in production it should
    be run with a reverse proxy. If you activate the '--dev' flag, an HTTP
    server will be run instead.
    """
    env = os.environ

    env["UWSGI_ENV"] = f"DJANGO_SETTINGS_MODULE={ctx.obj['cfg']}"

    if devel:
        env["GRIMOIRELAB_DEBUG"] = "true"

        from django.conf import settings

        env["UWSGI_HTTP"] = env.get("GRIMOIRELAB_HTTP_DEV", "127.0.0.1:8000")
        env["UWSGI_STATIC_MAP"] = settings.STATIC_URL + "=" + settings.STATIC_ROOT
    else:
        env["UWSGI_HTTP"] = ""

    env["UWSGI_MODULE"] = "grimoirelab.core.app.wsgi:application"
    env["UWSGI_SOCKET"] = "0.0.0.0:9314"

    # Run in multiple threads by default
    env["UWSGI_WORKERS"] = env.get("GRIMOIRELAB_UWSGI_WORKERS", "1")
    env["UWSGI_THREADS"] = env.get("GRIMOIRELAB_UWSGI_THREADS", "4")

    # These options shouldn't be modified
    env["UWSGI_MASTER"] = "true"
    env["UWSGI_ENABLE_THREADS"] = "true"
    env["UWSGI_LAZY_APPS"] = "true"
    env["UWSGI_SINGLE_INTERPRETER"] = "true"

    os.execvp("uwsgi", ("uwsgi",))


def _items_consumer(connection):
    while True:
        data = connection.lpop(settings.Q_EVENTS)
        if not data:
            time.sleep(5)
            continue
        yield json.loads(data)


@run.command()
def test_consumer():
    """Consume Perceval items from the queue and prints them."""

    connection = django_rq.get_connection()
    items = _items_consumer(connection)
    for i, item in enumerate(items):
        print(i, item['id'])


@run.command()
@click.argument('url')
@click.argument('index')
def opensearch_consumer(url, index):
    """Consume Perceval items and insert them into Opensearch."""

    from grimoire_elk.elastic import ElasticSearch

    redis = django_rq.get_connection()
    elastic = ElasticSearch(url, index)
    items = _items_consumer(redis)
    elastic.bulk_upload(items, field_id='id')
