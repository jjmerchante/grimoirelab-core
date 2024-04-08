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

import datetime
import logging

from typing import Any, TYPE_CHECKING
from uuid import uuid4

import django_rq
import perceval

from django.conf import settings
from rq import cancel_job
from rq.job import Job as JobRQ

from .backends.utils import get_scheduler_backend
from .errors import NotFoundError
from .jobs import PercevalJob
from .models import FetchTask, Job

if TYPE_CHECKING:
    from redis import Redis

logger = logging.getLogger(__name__)


def schedule_task(
        backend: str,
        category: str,
        backend_args: dict[str, Any],
        queue_id: str = settings.Q_PERCEVAL_JOBS,
        interval: int = settings.PERCEVAL_JOB_INTERVAL,
        max_retries: int = settings.PERCEVAL_JOB_MAX_RETRIES,
) -> FetchTask:
    """Create a new task and schedule a job for that task"""

    task = FetchTask.objects.create(
        backend=backend,
        category=category,
        backend_args=backend_args,
        queue=queue_id,
        interval=interval,
        max_retries=max_retries,
        status=FetchTask.Status.ENQUEUED
    )
    enqueue_task(task=task)

    return task


def remove_task(task_id: str):
    """Remove a task and cancel the associated job"""

    try:
        task = FetchTask.objects.get(id=task_id)
    except FetchTask.DoesNotExist:
        raise NotFoundError(element=task_id)

    connection = django_rq.get_connection()

    job = Job.objects.filter(task=task, status=Job.Status.RUNNING).only('job_id')
    if job:
        cancel_job(job.job_id, connection=connection)

    task.delete()


def reschedule_task(task_id: str):
    """Reschedule a task from scratch when is with status failed"""

    try:
        task = FetchTask.objects.get(id=task_id)
    except FetchTask.DoesNotExist:
        raise NotFoundError(element=task_id)

    if task.status == FetchTask.Status.FAILED:
        task.age = 0
        task.executions = 0
        task.num_failures = 0
        task.status = FetchTask.Status.ENQUEUED
        task.save()

        enqueue_task(task=task)

        return True

    return False


def _build_job_args(task):
    return {
        'qitems': settings.Q_EVENTS,
        'task_id': task.task_id
    }


def enqueue_task(
        task: FetchTask,
        scheduled_datetime: datetime.datetime | None = None,
        job_args: dict | None = None
) -> PercevalJob:
    """
    Create a new job for the specified Task at a specific time.
    The arguments of the new job are based on those of the previous
    job or the task, if the job doesn't exist.
    The status of the task will change to `ENQUEUED`.

    :param task: the task to enqueue
    :param scheduled_datetime: datetime at which the task will be executed
    :param job_args: use these arguments for the job
    :return: Perceval job enqueued
    """

    if not scheduled_datetime:
        scheduled_datetime = datetime.datetime.now(datetime.timezone.utc)

    if not job_args:
        job_args = _build_job_args(task)
        backend = get_scheduler_backend(task.backend)
        backend_args = backend.create_backend_args(task)
        job_args.update(backend_args)

    job = Job.objects.create(
        job_id=str(uuid4()),
        task=task,
        backend=task.backend,
        category=task.category,
        backend_args=job_args,
        queue=task.queue,
        scheduled_datetime=scheduled_datetime
    )

    django_rq.get_queue(task.queue, job_class=PercevalJob).enqueue_at(
        datetime=scheduled_datetime,
        f=PercevalJob.run,
        result_ttl=settings.PERCEVAL_JOB_RESULT_TTL,
        job_timeout=settings.PERCEVAL_JOB_TIMEOUT,
        on_success=on_success_callback,
        on_failure=on_failure_callback,
        job_id=job.job_id,
        **job_args,
    )

    task.age += 1
    task.scheduled_datetime = scheduled_datetime
    task.save()

    logger.info(
        f"Job #{job.job_id} (task: {job_args['task_id']}) ({job_args['backend']})"
        f" enqueued in '{task.queue}' at {scheduled_datetime}"
    )

    return job


def on_success_callback(job: JobRQ, connection: Redis, result: Any, *args) -> None:
    """Reschedule the job based on the interval defined by the task.

    The new arguments for the job are obtained from the result
    of the job object.
    """
    try:
        dbjob = Job.objects.get(job_id=job.id)
    except Job.DoesNotExist:
        logger.error("Job not found. Not rescheduling.")
        return

    # Update task
    task = dbjob.task
    task.status = FetchTask.Status.COMPLETED
    task.last_execution = datetime.datetime.now(datetime.timezone.utc)
    task.executions = task.executions + 1
    task.failed = False
    task.num_failures = 0
    task.save()

    # Update job result
    dbjob.status = Job.Status.COMPLETED
    dbjob.result = result.to_dict()
    dbjob.logs = job.meta['log']
    dbjob.save()

    logger.info(f"Job #{job.id} (task: {task.id}) completed. {result.summary.fetched} items fetched.")

    # Create new job
    if task.interval > 0:
        task.status = FetchTask.Status.ENQUEUED
        backend = get_scheduler_backend(task.backend)
        job_args = backend.update_backend_args(result.summary, dbjob.backend_args)
        scheduled_datetime = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=task.interval)
        enqueue_task(task, scheduled_datetime=scheduled_datetime, job_args=job_args)


def on_failure_callback(job: JobRQ, connection: Redis, t: Any, value: Any, traceback: Any):
    try:
        jobdb = Job.objects.get(job_id=job.id)
    except Job.DoesNotExist:
        logger.error("Job not found. Not rescheduling.")
        return

    result = job.meta.get('result', None)

    # Update the task
    task = jobdb.task
    task.status = FetchTask.Status.FAILED
    task.last_execution = datetime.datetime.now(datetime.timezone.utc)
    task.num_failures += 1
    task.save()

    # Update the job result
    jobdb.status = Job.Status.FAILED
    jobdb.result = result.to_dict() if result else None
    jobdb.logs = job.meta.get('log', None)
    jobdb.save()

    logger.error(f"Job #{job.id} (task: {task.id}) failed; error: {value}")

    task_max_retries = settings.PERCEVAL_JOB_MAX_RETRIES

    # Retry the task if possible
    try:
        bklass = perceval.backend.find_backends(perceval.backends)[0][task.backend]
    except KeyError:
        bklass = None

    if not bklass or not bklass.has_resuming():
        logger.error(f"Job #{job.id} (task: {task.id}) unable to resume; cancelled")
    elif task.num_failures >= task_max_retries:
        logger.error(f"Job #{job.id} (task: {task.id}) max retries reached; cancelled")
    else:
        logger.error(f"Job #{job.id} (task: {task.id}) failed but task will be retried")
        task.status = FetchTask.Status.RECOVERY

        job_args = None
        if result and result.summary:
            backend = get_scheduler_backend(task.backend)
            job_args = backend.recovery_params(
                result.summary, jobdb.backend_args
            )

        scheduled_datetime = datetime.datetime.now(
            datetime.timezone.utc
        ) + datetime.timedelta(seconds=settings.PERCEVAL_JOB_RETRY_INTERVAL)
        enqueue_task(task, scheduled_datetime=scheduled_datetime, job_args=job_args)
