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
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    IntegerField,
    JSONField,
    PositiveIntegerField,
    IntegerChoices,
    ForeignKey,
    CASCADE,
)
from django.utils.translation import gettext_lazy as _

from grimoirelab_toolkit.datetime import datetime_utcnow

from ..models import (
    BaseModel,
    MAX_SIZE_CHAR_FIELD,
    MAX_SIZE_CHAR_INDEX,
)


if typing.TYPE_CHECKING:
    from typing import Any, Self, Callable, Iterator


GRIMOIRELAB_TASK_PREFIX = "grimoire:task:"
GRIMOIRELAB_JOB_PREFIX = "grimoire:job:"


class SchedulerStatus(IntegerChoices):
    """Types of task and job status."""

    NEW = 1, _("new")
    ENQUEUED = 2, _("enqueued")
    RUNNING = 3, _("running")
    COMPLETED = 4, _("completed")
    FAILED = 5, _("failed")
    RECOVERY = 6, _("recovery")
    CANCELED = 7, _("canceled")


class Task(BaseModel):
    """Base class for tasks to be executed by the scheduler.

    A task is a scheduled and recurrent work. Each run of the task
    is called a job.

    The life cycle of a task starts when is created and added
    to the system (`NEW` status). When the scheduler picks the task
    and plans to execute it, a new job will be created and added to
    a queue. The status will be 'ENQUEUED'.

    The job will stay in the queue until one worker is free to execute
    it. Then, the status of the task will be set to 'RUNNING'.

    Depending on the result of the job, the task will be set to
    'COMPLETED', if the task was executed successfully, or 'FAILED',
    if there was an error. Then, the task will be scheduled again.

    Tasks that were cancelled or interrupted while running that
    can be resumed will be mark as 'RECOVERY'.

    This class is an abstract class and should be inherited by
    implementing methods to create the task, prepare the job
    parameters for running the task, and determine if the task can be
    retried. Also, the function to be executed by the job, and the
    callback functions to be called when the job is successful or fails
    must be provided.
    """

    TASK_TYPE = "task"

    # Task data
    uuid = CharField(max_length=MAX_SIZE_CHAR_INDEX, unique=True)
    task_type = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    task_args = JSONField(null=True, default=None)

    # Status data
    status = IntegerField(
        choices=SchedulerStatus.choices,
        default=SchedulerStatus.NEW,
    )
    runs = PositiveIntegerField(default=0)
    failures = PositiveIntegerField(default=0)
    last_run = DateTimeField(null=True, default=None)

    # Scheduling configuration
    scheduled_at = DateTimeField(null=True, default=None)
    job_interval = PositiveIntegerField(default=settings.GRIMOIRELAB_JOB_INTERVAL)
    job_max_retries = PositiveIntegerField(
        null=True,
        default=settings.GRIMOIRELAB_JOB_MAX_RETRIES,
    )
    burst = BooleanField(default=False)

    class Meta:
        abstract = True

    @classmethod
    def create_task(
        cls,
        task_args: dict[str, Any],
        job_interval: int,
        job_max_retries: int,
        burst: bool = False,
        *args,
        **kwargs,
    ) -> Self:
        """Create a new task.

        Create and save a new task with the given arguments.

        :param task_args: arguments to be passed to the task.
        :param job_interval: interval in seconds between each task execution.
        :param job_max_retries: maximum number of retries before the task is
            considered failed.
        :param burst: flag to indicate if the task will only run once.
        :param args: additional arguments.
        :param kwargs: additional keyword arguments.
        """
        task = cls(
            uuid=str(uuid.uuid4()),
            task_type=cls.TASK_TYPE,
            task_args=task_args,
            job_interval=job_interval,
            job_max_retries=job_max_retries,
            burst=burst,
        )
        task.save()
        return task

    def save_run(self, status: SchedulerStatus) -> None:
        """Save the result of the task execution.

        This method will update the internal state of the task after a run,
        according to the new status given as argument.

        :param status: new status of the task.
        """
        self.runs += 1
        self.last_run = datetime_utcnow()

        if status == SchedulerStatus.FAILED:
            self.failures += 1
        else:
            self.failures = 0
        self.status = status
        self.save()

    def prepare_job_parameters(self) -> dict[str, Any]:
        """Generate the parameters for running the job."""

        raise NotImplementedError

    def can_be_retried(self) -> bool:
        """Check if the task can be retried."""

        raise NotImplementedError

    @property
    def task_id(self) -> str:
        """Return the task id."""

        return f"{GRIMOIRELAB_TASK_PREFIX}{self.uuid}"

    @property
    def default_job_queue(self) -> str:
        """Return the default queue for the job."""

        raise NotImplementedError

    @staticmethod
    def job_function(*args, **kwargs) -> Callable:
        """Return the function that will be executed by the job."""

        raise NotImplementedError

    @staticmethod
    def on_success_callback(self) -> Callable:
        """Return the function to be called when the job is successful."""

        raise NotImplementedError

    @staticmethod
    def on_failure_callback(self) -> Callable:
        """Return the function to be called when the job fails."""

        return NotImplementedError


