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

from django.conf import settings
from django.db.models import (CharField,
                              DateTimeField,
                              JSONField,
                              IntegerChoices,
                              Model,
                              PositiveIntegerField,
                              IntegerField,
                              ForeignKey,
                              CASCADE)
from django.utils.translation import gettext_lazy as _

from grimoirelab_toolkit.datetime import datetime_utcnow


# Innodb and utf8mb4 can only index 191 characters
# For more information regarding this topic see:
# https://dev.mysql.com/doc/refman/5.5/en/charset-unicode-conversion.html
MAX_SIZE_CHAR_INDEX = 191
MAX_SIZE_CHAR_FIELD = 128


class CreationDateTimeField(DateTimeField):
    """Field automatically set to the current date when an object is created."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('editable', False)
        kwargs.setdefault('default', datetime_utcnow)
        super().__init__(*args, **kwargs)


class LastModificationDateTimeField(DateTimeField):
    """Field automatically set to the current date on each save() call."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('editable', False)
        kwargs.setdefault('default', datetime_utcnow)
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        value = datetime_utcnow()
        setattr(model_instance, self.attname, value)
        return value


class EntityBase(Model):
    created_at = CreationDateTimeField()
    last_modified = LastModificationDateTimeField()

    class Meta:
        abstract = True


class Task(EntityBase):
    pass


class FetchTask(Task):
    class Status(IntegerChoices):
        """
        The life cycle of a task starts when is created and added
        to the system as `NEW`. It will remain in this status until
        its job is `ENQUEUED`.

        The job will advance in the queue while other jobs are
        executed. Right after it gets to the head of the queue and a
        worker is free it will execute. The task will be `RUNNING`.

        Depending on the result executing the job, the outcomes will
        be different. If the job executed successfully, the task
        will be set to `COMPLETED`. If there was an error the status
        will be `FAILED`.

        Recurring tasks, that were successful, will be re-scheduled
        again (`ENQUEUED`), stating a new cycle.
        """
        NEW = 1, _("new")
        ENQUEUED = 2, _("enqueued")
        RUNNING = 3, _("running")
        COMPLETED = 4, _("completed")
        FAILED = 5, _("failed")
        RECOVERY = 6, _("recovery")

    backend = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    category = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    backend_args = JSONField(null=True, default=None)
    status = IntegerField(choices=Status.choices, default=Status.NEW)
    age = PositiveIntegerField(default=0)
    executions = PositiveIntegerField(default=0)
    num_failures = PositiveIntegerField(default=0)
    queue = CharField(max_length=MAX_SIZE_CHAR_FIELD, null=True, default=None)
    # Scheduling configuration
    scheduled_datetime = DateTimeField(null=True, default=None)
    interval = PositiveIntegerField(default=settings.PERCEVAL_JOB_INTERVAL)
    max_retries = PositiveIntegerField(null=True, default=settings.PERCEVAL_JOB_MAX_RETRIES)
    last_execution = DateTimeField(null=True, default=None)

    @property
    def task_id(self):
        return f"{settings.TASK_PREFIX}{self.pk}"

    class Meta:
        db_table = 'fetch_tasks'


class Job(EntityBase):
    class Status(IntegerChoices):
        """
        The life cycle of a job starts when it is `ENQUEUED`.

        The job will advance in the queue while other jobs are
        executed. Right after it gets to the head of the queue and a
        worker is free it will execute. The job will be `RUNNING`.

        Depending on the result executing the job, the outcomes will
        be different. If the job executed successfully, the job
        will be set to `COMPLETED`. If there was an error the status
        will be `FAILED`.
        """
        ENQUEUED = 1, _("enqueued")
        RUNNING = 2, _("running")
        COMPLETED = 3, _("completed")
        FAILED = 4, _("failed")

    job_id = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    task = ForeignKey(FetchTask, on_delete=CASCADE, related_name='jobs')
    backend = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    category = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    backend_args = JSONField(null=True, default=None)
    status = IntegerField(choices=Status.choices, default=Status.ENQUEUED)
    queue = CharField(max_length=MAX_SIZE_CHAR_FIELD, null=True, default=None)
    scheduled_datetime = DateTimeField(null=True, default=None)
    result = JSONField(null=True, default=None)
    logs = JSONField(null=True, default=None)


# class Token(EntityBase):
#     backend = CharField(max_length=MAX_SIZE_CHAR_FIELD)
#     token = CharField(max_length=MAX_SIZE_CHAR_FIELD)
#
#     class Meta:
#         db_table = 'tokens'
