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
import time
import typing

import click
import django.core
import django.core.wsgi
import django_rq
import redis.exceptions

from django.conf import settings
from django.db import connections, OperationalError

if typing.TYPE_CHECKING:
    from click import Context


DEFAULT_BACKOFF_MAX = 120
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
@click.option("--clear-tasks",
              is_flag=True,
              default=False,
              help="Clear background tasks.")
@run.command()
@click.pass_context
def server(ctx: Context, devel: bool, clear_tasks: bool):
    """Start the GrimoireLab core server.

    GrimoireLab server allows to schedule tasks and fetch data from
    software repositories. The server provides an API to perform all
    the operations.

    By default, the server runs a WSGI app because in production it
    should be run with a reverse proxy. If you activate the '--dev' flag,
    a HTTP server will be run instead.
    """
    wait_for_services(wait_archivist_storage=False)

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

    create_background_tasks(clear_tasks)

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
    wait_for_services(wait_archivist_storage=False)

    django.core.management.call_command(
        'rqworker-pool', settings.GRIMOIRELAB_Q_EVENTIZER_JOBS,
        num_workers=workers
    )


@run.command()
@click.option('--workers',
              default=20,
              show_default=True,
              help="Number of workers to run in the pool.")
def archivists(workers: int):
    """Start a pool of archivists workers.

    The workers on the pool will run tasks to fetch events from redis.
    Data will be stored in the defined data source.

    The number of workers running in the pool can be defined with the
    parameter '--workers'.

    Workers get jobs from the GRIMOIRELAB_Q_ARCHIVIST_JOBS queue defined
    in the configuration file.
    """
    wait_for_services()

    django.core.management.call_command(
        'rqworker-pool', settings.GRIMOIRELAB_Q_ARCHIVIST_JOBS,
        num_workers=workers
    )


def create_background_tasks(clear_tasks: bool):
    """
    Create background tasks before starting the server.
    :param clear_tasks: clear tasks before creating new ones.
    :return:
    """
    from grimoirelab.core.scheduler.scheduler import schedule_task
    from grimoirelab.core.scheduler.tasks.models import StorageTask
    from grimoirelab.core.scheduler.models import SchedulerStatus

    workers = settings.GRIMOIRELAB_ARCHIVIST['WORKERS']
    storage_url = settings.GRIMOIRELAB_ARCHIVIST['STORAGE_URL']
    storage_db_name = settings.GRIMOIRELAB_ARCHIVIST['STORAGE_INDEX']
    storage_type = settings.GRIMOIRELAB_ARCHIVIST['STORAGE_TYPE']
    verify_certs = settings.GRIMOIRELAB_ARCHIVIST['STORAGE_VERIFY_CERT']
    events_per_job = settings.GRIMOIRELAB_ARCHIVIST['EVENTS_PER_JOB']
    block_timeout = settings.GRIMOIRELAB_ARCHIVIST['BLOCK_TIMEOUT']

    if clear_tasks:
        StorageTask.objects.all().delete()
        click.echo("Removing old background tasks.")

    current = StorageTask.objects.filter(burst=False).exclude(status=SchedulerStatus.FAILED).count()
    if workers == current:
        click.echo("Background tasks already created. Skipping.")
        return

    task_args = {
        'storage_url': storage_url,
        'storage_db_name': storage_db_name,
        'storage_verify_certs': verify_certs,
        'redis_group': 'archivist',
        'limit': events_per_job,
        'block_timeout': block_timeout
    }
    if workers > current:
        for _ in range(workers - current):
            schedule_task(
                task_type=StorageTask.TASK_TYPE,
                storage_type=storage_type,
                task_args=task_args,
                job_interval=1,
                job_max_retries=10
            )
        click.echo(f"Created {workers} background tasks.")
    elif workers < current:
        tasks = StorageTask.objects.all()[workers:]
        tasks.update(burst=True)


def wait_for_services(
        wait_database: bool = True,
        wait_redis: bool = True,
        wait_archivist_storage: bool = True
):
    """Wait for services to be available before starting"""

    if wait_database:
        wait_database_ready()

    if wait_redis:
        wait_redis_ready()

    if wait_archivist_storage:
        wait_archivist_storage_ready()


def _sleep_backoff(attempt: int) -> None:
    """Sleep with exponential backoff"""

    backoff = min(DEFAULT_BACKOFF_MAX, 2 ** attempt)
    time.sleep(backoff)


def wait_database_ready():
    """Wait for the database to be available before starting"""

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            db_conn = connections['default']
            if db_conn:
                db_conn.cursor()
                db_conn.close()
                break
        except OperationalError as e:
            click.echo(f"[{attempt}/{DEFAULT_MAX_RETRIES}] Database connection not ready {e.__cause__}")
            _sleep_backoff(attempt)
    else:
        click.echo("Failed to connect to the database")
        exit(1)


def wait_redis_ready():

    for attempt in range(DEFAULT_MAX_RETRIES):
        try:
            redis_conn = django_rq.get_connection(settings.GRIMOIRELAB_Q_EVENTIZER_JOBS)
            redis_conn.ping()
            break
        except redis.exceptions.ConnectionError as e:
            click.echo(f"[{attempt}/{DEFAULT_MAX_RETRIES}] Redis connection not ready {e.__cause__}")
            _sleep_backoff(attempt)
    else:
        click.echo("Failed to connect to Redis server")
        exit(1)


def wait_archivist_storage_ready():
    """Wait for the storage to be available before starting"""

    for attempt in range(DEFAULT_MAX_RETRIES):
        from grimoirelab.core.scheduler.tasks.archivist import get_storage_backend
        Storage = get_storage_backend(settings.GRIMOIRELAB_ARCHIVIST['STORAGE_TYPE'])
        storage = Storage(url=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_URL'],
                          db_name=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_INDEX'],
                          verify_certs=settings.GRIMOIRELAB_ARCHIVIST['STORAGE_VERIFY_CERT'])

        if storage.ping():
            break
        else:
            click.echo(f"[{attempt}/{DEFAULT_MAX_RETRIES}] Storage connection not ready")
            _sleep_backoff(attempt)
    else:
        click.echo("Failed to connect to archivist storage")
        exit(1)