class JobResultEncoder(DjangoJSONEncoder):
    """JSON encoder for job results."""

    def default(self, o):
        try:
            return o.__dict__
        except AttributeError:
            return super().default(o)


class JobArgsEncoder(DjangoJSONEncoder):
    """JSON encoder for job arguments."""

    def default(self, o):
        if isinstance(o, User):
            return o.username
        return DjangoJSONEncoder.default(self, o)


class Job(BaseModel):
    """Base class for jobs executed by the scheduler.

    A job is a single execution of a task. Its life cycle
    starts when it is `ENQUEUED`.

    The job will advance in the queue while other jobs are
    executed. Right after it gets to the head of the queue and a
    worker is free it will execute. The job will be `RUNNING`.

    Depending on the result executing the job, the outcomes will
    be different. If the job executed successfully, the job
    will be set to `COMPLETED`. If there was an error the status
    will be `FAILED`.
    """

    # Job data
    uuid = CharField(max_length=MAX_SIZE_CHAR_INDEX, unique=True)
    job_num = PositiveIntegerField(null=False)
    job_args = JSONField(encoder=JobArgsEncoder, null=True, default=None)

    # Status
    status = IntegerField(choices=SchedulerStatus.choices, default=SchedulerStatus.ENQUEUED)
    progress = JSONField(encoder=JobResultEncoder, null=True, default=None)
    logs = JSONField(null=True, default=None)

    # Scheduling
    queue = CharField(max_length=MAX_SIZE_CHAR_FIELD, null=True, default=None)
    scheduled_at = DateTimeField(null=True, default=None)
    started_at = DateTimeField(null=True, default=None)
    finished_at = DateTimeField(null=True, default=None)

    class Meta:
        abstract = True

    def save_run(
        self, status: SchedulerStatus, progress: Any = None, logs: list[str] = None
    ) -> None:
        """Save the result of the job and task execution.

        This method will update the internal state of the job after a run,
        and the task related to this job. They will be updated according
        to the new status given as argument.

        :param status: new status of the task.
        :param progress: progress of the job.
        :param logs: logs generated while running the job.
        """
        self.finished_at = datetime_utcnow()
        self.status = status
        self.progress = progress
        self.logs = logs
        self.save()
        self.task.save_run(status)

    @property
    def job_id(self) -> str:
        """Return the job id."""

        return f"{GRIMOIRELAB_JOB_PREFIX}{self.uuid}"


def _create_job_class(task_class: type[Task]) -> type[Job]:
    """Create a new job class related to the given task class.

    The job class will be created with the same name of the
    task class but replacing 'Task' by 'Job' suffix. Jobs of
    the new class will be accessible through the task class
    using the related name 'jobs'.

    :param task_class: the task class to be related to the new job class.

    :returns: the new job class.
    """
    class_name = task_class.__name__.replace("Task", "Job")
    job_class = type(
        class_name,
        (Job,),
        {
            "task": ForeignKey(
                task_class,
                on_delete=CASCADE,
                related_name="jobs",
            ),
            "__module__": task_class.__module__,
        },
    )
    return job_class


GRIMOIRELAB_TASK_MODELS = {}


def register_task_model(task_type: str, task_class: type[Task]) -> tuple[type[Task], type[Job]]:
    """Register a new task model type.

    The new task model will be registered with the name specified.
    A job model related to the task will be created and registered,
    too. The job class will be created with the same name of the
    task class but replacing 'Task' by 'Job' suffix.

    This function will raise an exception if any previous task
    type with the same name has been already registered.

    :param task_type: name of the task type.
    :param task_class: the task class and job class associated
        to the given type.

    :returns: a tuple with the task class and the job class

    :raises ValueError: if the task type is already registered.
    """
    if task_type in GRIMOIRELAB_TASK_MODELS:
        raise ValueError(f"{task_type} task type is already registered")

    job_class = _create_job_class(task_class)

    GRIMOIRELAB_TASK_MODELS[task_type] = (task_class, job_class)

    return task_class, job_class


def get_registered_task_model(task_type: str) -> tuple[type[Task], type[Job]]:
    """Return the task class of the given type.

    :param task_type: type of the task to be returned.

    :returns: the task class and job class associated
        to the given type.

    :raises KeyError: if the task type is not registered.
    """
    if task_type not in GRIMOIRELAB_TASK_MODELS:
        raise KeyError(f"{task_type} is not a valid task type")

    return GRIMOIRELAB_TASK_MODELS[task_type]


def get_all_registered_task_models() -> Iterator[tuple[type[Task], type[Job]]]:
    """Return all registered task models.

    :returns: an iterator with all registered task classes and
        job classes.
    """
    return iter(GRIMOIRELAB_TASK_MODELS.values())


def get_all_registered_task_names() -> list[str]:
    """Return all registered task names.

    :returns: a list with all registered task names.
    """
    return list(GRIMOIRELAB_TASK_MODELS.keys())
