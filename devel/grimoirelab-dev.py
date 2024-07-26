#!/usr/bin/env python3
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

import os
import typing

import click
import django.core.wsgi
import django_rq

import grimoire_elk.elastic

if typing.TYPE_CHECKING:
    from click import Context
    from typing import Any, Generator


@click.group()
@click.option('--config', 'cfg',
              envvar='GRIMOIRELAB_CONFIG',
              default='grimoirelab.core.config.settings',
              show_default=True,
              help="Configuration module in Python path syntax")
@click.pass_context
def grimoirelab_dev(ctx: Context, cfg: str):
    """Developer tools for testing GrimoireLab core.

    This command offers a set of tools that can come in handy to
    test the correct behavior of the GrimoireLab core components.

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


@grimoirelab_dev.group()
def schedule():
    """Command to schedule new tasks."""
    pass


@schedule.command('eventize-git')
@click.argument('repository')
def eventize_git(repository: str):
    """Run a task to eventize data from a Git repository.

    It will create a FetchTask to fetch the data for the given Git
    repository and store the results in a Redis Queue.
    """
    from grimoirelab.core.scheduler.scheduler import schedule_task

    backend = 'git'
    category = 'commit'
    backend_args = {
        "uri": repository
    }

    schedule_task(backend=backend,
                  category=category,
                  backend_args=backend_args)


@schedule.command('eventize-github')
@click.argument('category')
@click.argument('owner')
@click.argument('repository')
@click.option('--api-token', 'api_token',
              help="Token for fetching commits for this repository")
def eventize_github(
        category: str,
        owner: str,
        repository: str,
        api_token: str | None = None
):
    """Run a task to eventize data from a GitHub repository.

    It will create a FetchTask to fetch the data for the given GitHub
    repository and store the results in a Redis Queue.
    """
    from grimoirelab.core.scheduler.scheduler import schedule_task

    backend = 'github'
    category = category
    backend_args = {
        "owner": owner,
        "repository": repository
    }

    if api_token:
        backend_args['api_token'] = api_token

    schedule_task(backend=backend,
                  category=category,
                  backend_args=backend_args)


@grimoirelab_dev.group()
def consume():
    """Consume events from the queue."""

    pass


@consume.command(name='stdout')
def stdout_consumer():
    """Consume events to print them to stdout."""

    connection = django_rq.get_connection()
    items = _items_consumer(connection)

    for i, item in enumerate(items):
        click.echo(i, item['id'])


@consume.command(name='opensearch')
@click.argument('url')
@click.argument('index')
@click.pass_context
def opensearch_consumer(url: str, index: str):
    """Consume events to insert them into OpenSearch."""

    redis = django_rq.get_connection()
    elastic = grimoire_elk.elastic.ElasticSearch(url, index)
    items = _items_consumer(redis)
    elastic.bulk_upload(items, field_id='id')


def _items_consumer(connection: django_rq.Connection) -> Generator[dict, Any]:
    """Generator to consume items from the queue."""

    import time
    import json

    from django.conf import settings

    while True:
        data = connection.lpop(settings.Q_EVENTS)
        if not data:
            time.sleep(5)
            continue
        yield json.loads(data)


if __name__ == "__main__":
    grimoirelab_dev()
