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

import datetime
import logging
import typing
import uuid

import django_rq
import rq.exceptions
import rq.job

from django.conf import settings

from grimoirelab_toolkit.datetime import datetime_utcnow

from .db import (
    find_tasks_by_status,
    find_job,
    find_task
)
from .errors import NotFoundError
from .models import (
    Job,
    SchedulerStatus,
    Task,
    get_registered_task_model
)

if typing.TYPE_CHECKING:
    import redis
    from typing import Any


logger = logging.getLogger(__name__)


def schedule_task(
    task_type: str,
    task_args: dict[str, Any],
    job_interval: int = settings.GRIMOIRELAB_JOB_INTERVAL,
    job_max_retries: int = settings.GRIMOIRELAB_JOB_MAX_RETRIES,
    burst: bool = False,
    *args, **kwargs
) -> Task:
    """Schedule a task to be executed in the future.

    :param task_type: type of task to be scheduled.
    :param task_args: arguments to be passed to the task.
    :param job_interval: interval in seconds between each task execution.
    :param job_max_retries: maximum number of retries before the task
        is considered failed.
    :param burst: flag to indicate if the task will only run once.

    :return: the scheduled task object.
    """
    task_class, _ = get_registered_task_model(task_type)
    task = task_class.create_task(
        task_args, job_interval, job_max_retries, burst=burst,
        *args, **kwargs
    )
    _enqueue_task(
        task,
        scheduled_at=datetime_utcnow()
    )

    return task


def cancel_task(task_uuid: str) -> None:
    """Cancel a task that is scheduled and delete all its jobs.

    The task will be deleted from the database and all its jobs
    too. Pending jobs will be also canceled and removed.

    :param task_uuid: uuid of the task to be cancelled.

    :raises NotFoundError: when the task is not found.
    """
    task = find_task(task_uuid)

    _, job_class = get_registered_task_model(task.TASK_TYPE)

    jobs = job_class.objects.filter(task=task).all()
    for job in jobs:
        job_rq = rq.job.Job.fetch(job.uuid, connection=django_rq.get_connection())
        job_rq.delete()

    task.delete()


def maintain_tasks() -> None:
    """Maintain the tasks that are scheduled to be executed.

    This function will check the status of the tasks and jobs
    that are scheduled, rescheduling them if necessary.
    """
    tasks = find_tasks_by_status(
        [
            SchedulerStatus.RUNNING,
            SchedulerStatus.RECOVERY,
            SchedulerStatus.ENQUEUED,
            SchedulerStatus.NEW
        ]
    )

    for task in tasks:
        job_db = task.jobs.order_by('scheduled_at').first()

        try:
            rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
            continue
        except rq.exceptions.NoSuchJobError:
            logger.debug(
                f"Job #{job_db.job_id} in queue (task: {task.task_id}) missing. Rescheduling."
            )

        current_time = datetime_utcnow()
        scheduled_at = task.scheduled_at if task.scheduled_at > current_time else current_time

        _schedule_job(task, job_db, scheduled_at, job_db.job_args)


def _enqueue_task(
    task: Task,
    scheduled_at: datetime.datetime | None = None
) -> Job:
    """Enqueue the task to be executed in the future.

    A new job for the task will be created and enqueued in the
    best queue available. This job will be scheduled to execute
    at the time specified by the parameter 'scheduled_at'. When
    this parameter is not set, the job will be run as soon as
    possible.

    :param task: task to be enqueued.
    :param scheduled_at: datetime when the task should be executed.

    :return: the job object created.
    """
    if not scheduled_at:
        scheduled_at = datetime_utcnow()

    job_args = task.prepare_job_parameters()
    queue = task.default_job_queue

    _, job_class = get_registered_task_model(task.task_type)

    job = job_class.objects.create(
        uuid=str(uuid.uuid4()),
        job_num=job_class.objects.filter(task=task).count() + 1,
        job_args=job_args,
        queue=queue,
        scheduled_at=scheduled_at,
        task=task
    )

    _schedule_job(task, job, scheduled_at, job_args)

    logger.info(
        f"Job #{job.job_id} (task: {task.task_id})"
        f" enqueued in '{job.queue}' at {scheduled_at}"
    )

    return job


