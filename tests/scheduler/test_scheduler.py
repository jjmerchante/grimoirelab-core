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
import unittest.mock

from grimoirelab.core.scheduler.models import FetchTask, Job as DBJob
from grimoirelab.core.scheduler.scheduler import schedule_task, enqueue_task
from grimoirelab.core.scheduler.jobs import JobResult
from .base import TestBaseRQ


def mock_perceval_job(*args, **kwargs):
    return JobResult(job_id='job_1', task_id='task_1',
                     backend='backend_1', category='category_1')


class TestScheduler(TestBaseRQ):
    """Unit tests for scheduler functions"""

    @unittest.mock.patch('grimoirelab.core.scheduler.jobs.PercevalJob.run',
                         mock_perceval_job)
    def test_schedule_task(self):
        """Test to schedule a task"""

        backend_args = {
            "gitpath": '/tmp/1',
            "uri": 'https://example.com/example.git'
        }
        task = schedule_task(backend='backend_1',
                             category='category_1',
                             backend_args=backend_args,
                             queue_id='default',
                             interval=360,
                             max_retries=10)

        self.assertIsInstance(task, FetchTask)
        self.assertEqual(task.backend, 'backend_1')
        self.assertEqual(task.category, 'category_1')
        self.assertEqual(task.backend_args, backend_args)
        self.assertEqual(task.age, 1)
        self.assertEqual(task.queue, 'default')
        self.assertEqual(task.interval, 360)
        self.assertEqual(task.max_retries, 10)
        self.assertEqual(task.task_id, f'grimoire:task:{task.pk}')

    def test_enqueue_job(self):
        """Test to enqueue a job"""

        backend_args = {
            "gitpath": '/tmp/1',
            "uri": 'https://example.com/example.git'
        }
        task = FetchTask.objects.create(backend='backend_1',
                                        category='category_1',
                                        backend_args=backend_args,
                                        queue='default',
                                        interval=360,
                                        max_retries=10)
        scheduled_datetime = datetime.datetime.now(datetime.timezone.utc)
        job = enqueue_task(task=task,
                           scheduled_datetime=scheduled_datetime)
        # Task updated
        self.assertIsInstance(task, FetchTask)
        self.assertEqual(task.backend, 'backend_1')
        self.assertEqual(task.category, 'category_1')
        self.assertEqual(task.backend_args, backend_args)
        self.assertEqual(task.age, 1)
        self.assertEqual(task.scheduled_datetime, scheduled_datetime)
        self.assertEqual(task.queue, 'default')
        self.assertEqual(task.interval, 360)
        self.assertEqual(task.max_retries, 10)
        self.assertEqual(task.task_id, f'grimoire:task:{task.pk}')

        self.assertIsInstance(job, DBJob)
        self.assertEqual(job.task, task)
        self.assertEqual(job.backend, 'backend_1')
        self.assertEqual(job.category, 'category_1')
        self.assertEqual(job.queue, 'default')
        self.assertEqual(job.scheduled_datetime, scheduled_datetime)
