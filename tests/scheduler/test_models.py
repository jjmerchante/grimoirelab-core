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
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#
import datetime

from django.conf import settings
from django.test import TransactionTestCase

from grimoirelab_toolkit.datetime import datetime_utcnow

from grimoirelab.core.scheduler.models import FetchTask, Job


class TestFetchTask(TransactionTestCase):
    """Unit tests for FetchTask class"""

    def test_create_task(self):
        """Test task creation"""

        backend_args = {
            "uri": "https://example.com/a.git"
        }
        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')

        self.assertEqual(task.backend, 'backend')
        self.assertEqual(task.category, 'category_1')
        self.assertEqual(task.backend_args, backend_args)
        self.assertEqual(task.status, FetchTask.Status.NEW)
        self.assertEqual(task.age, 0)
        self.assertEqual(task.executions, 0)
        self.assertEqual(task.num_failures, 0)
        self.assertEqual(task.queue, 'default')
        self.assertEqual(task.interval, settings.PERCEVAL_JOB_INTERVAL)
        self.assertEqual(task.max_retries, settings.PERCEVAL_JOB_MAX_RETRIES)
        self.assertEqual(task.last_execution, None)
        self.assertEqual(task.task_id, f'grimoire:task:{task.pk}')

    def test_created_at(self):
        """Check creation date is only set when the object is created"""

        before_dt = datetime_utcnow()
        backend_args = {
            "uri": "https://example.com/a.git"
        }
        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')
        after_dt = datetime_utcnow()

        self.assertEqual(task.backend, 'backend')
        self.assertEqual(task.category, 'category_1')
        self.assertGreaterEqual(task.created_at, before_dt)
        self.assertLessEqual(task.created_at, after_dt)

        task.backend = 'backend_2'
        task.save()

        self.assertEqual(task.backend, "backend_2")
        self.assertGreaterEqual(task.created_at, before_dt)
        self.assertLessEqual(task.created_at, after_dt)

    def test_last_modified(self):
        """Check last modification date is set when the object is updated"""

        before_dt = datetime_utcnow()
        backend_args = {
            "uri": "https://example.com/a.git"
        }
        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')
        after_dt = datetime_utcnow()

        self.assertEqual(task.backend, 'backend')
        self.assertGreaterEqual(task.last_modified, before_dt)
        self.assertLessEqual(task.last_modified, after_dt)

        before_modified_dt = datetime_utcnow()
        task.backend = 'Backend_2'
        task.save()
        after_modified_dt = datetime_utcnow()

        self.assertEqual(task.backend, 'Backend_2')
        self.assertGreaterEqual(task.last_modified, before_modified_dt)
        self.assertLessEqual(task.last_modified, after_modified_dt)


class TestJob(TransactionTestCase):
    """Unit tests for Job class"""

    def test_create_task(self):
        """Test job creation"""

        backend_args = {
            "uri": "https://example.com/a.git"
        }
        scheduled_datetime = datetime.datetime.now(datetime.timezone.utc)

        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')
        job = Job.objects.create(
            job_id='job-id-1',
            task=task,
            backend=task.backend,
            category=task.category,
            backend_args=backend_args,
            queue=task.queue,
            scheduled_datetime=scheduled_datetime
        )

        self.assertEqual(job.job_id, 'job-id-1')
        self.assertEqual(job.task, task)
        self.assertEqual(job.backend, 'backend')
        self.assertEqual(job.category, 'category_1')
        self.assertEqual(job.backend_args, backend_args)
        self.assertEqual(job.queue, 'default')
        self.assertEqual(job.scheduled_datetime, scheduled_datetime)
        self.assertEqual(job.result, None)
        self.assertEqual(job.logs, None)

    def test_created_at(self):
        """Check creation date is only set when the object is created"""

        before_dt = datetime_utcnow()
        backend_args = {
            "uri": "https://example.com/a.git"
        }
        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')
        job = Job.objects.create(
            job_id='job-id-2',
            task=task,
            backend=task.backend,
            category=task.category,
            queue=task.queue
        )
        after_dt = datetime_utcnow()

        self.assertEqual(job.backend, 'backend')
        self.assertEqual(job.category, 'category_1')
        self.assertGreaterEqual(job.created_at, before_dt)
        self.assertLessEqual(job.created_at, after_dt)

        job.backend = 'backend_2'
        job.save()

        self.assertEqual(job.backend, "backend_2")
        self.assertGreaterEqual(job.created_at, before_dt)
        self.assertLessEqual(job.created_at, after_dt)

    def test_last_modified(self):
        """Check last modification date is set when the object is updated"""

        before_dt = datetime_utcnow()
        backend_args = {
            "uri": "https://example.com/a.git"
        }
        task = FetchTask.objects.create(backend='backend',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default')
        job = Job.objects.create(
            job_id='job-id-2',
            task=task,
            backend=task.backend,
            category=task.category,
            queue=task.queue
        )
        after_dt = datetime_utcnow()

        self.assertEqual(job.backend, 'backend')
        self.assertGreaterEqual(job.last_modified, before_dt)
        self.assertLessEqual(job.last_modified, after_dt)

        before_modified_dt = datetime_utcnow()
        job.backend = 'Backend_2'
        job.save()
        after_modified_dt = datetime_utcnow()

        self.assertEqual(job.backend, 'Backend_2')
        self.assertGreaterEqual(job.last_modified, before_modified_dt)
        self.assertLessEqual(job.last_modified, after_modified_dt)