def _schedule_job(
    task: Task,
    job: Job,
    scheduled_at: datetime.datetime,
    job_args: dict[str, Any]
) -> rq.job.Job:
    """Schedule the job to be executed."""

    queue = task.default_job_queue

    try:
        queue_rq = django_rq.get_queue(queue)
        rq_job = queue_rq.enqueue_at(
            datetime=scheduled_at,
            f=task.job_function,
            result_ttl=settings.GRIMOIRELAB_JOB_RESULT_TTL,
            job_timeout=settings.GRIMOIRELAB_JOB_TIMEOUT,
            on_success=task.on_success_callback,
            on_failure=task.on_failure_callback,
            job_id=job.uuid,
            **job_args,
        )

        job.status = SchedulerStatus.ENQUEUED
        task.status = SchedulerStatus.ENQUEUED
        task.scheduled_at = scheduled_at
    except Exception as e:
        logger.error(f"Error enqueuing job of task {task.task_id}. Not scheduled. Error: {e}")
        job.status = SchedulerStatus.FAILED
        task.status = SchedulerStatus.FAILED
        raise e
    finally:
        job.save()
        task.save()

    return rq_job


def _on_success_callback(
    job: rq.job.Job,
    connection: redis.Redis,
    result: Any,
    *args,
    **kwargs
) -> None:
    """Reschedule the job based on the interval defined by the task.

    The new arguments for the job are obtained from the result
    of the job object.
    """
    try:
        job_db = find_job(job.id)
    except NotFoundError:
        logger.error("Job not found. Not rescheduling.")
        return

    job_db.save_run(SchedulerStatus.COMPLETED,
                    progress=result, logs=job.meta.get('log', None))
    task = job_db.task

    logger.info(
        f"Job #{job_db.job_id} (task: {task.task_id}) completed."
    )

    # Reschedule task
    if task.burst:
        logger.info(f"Task: {task.task_id} finished. It was a burst task. It won't be rescheduled.")
        return
    else:
        scheduled_at = datetime_utcnow() + datetime.timedelta(seconds=task.job_interval)
        _enqueue_task(task, scheduled_at=scheduled_at)


def _on_failure_callback(
    job: rq.job.JobRQ,
    connection: redis.Redis,
    t: Any,
    value: Any,
    traceback: Any
):
    """Reschedule the job when it failed.

    The function will try to reschedule again the job. This means
    that in some cases, it will have to try to recover from the
    point it failed.

    If the job reached the number of retries, it will be cancelled.

    The new arguments for the job are obtained from the result
    of the job object.
    """
    try:
        job_db = find_job(job.id)
    except NotFoundError:
        logger.error("Job not found. Not rescheduling.")
        return

    job_db.save_run(SchedulerStatus.FAILED,
                    progress=job.meta['progress'],
                    logs=job.meta.get('log', None))
    task = job_db.task

    logger.error(
        f"Job #{job_db.job_id} (task: {task.task_id}) failed; error: {value}"
    )

    # Try to retry the task
    if task.failures >= task.job_max_retries:
        logger.error(
            f"Task: {task.task_id} max retries reached; cancelled"
        )
        return
    elif not task.can_be_retried():
        logger.error(f"Task: {task.task_id} can't be retried")
        return
    else:
        logger.error(f"Task: {task.task_id} failed but task will be retried")
        task.status = SchedulerStatus.RECOVERY
        task.save()

    scheduled_at = datetime_utcnow() + datetime.timedelta(seconds=task.job_interval)
    _enqueue_task(task, scheduled_at=scheduled_at)
