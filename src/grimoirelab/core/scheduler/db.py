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

import typing

from .models import SchedulerStatus, get_all_registered_task_models
from .errors import NotFoundError


if typing.TYPE_CHECKING:
    from typing import Iterator
    from .models import Task, Job


def find_tasks_by_status(statuses: list[SchedulerStatus]) -> Iterator[Task]:
    """Find tasks by their status.

    :param statuses: list of status to filter tasks by.

    :returns: iterator of tasks with the given status.
    """
    for task_class, _ in get_all_registered_task_models():
        yield from task_class.objects.filter(status__in=statuses).iterator()


def find_task(task_uuid: str) -> Task:
    """Find a task by its uuid.

    Due to the way the tasks are defined with Django,
    we need to iterate through all the task models to find
    the task.

    :param task_uuid: the task uuid to find.

    :returns: the task found
    .
    :raises NotFoundError: when the task is not found.
    """
    for task_class, _ in get_all_registered_task_models():
        try:
            task = task_class.objects.get(uuid=task_uuid)
        except task_class.DoesNotExist:
            continue
        else:
            return task
    raise NotFoundError(element=task_uuid)


def find_job(job_uuid: str) -> Job:
    """Find a job by its uuid.

    Due to the way the jobs are defined with Django,
    we need to iterate through all the job models to find
    the job.

    :param job_uuid: the job uuid to find.

    :returns: the job found.

    :raises NotFoundError: if the job is not found.
    """
    for _, job_class in get_all_registered_task_models():
        try:
            job = job_class.objects.get(uuid=job_uuid)
        except job_class.DoesNotExist:
            continue
        else:
            return job
    raise NotFoundError(element=job_uuid)
