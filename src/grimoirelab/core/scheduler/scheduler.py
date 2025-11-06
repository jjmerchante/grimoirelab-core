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
import typing
import uuid

import django.db
import django_rq
import rq.exceptions
import rq.job
import structlog

from django.conf import settings
from rq.registry import StartedJobRegistry
from rq.command import send_stop_job_command

from grimoirelab_toolkit.datetime import datetime_utcnow

from .db import (
    find_tasks_by_status,
    find_job,
    find_task,
)
from .errors import NotFoundError
from .models import (
    Job,
    SchedulerStatus,
    Task,
    get_registered_task_model,
)

if typing.TYPE_CHECKING:
    import redis
    from typing import Any


RQ_JOB_STOPPED_STATUS = [
    rq.job.JobStatus.FINISHED,
    rq.job.JobStatus.FAILED,
    rq.job.JobStatus.STOPPED,
    rq.job.JobStatus.CANCELED,
]


logger = structlog.get_logger(__name__)


def schedule_task(
    task_type: str,
    task_args: dict[str, Any],
    job_interval: int = settings.GRIMOIRELAB_JOB_INTERVAL,
    job_max_retries: int = settings.GRIMOIRELAB_JOB_MAX_RETRIES,
    burst: bool = False,
    *args,
    **kwargs,
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
        task_args, job_interval, job_max_retries, burst=burst, *args, **kwargs
    )
    _enqueue_task(task, scheduled_at=datetime_utcnow())

    logger.info(
        "task scheduled",
        task_uuid=task.uuid,
        task_args=task_args,
        job_interval=job_interval,
        job_max_retries=job_max_retries,
        burst=burst,
    )

    return task


def cancel_task(task_uuid: str) -> None:
    """Cancel a task that is scheduled and its jobs.

    The task will be cancelled and all the jobs that are scheduled.
    If the task is running, it will be stopped.

    :param task_uuid: uuid of the task to be cancelled.

    :raises NotFoundError: when the task is not found.
    """
    task = find_task(task_uuid)

    jobs = task.jobs.all()
    for job in jobs:
        connection = django_rq.get_connection(task.default_job_queue)
        try:
            job_rq = rq.job.Job.fetch(job.uuid, connection=connection)
        except rq.exceptions.NoSuchJobError:
            continue
        if job_rq.get_status() == rq.job.JobStatus.STARTED:
            send_stop_job_command(connection, job_rq.id)
        job_rq.delete()

        if job.status not in (SchedulerStatus.FAILED, SchedulerStatus.COMPLETED):
            job.status = SchedulerStatus.CANCELED
            job.save()

    if task.status not in (SchedulerStatus.COMPLETED, SchedulerStatus.FAILED):
        task.status = SchedulerStatus.CANCELED
        task.save()

    logger.info("task canceled", task_uuid=task.uuid)


def reschedule_task(task_uuid: str) -> None:
    """Reschedule a task

    The task will be rescheduled to be executed as soon
    as possible. If it is running, it will be cancelled and
    rescheduled.

    :param task_uuid: uuid of the task to be rescheduled.

    :raises NotFoundError: when the task is not found.
    """
    task = find_task(task_uuid)

    if task.status == SchedulerStatus.ENQUEUED:
        # Cancel the enqueued job and force the execution
        job = task.jobs.order_by("-scheduled_at").first()
        try:
            job_rq = rq.job.Job.fetch(
                job.uuid, connection=django_rq.get_connection(task.default_job_queue)
            )
            job_rq.delete()
        except (rq.exceptions.NoSuchJobError, rq.exceptions.InvalidJobOperation):
            pass
        _schedule_job(task, job, datetime_utcnow(), job.job_args)
    elif task.status == SchedulerStatus.RUNNING:
        # Make sure it is running
        job = task.jobs.order_by("-scheduled_at").first()
        if _is_job_removed_or_stopped(job, task.default_job_queue):
            job.save_run(SchedulerStatus.CANCELED)
            _enqueue_task(task)
    else:
        _enqueue_task(task)

    logger.info("task rescheduled", task_uuid=task.uuid)


def maintain_tasks() -> None:
    """Maintain the tasks that are scheduled to be executed.

    This function will check the status of the tasks and jobs
    that are scheduled, rescheduling them if necessary.
    """
    active_status = [
        SchedulerStatus.RUNNING,
        SchedulerStatus.RECOVERY,
        SchedulerStatus.ENQUEUED,
        SchedulerStatus.NEW,
    ]
    tasks = find_tasks_by_status(active_status)

    for task in tasks:
        job_db = task.jobs.filter(status__in=active_status).order_by("-scheduled_at").first()

        if not job_db:
            logger.error(
                "Task in active status but no active job found; rescheduling",
                task_uuid=task.uuid,
            )
            _enqueue_task(task, scheduled_at=datetime_utcnow())
            continue

        if not _is_job_removed_or_stopped(job_db, task.default_job_queue):
            continue

        logger.error(
            "Job stopped but task wasn't updated; rescheduling",
            task_uuid=task.uuid,
            job_uuid=job_db.uuid,
            queue=job_db.queue,
        )

        current_time = datetime_utcnow()
        scheduled_at = max(task.scheduled_at, current_time)

        job_db.save_run(SchedulerStatus.CANCELED)
        _enqueue_task(task, scheduled_at=scheduled_at)

    logger.debug("Maintenance of tasks completed")


