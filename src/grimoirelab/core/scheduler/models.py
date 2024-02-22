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

from django.db.models import (CharField,
                              DateTimeField,
                              JSONField,
                              IntegerChoices,
                              Model,
                              PositiveIntegerField, IntegerField)

from grimoirelab_toolkit.datetime import datetime_utcnow

from .common import MAX_JOB_RETRIES, TASK_PREFIX, DEFAULT_JOB_INTERVAL

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
        NEW = 1
        ENQUEUED = 2
        RUNNING = 3
        COMPLETED = 4
        FAILED = 5

    backend = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    category = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    backend_args = JSONField(null=True, default=None)
    status = IntegerField(choices=Status.choices, default=Status.NEW)
    age = PositiveIntegerField(default=0)
    executions = PositiveIntegerField(default=0)
    num_failures = PositiveIntegerField(default=0)
    job_id = CharField(max_length=MAX_SIZE_CHAR_FIELD, null=True, default=None)
    queue = CharField(max_length=MAX_SIZE_CHAR_FIELD, null=True, default=None)
    # Scheduling configuration
    scheduled_datetime = DateTimeField(null=True, default=None)
    interval = PositiveIntegerField(default=DEFAULT_JOB_INTERVAL)
    max_retries = PositiveIntegerField(null=True, default=MAX_JOB_RETRIES)
    last_execution = DateTimeField(null=True, default=None)

    @property
    def task_id(self):
        return f"{TASK_PREFIX}{self.pk}"

    class Meta:
        db_table = 'fetch_tasks'
