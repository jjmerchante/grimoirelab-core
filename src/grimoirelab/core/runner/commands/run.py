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
import multiprocessing
import os
import time
import typing

import certifi
import click
import django.core
import django.core.wsgi
import django_rq
import opensearchpy
import redis
import structlog

from django.conf import settings
from django.db import connections, OperationalError
from urllib3.util import create_urllib3_context

if typing.TYPE_CHECKING:
    from click import Context


DEFAULT_BACKOFF_MAX = 60
DEFAULT_MAX_RETRIES = 10


logger = structlog.get_logger(__name__)


@click.group()
@click.pass_context
def run(ctx: Context):
    """Run a GrimoireLab service."""

    pass


@click.option(
    "--dev",
    "devel",
    is_flag=True,
    default=False,
    help="Run the service in developer mode.",
)
@click.option(
    "--maintenance-interval",
    default=300,
    show_default=True,
    help="Interval in seconds to run maintenance tasks.",
)
@run.command()
@click.pass_context
def server(ctx: Context, devel: bool, maintenance_interval: int):
    """Start the GrimoireLab core server.

    GrimoireLab server allows to schedule tasks and fetch data from
    software repositories. The server provides an API to perform all
    the operations.

    By default, the server runs a WSGI app because in production it
    should be run with a reverse proxy. If you activate the '--dev' flag,
    a HTTP server will be run instead.

    The server also runs maintenance tasks in the background every
    defined interval (default is 60 seconds). These tasks include
    rescheduling failed tasks and cleaning old jobs.
    """
    _wait_database_ready()
    _wait_redis_ready()

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

    # Run maintenance tasks in the background
    _maintenance_process(maintenance_interval)

    # Run the server
    os.execvp("uwsgi", ("uwsgi",))


def periodic_maintain_tasks(interval):
    from grimoirelab.core.scheduler.scheduler import maintain_tasks

    while True:
        try:
            maintain_tasks()
            logger.info("Maintenance tasks executed successfully")
        except redis.exceptions.ConnectionError as exc:
            logger.error("Redis connection error during maintenance tasks", err=exc)
        except django.db.utils.OperationalError as exc:
            logger.error("Database connection error during maintenance tasks", err=exc)
            connections.close_all()
        except Exception as exc:
            logger.error("Unexpected error during maintenance tasks", err=exc)
            raise
        except KeyboardInterrupt:
            logger.info("Maintenance task interrupted. Exiting...")
            return

        time.sleep(interval)


def _maintenance_process(maintenance_interval):
    """Process to run maintenance tasks periodically."""

    process = multiprocessing.Process(
        target=periodic_maintain_tasks, args=(maintenance_interval,), daemon=True
    )
    process.start()

    logger.info("Started maintenance process", pid=process.pid)

    return process


def worker_options(workers: int = 5, verbose: bool = False, burst: bool = False):
    """Decorator to add common worker options to commands."""

    def decorator(f):
        f = click.option(
            "--workers",
            default=workers,
            show_default=True,
            help="Number of workers to run in the pool.",
        )(f)
        f = click.option(
            "--verbose",
            is_flag=True,
            default=verbose,
            help="Enable verbose mode.",
        )(f)
        f = click.option(
            "--burst",
            is_flag=True,
            default=burst,
            help="Process all the events and exit.",
        )(f)
        return f

    return decorator


@run.command()
@worker_options(workers=5)
def eventizers(workers: int, verbose: bool, burst: bool):
    """Start a pool of eventizer workers.

    The workers on the pool will run tasks to fetch data from software
    development repositories. Data will be processed in form of events,
    and published in the events queue.

    The number of workers running in the pool can be defined with the
    parameter '--workers'.

    Workers get jobs from the GRIMOIRELAB_Q_EVENTIZER_JOBS queue defined
    in the configuration file.
    """
    _wait_redis_ready()
    _wait_database_ready()

    django.core.management.call_command(
        "rqworker-pool",
        settings.GRIMOIRELAB_Q_EVENTIZER_JOBS,
        num_workers=workers,
        burst=burst,
        verbosity=3 if verbose else 1,
    )


@run.command()
@worker_options(workers=5)
def sortinghat_workers(workers: int, verbose: bool, burst: bool):
    """Start a pool of SortingHat workers.

    The workers on the pool will process SortingHat related tasks.

    The number of workers running in the pool can be defined with the
    parameter '--workers'.

    To enable verbose mode, use the '--verbose' flag.

    If the '--burst' flag is enabled, the pool will process all the events
    and exit.

    Workers get jobs from the GRIMOIRELAB_Q_SORTINGHAT_JOBS queue defined
    in the configuration file.
    """
    _wait_redis_ready()
    _wait_database_ready()

    django.core.management.call_command(
        "rqworker-pool",
        settings.GRIMOIRELAB_Q_SORTINGHAT_JOBS,
        num_workers=workers,
        burst=burst,
        verbosity=3 if verbose else 1,
    )


def _sleep_backoff(attempt: int) -> None:
    """Sleep with exponential backoff"""

    backoff = min(DEFAULT_BACKOFF_MAX, 2**attempt)
    time.sleep(backoff)