def _is_job_removed_or_stopped(job: Job, queue: str) -> bool:
    """
    Check if the job was removed or stopped.

    :param job: job to check.
    :param queue: queue where the job is enqueued.
    """
    try:
        connection = django_rq.get_connection(queue)
        job_rq = rq.job.Job.fetch(job.uuid, connection=connection)
        status = job_rq.get_status()
        if status == rq.job.JobStatus.STARTED:
            # Sometimes, the worker may be forcibly stopped, leaving the job
            # in the STARTED status. We need to check if the job has expired
            # due to a missing heartbeat.
            try:
                expiration_date = StartedJobRegistry(queue, connection).get_expiration_time(job_rq)
            except TypeError:
                return True
            return expiration_date < datetime.datetime.now()
        else:
            return status in RQ_JOB_STOPPED_STATUS
    except rq.exceptions.NoSuchJobError:
        return True


def _enqueue_task(task: Task, scheduled_at: datetime.datetime | None = None) -> Job:
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
        task=task,
    )

    _schedule_job(task, job, scheduled_at, job_args)

    return job


def _schedule_job(
    task: Task, job: Job, scheduled_at: datetime.datetime, job_args: dict[str, Any]
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
            on_success=rq.job.Callback(task.on_success_callback),
            on_failure=rq.job.Callback(task.on_failure_callback),
            job_id=job.uuid,
            **job_args,
        )

        job.status = SchedulerStatus.ENQUEUED
        task.status = SchedulerStatus.ENQUEUED
        job.scheduled_at = scheduled_at
        task.scheduled_at = scheduled_at
    except Exception as ex:
        job.status = SchedulerStatus.FAILED
        task.status = SchedulerStatus.FAILED
        logger.error(
            "job scheduling",
            job_uuid=job.uuid,
            task_uuid=task.uuid,
            exc_info=ex,
        )
        raise ex
    finally:
        job.save()
        task.save()

    logger.info(
        "job scheduled",
        job_uuid=job.uuid,
        job_args=job_args,
        task_uuid=task.uuid,
        queue=job.queue,
        scheduled_at=scheduled_at,
    )

    return rq_job


def _on_success_callback(
    job: rq.job.Job, connection: redis.Redis, result: Any, *args, **kwargs
) -> None:
    """Reschedule the job based on the interval defined by the task.

    The new arguments for the job are obtained from the result
    of the job object.
    """
    # After long-running tasks, the connection may be closed.
    # Close unusable connections and let Django reopen them if needed.
    django.db.close_old_connections()

    try:
        job_db = find_job(job.id)
    except NotFoundError:
        logger.error("job not found", job_uuid=job.uuid)
        return

    job_db.save_run(
        SchedulerStatus.COMPLETED,
        progress=result,
        logs=job.meta.get("log", None),
    )
    task = job_db.task

    logger.info("job completed", job_uuid=job_db.uuid, task_uuid=task.uuid)

    # Reschedule task
    if task.burst:
        logger.info("task completed", task_uuid=task.uuid, burst=True)
        return
    else:
        scheduled_at = datetime_utcnow() + datetime.timedelta(seconds=task.job_interval)
        _enqueue_task(task, scheduled_at=scheduled_at)


def _on_failure_callback(
    job: rq.job.JobRQ, connection: redis.Redis, t: Any, value: Any, traceback: Any
):
    """Reschedule the job when it failed.

    The function will try to reschedule again the job. This means
    that in some cases, it will have to try to recover from the
    point it failed.

    If the job reached the number of retries, it will be cancelled.

    The new arguments for the job are obtained from the result
    of the job object.
    """
    # After long-running tasks, the connection may be closed.
    # Close unusable connections and let Django reopen them if needed.
    django.db.close_old_connections()

    try:
        job_db = find_job(job.id)
    except NotFoundError:
        logger.error("job not found", job_uuid=job.uuid)
        return

    job_db.save_run(
        SchedulerStatus.FAILED,
        progress=job.meta["progress"],
        logs=job.meta.get("log", None),
    )
    task = job_db.task

    logger.error("job failed", job_uuid=job_db.uuid, task_uuid=task.uuid, error=value)

    # Define new log to reuse parameters
    log = logger.bind(task_uuid=task.uuid, job_uuid=job_db.uuid)

    # Retry the task, if possible
    if task.failures >= task.job_max_retries:
        log.error("task failed; max retries reached", max_failures=task.failures)
        return
    elif not task.can_be_retried():
        log.error("task failed; can't be retried")
        return
    else:
        task.status = SchedulerStatus.RECOVERY
        task.save()
        scheduled_at = datetime_utcnow() + datetime.timedelta(seconds=task.job_interval)
        _enqueue_task(task, scheduled_at=scheduled_at)
        log.error("task failed; recovered")
