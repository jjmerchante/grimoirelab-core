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

from typing import TYPE_CHECKING
from typing import Any
from collections.abc import Callable

import copy
import datetime
import logging

import django_rq
import perceval.backend
import perceval.backends

from grimoirelab_toolkit.datetime import str_to_datetime

from .jobs import execute_perceval_job
from .models import FetchTask
from .common import (DEFAULT_JOB_INTERVAL,
                     MAX_JOB_RETRIES,
                     Q_DEFAULT_JOBS,
                     Q_STORAGE_ITEMS)

if TYPE_CHECKING:
    from redis import Redis
    from rq.job import Job


logger = logging.getLogger(__name__)


def schedule_task(
        backend: str,
        category: str,
        backend_args: dict[str, Any],
        queue_id: str = Q_DEFAULT_JOBS,
        interval: int = DEFAULT_JOB_INTERVAL,
        max_retries: int = MAX_JOB_RETRIES
) -> FetchTask:
    """Create a new task and schedule a job for that task"""

    task = FetchTask.objects.create(backend=backend,
                                    category=category,
                                    backend_args=backend_args,
                                    queue=queue_id,
                                    interval=interval,
                                    max_retries=max_retries)

    enqueue_job(task, fn=execute_perceval_job)

    return task


def enqueue_job(
        task: FetchTask,
        fn: Callable,
        scheduled_datetime: datetime.datetime | None = None
) -> Job:
    """Enqueue a new job for the given task."""

    if not scheduled_datetime:
        scheduled_datetime = datetime.datetime.now(datetime.timezone.utc)

    job_args = _build_job_arguments(task)

    # TODO: should result_ttl be always set to -1?
    job = django_rq.get_queue(task.queue).enqueue_at(datetime=scheduled_datetime,
                                                     f=fn,
                                                     on_success=on_success_job,
                                                     on_failure=on_failed_job,
                                                     result_ttl=-1,
                                                     job_timeout=-1,
                                                     **job_args)

    task.status = FetchTask.Status.ENQUEUED
    task.age += 1
    task.scheduled_datetime = scheduled_datetime
    task.job_id = job.id
    task.save()

    logger.info(f"Job #{job.id} (task: {job_args['task_id']}) ({job_args['backend']})"
                f" enqueued in '{task.queue}' at {scheduled_datetime}")

    return job


def on_success_job(
        job: Job,
        connection: Redis,
        result: Any,
        *args,
        **kwargs
) -> None:
    """Reschedule the job based on the interval defined by the task.

    The new arguments for the job are obtained from the task
    object. This way if the object is updated between runs it
    will use the updated arguments.
    """
    try:
        task = FetchTask.objects.get(job_id=job.id)
    except FetchTask.DoesNotExist:
        logger.error("FetchTask not found. Not rescheduling.")
        return

    task.last_execution = datetime.datetime.now(datetime.timezone.utc)
    task.executions = task.executions + 1
    task.failed = False

    if result.summary.fetched > 0:
        backend_args = task.backend_args
        backend_args['next_from_date'] = result.summary.max_updated_on.isoformat()

        if result.summary.max_offset:
            backend_args['next_offset'] = result.summary.max_offset

        task.backend_args = backend_args

    scheduled_datetime = \
        datetime.datetime.now(datetime.timezone.utc) + \
        datetime.timedelta(seconds=task.interval)
    job = enqueue_job(task, job.func, scheduled_datetime=scheduled_datetime)
    task.job_id = job.id

    task.save()


def on_failed_job(
        job: Job,
        connection: Redis,
        t: Any,
        value: Any,
        traceback: Any
) -> None:
    try:
        task = FetchTask.objects.get(job_id=job.id)
    except FetchTask.DoesNotExist:
        logger.error("FetchTask not found. Not rescheduling.")
        return

    task.last_execution = datetime.datetime.now(datetime.timezone.utc)
    task.num_failures += 1

    logger.error("Job #%s (task: %s) failed; error: %s",
                 job.id, task.id, value)

    task_max_retries = MAX_JOB_RETRIES

    try:
        bklass = perceval.backend.find_backends(perceval.backends)[0][task.backend]
    except KeyError:
        bklass = None

    if not bklass or not bklass.has_resuming():
        task.status = FetchTask.Status.FAILED
        logger.error("Job #%s (task: %s) unable to resume; cancelled",
                     job.id, task.id)
    elif task.num_failures >= task_max_retries:
        task.status = FetchTask.Status.FAILED
        logger.error("Job #%s (task: %s) max retries reached; cancelled",
                     job.id, task.id)
    else:
        logger.error("Job #%s (task: %s) failed but task will be resumed",
                     job.id, task.id)

        result = job.meta.get('result', None)
        if result and result.summary.fetched > 0:
            task.backend_args['next_from_date'] = result.summary.max_updated_on

            if result.summary.max_offset:
                task.backend_args['next_offset'] = result.summary.max_offset

        scheduled_datetime = \
            datetime.datetime.now(datetime.timezone.utc) + \
            datetime.timedelta(minutes=task.interval)
        job = enqueue_job(task, job.func, scheduled_datetime=scheduled_datetime)
        task.job_id = job.id

    task.save()


def _build_job_arguments(task: FetchTask) -> dict[str, Any]:
    """Build the set of arguments required for running a job"""

    job_args = {}
    job_args['qitems'] = Q_STORAGE_ITEMS
    job_args['task_id'] = task.task_id

    # Backend parameters
    job_args['backend'] = task.backend
    backend_args = copy.deepcopy(task.backend_args)

    if 'next_from_date' in backend_args:
        backend_args['from_date'] = backend_args.pop('next_from_date')

    if 'next_offset' in backend_args:
        backend_args['offset'] = backend_args.pop('next_offset')

    if 'from_date' in backend_args and isinstance(backend_args['from_date'], str):
        backend_args['from_date'] = str_to_datetime(backend_args['from_date'])

    job_args['backend_args'] = backend_args

    # Category
    job_args['category'] = task.category

    return job_args
