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

from django.db.models import CharField

from ...scheduler.models import (
    SchedulerStatus,
    Task,
    register_task_model
)
from ...scheduler.scheduler import (
    _on_success_callback,
    _on_failure_callback
)
from ...models import MAX_SIZE_CHAR_FIELD
from .chronicler import (
    chronicler_job,
    ChroniclerProgress,
    get_chronicler_argument_generator
)

if typing.TYPE_CHECKING:
    from typing import Any, Self


class EventizerTask(Task):
    """Task to fetch and eventize data.

    This task will fetch data from a software development repository
    and convert it into events. Fetched data and events will be
    published to a Redis queue. The progress of the task can be accessed
    through the property `progress`. The result of the task can be obtained
    accessing to the property `result` of the object.

    Data will be fetched using `perceval` and eventized using
    `chronicler`.

    :param datasource_type: type of the datasource
        (e.g., 'git', 'github')
    :param datasource_category: category of the datasource
        (e.g., 'pull_request', 'issue')
    :param job_args: extra arguments to pass to the job
        (e.g., 'url', 'owner', 'repository')
    """
    datasource_type = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    datasource_category = CharField(max_length=MAX_SIZE_CHAR_FIELD)

    TASK_TYPE = 'eventizer'

    @classmethod
    def create_task(
        cls,
        task_args: dict[str, Any],
        job_interval: int,
        job_max_retries: int,
        datasource_type: str,
        datasource_category: str,
        burst: bool = False,
        *args, **kwargs
    ) -> Self:
        """Create a new task to eventize data.

        This method will create a new task to eventize data from a
        a repository. Besides the common arguments to create a task,
        this method requires the type of the datasource and the category
        of items to eventize.

        :param task_args: arguments to pass to the task.
        :param job_interval: interval in seconds between each task execution.
        :param job_max_retries: maximum number of retries before the task is
            considered failed.
        :param datasource_type: type of the datasource.
        :param datasource_category: category of the item to eventize.
        :param burst: flag to indicate if the task will only run once.
        :param args: additional arguments.
        :param kwargs: additional keyword arguments.

        :return: the new task created.
        """
        task = super().create_task(
            task_args, job_interval, job_max_retries, burst=burst,
            *args, **kwargs
        )
        task.datasource_type = datasource_type
        task.datasource_category = datasource_category
        task.save()

        return task

    def prepare_job_parameters(self):
        """Generate the parameters for a new job.

        This method will generate the parameters for a new job
        based on the original parameters set for the task plus
        the latest job parameters used. Depending on the status
        of the task, new parameters will be generated.
        """
        task_args = {
            'datasource_type': self.datasource_type,
            'datasource_category': self.datasource_category,
            'events_queue': 'events'
        }

        args_gen = get_chronicler_argument_generator(self.datasource_type)

        # Get the latest job arguments used and use them
        # to prepare the new job arguments.
        if self.status == SchedulerStatus.NEW:
            job_args = args_gen.initial_args(self.task_args)
        elif self.status == SchedulerStatus.COMPLETED:
            job = self.jobs.all().order_by('-job_num').first()
            progress = ChroniclerProgress.from_dict(job.progress)
            job_args = args_gen.resuming_args(job.job_args['job_args'], progress)
        elif self.status == SchedulerStatus.RECOVERY:
            job = self.jobs.all().order_by('-job_num').first()
            progress = ChroniclerProgress.from_dict(job.progress)
            job_args = args_gen.recovery_args(job.job_args['job_args'], progress)
        else:
            job_args = self.task_args

        task_args['job_args'] = job_args

        return task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return 'default'

    @staticmethod
    def job_function(*args, **kwargs):
        return chronicler_job(*args, **kwargs)

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)


register_task_model(EventizerTask.TASK_TYPE, EventizerTask)