def _wait_opensearch_ready(
    url: str, username: str | None, password: str | None, index: str, verify_certs: bool
) -> None:
    """Wait for OpenSearch to be available before starting"""

    # The 'opensearch' library writes logs with the exceptions while
    # connecting to the database. Disable them temporarily until
    # the service is up. We have to use logging library because structlog
    # doesn't allow to disable a logger dynamically.
    os_logger = logging.getLogger("opensearch")
    os_logger.disabled = True

    context = None
    if verify_certs:
        # Use certificates from the local system and certifi
        context = create_urllib3_context()
        context.load_default_certs()
        context.load_verify_locations(certifi.where())

    auth = (username, password) if username and password else None

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            client = opensearchpy.OpenSearch(
                hosts=[url],
                http_auth=auth,
                http_compress=True,
                verify_certs=verify_certs,
                ssl_context=context,
                ssl_show_warn=False,
            )
            client.search(index=index, size=0)
            break
        except opensearchpy.exceptions.NotFoundError:
            # Index still not created, but OpenSearch is up
            break
        except opensearchpy.exceptions.AuthorizationException:
            logger.error("OpenSearch Authorization failed. Check your credentials.")
            exit(1)
        except (
            opensearchpy.exceptions.ConnectionError,
            opensearchpy.exceptions.TransportError,
        ) as exc:
            logger.warning(
                f"[{attempt + 1}/{DEFAULT_MAX_RETRIES}] OpenSearch connection not ready",
                err=exc,
            )
            _sleep_backoff(attempt)

    else:
        logger.error("Failed to connect to OpenSearch.")
        exit(1)

    # Enable back 'opensearch' library logs
    os_logger.disabled = False

    logger.info("OpenSearch is ready.")


def _wait_redis_ready():
    """Wait for Redis to be available before starting"""

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            redis_conn = django_rq.get_connection()
            redis_conn.ping()
            break
        except redis.exceptions.ConnectionError as exc:
            logger.warning(
                f"[{attempt + 1}/{DEFAULT_MAX_RETRIES}] Redis connection not ready",
                err=exc,
            )
            _sleep_backoff(attempt)
    else:
        logger.error("Failed to connect to Redis server")
        exit(1)

    logger.info("Redis is ready")


def _wait_database_ready():
    """Wait for the database to be available before starting."""

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            db_conn = connections["default"]
            if db_conn:
                with db_conn.cursor():
                    pass  # Just test the connection
                break

        except OperationalError as exc:
            logger.warning(
                f"[{attempt + 1}/{DEFAULT_MAX_RETRIES}] Database connection not ready",
                err=exc.__cause__,
            )
            _sleep_backoff(attempt)
    else:
        error_msg = "Failed to connect to the database after all retries"
        logger.error(error_msg)
        raise ConnectionError(error_msg)

    logger.info("Database is ready.")

    # Close all database connections to avoid timed out connections
    connections.close_all()


@run.command()
@worker_options(workers=20)
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

    _wait_opensearch_ready(
        settings.GRIMOIRELAB_ARCHIVIST["STORAGE_URL"],
        settings.GRIMOIRELAB_ARCHIVIST["STORAGE_USERNAME"],
        settings.GRIMOIRELAB_ARCHIVIST["STORAGE_PASSWORD"],
        settings.GRIMOIRELAB_ARCHIVIST["STORAGE_INDEX"],
        settings.GRIMOIRELAB_ARCHIVIST["STORAGE_VERIFY_CERT"],
    )
    _wait_redis_ready()

    pool = OpenSearchArchivistPool(
        # Consumer parameters
        connection=django_rq.get_connection(),
        stream_name=settings.GRIMOIRELAB_EVENTS_STREAM_NAME,
        group_name="opensearch-archivist",
        num_consumers=workers,
        stream_block_timeout=settings.GRIMOIRELAB_ARCHIVIST["BLOCK_TIMEOUT"],
        verbose=verbose,
        # OpenSearch parameters
        url=settings.GRIMOIRELAB_ARCHIVIST["STORAGE_URL"],
        user=settings.GRIMOIRELAB_ARCHIVIST["STORAGE_USERNAME"],
        password=settings.GRIMOIRELAB_ARCHIVIST["STORAGE_PASSWORD"],
        index=settings.GRIMOIRELAB_ARCHIVIST["STORAGE_INDEX"],
        bulk_size=settings.GRIMOIRELAB_ARCHIVIST["BULK_SIZE"],
        verify_certs=settings.GRIMOIRELAB_ARCHIVIST["STORAGE_VERIFY_CERT"],
        rollover_indices=settings.GRIMOIRELAB_ARCHIVIST["ROLLOVER_INDICES"],
        rollover_size=settings.GRIMOIRELAB_ARCHIVIST["ROLLOVER_SIZE"],
    )
    pool.start(burst=burst)


@run.command()
@worker_options(workers=20)
def ushers(workers: int, verbose: bool, burst: bool):
    """Start a pool of workers that store identities from events.

    The workers will fetch events from a redis stream.
    Identities will be stored in SortingHat.

    The number of workers can be defined with the parameter '--workers'.
    To enable verbose mode, use the '--verbose' flag.

    If the '--burst' flag is enabled, the pool will process all the events
    and exit.
    """
    from grimoirelab.core.consumers.identities import SortingHatConsumerPool

    _wait_database_ready()
    _wait_redis_ready()

    pool = SortingHatConsumerPool(
        # Consumer parameters
        connection=django_rq.get_connection(),
        stream_name=settings.GRIMOIRELAB_EVENTS_STREAM_NAME,
        group_name="sortinghat-identities",
        num_consumers=workers,
        stream_block_timeout=settings.GRIMOIRELAB_ARCHIVIST["BLOCK_TIMEOUT"],
        verbose=verbose,
    )
    pool.start(burst=burst)
