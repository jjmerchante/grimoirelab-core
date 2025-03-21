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

import logging
import os
import time
import typing

import click
import django.core
import django.core.wsgi
import django_rq
import redis
import requests

from django.conf import settings

if typing.TYPE_CHECKING:
    from click import Context


DEFAULT_BACKOFF_MAX = 60
DEFAULT_MAX_RETRIES = 10


@click.group()
@click.pass_context
def run(ctx: Context):
    """Run a GrimoireLab service."""

    pass


@click.option("--dev", "devel",
              is_flag=True,
              default=False,
              help="Run the service in developer mode.")
@run.command()
@click.pass_context
def server(ctx: Context, devel: bool):
    """Start the GrimoireLab core server.

    GrimoireLab server allows to schedule tasks and fetch data from
    software repositories. The server provides an API to perform all
    the operations.

    By default, the server runs a WSGI app because in production it
    should be run with a reverse proxy. If you activate the '--dev' flag,
    a HTTP server will be run instead.
    """
    env = os.environ

    env["UWSGI_ENV"] = f"DJANGO_SETTINGS_MODULE={ctx.obj['cfg']}"

    if devel:
        env["GRIMOIRELAB_DEBUG"] = "true"
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

    # Run maintenance tasks
    from grimoirelab.core.scheduler.scheduler import maintain_tasks

    _ = django.core.wsgi.get_wsgi_application()
    maintain_tasks()

    # Run the server
    os.execvp("uwsgi", ("uwsgi",))


@run.command()
@click.option('--workers',
              default=5,
              show_default=True,
              help="Number of workers to run in the pool.")
def eventizers(workers: int):
    """Start a pool of eventizer workers.

    The workers on the pool will run tasks to fetch data from software
    development repositories. Data will be processed in form of events,
    and published in the events queue.

    The number of workers running in the pool can be defined with the
    parameter '--workers'.

    Workers get jobs from the GRIMOIRELAB_Q_EVENTIZER_JOBS queue defined
    in the configuration file.
    """
    django.core.management.call_command(
        'rqworker-pool', settings.GRIMOIRELAB_Q_EVENTIZER_JOBS,
        num_workers=workers
    )


def _sleep_backoff(attempt: int) -> None:
    """Sleep with exponential backoff"""

    backoff = min(DEFAULT_BACKOFF_MAX, 2 ** attempt)
    time.sleep(backoff)


def _wait_opensearch_ready(url, verify_certs) -> None:
    """Wait for OpenSearch to be available before starting"""

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            r = requests.get(url,
                             verify=verify_certs)
            r.raise_for_status()
            break
        except (requests.exceptions.ConnectionError, requests.HTTPError) as e:
            logging.warning(f"[{attempt + 1}/{DEFAULT_MAX_RETRIES}] OpenSearch connection not ready")
            _sleep_backoff(attempt)

    else:
        logging.error("Failed to connect to OpenSearch")
        exit(1)

    logging.info("OpenSearch is ready")


def _wait_redis_ready():
    """Wait for Redis to be available before starting"""

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            redis_conn = django_rq.get_connection()
            redis_conn.ping()
            break
        except redis.exceptions.ConnectionError as e:
            logging.warning(f"[{attempt + 1}/{DEFAULT_MAX_RETRIES}] Redis connection not ready: {e}")
            _sleep_backoff(attempt)
    else:
        logging.error("Failed to connect to Redis server")
        exit(1)

    logging.info("Redis is ready")


@run.command()
@click.option('--workers',
              default=20,
              show_default=True,
              help="Number of archivists to run.")
@click.option("--verbose",
              is_flag=True,
              default=False,
              help="Enable verbose mode.")
@click.option("--burst",
              is_flag=True,
              default=False,
              help="Process all the events and exit.")
def archivists(workers: int, verbose: bool, burst: bool):
    """Start a pool of archivists.

    The archivists will fetch events from a redis stream.
    Data will be stored in the defined data source.

    The number of archivists can be defined with the parameter '--workers'.
    To enable verbose mode, use the '--verbose' flag.

    If the '--burst' flag is enabled, the pool will process all the events
    and exit.
    """
    from grimoirelab.core.consumers.archivist import OpenSearchArchivistPool

    _wait_opensearch_ready(settings.GRIMOIRELAB_ARCHIVIST['STORAGE_URL'],
                           settings.GRIMOIRELAB_ARCHIVIST['STORAGE_VERIFY_CERT'])
    _wait_redis_ready()

    pool = OpenSearchArchivistPool(
        # Consumer parameters
        stream_name=settings.GRIMOIRELAB_EVENTS_STREAM_NAME,
        group_name="opensearch-archivist",
        num_consumers=workers,
        stream_block_timeout=settings.GRIMOIRELAB_ARCHIVIST['BLOCK_TIMEOUT'],
        verbose=verbose,
        # OpenSearch parameters
        url=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_URL'],
        user=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_USERNAME'],
        password=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_PASSWORD'],
        index=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_INDEX'],
        bulk_size=settings.GRIMOIRELAB_ARCHIVIST['BULK_SIZE'],
        verify_certs=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_VERIFY_CERT'],
    )
    pool.start(burst=burst)
