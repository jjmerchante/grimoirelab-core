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

from django.test import TransactionTestCase

from grimoirelab.core.scheduler.common import (DEFAULT_JOB_INTERVAL,
                                               MAX_JOB_RETRIES)
from grimoirelab_toolkit.datetime import datetime_utcnow

from grimoirelab.core.scheduler.models import FetchTask


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
        self.assertEqual(task.status, FetchTask.Status.NEW)
        self.assertEqual(task.age, 0)
        self.assertEqual(task.executions, 0)
        self.assertEqual(task.num_failures, 0)
        self.assertEqual(task.job_id, None)
        self.assertEqual(task.queue, 'default')
        self.assertEqual(task.interval, DEFAULT_JOB_INTERVAL)
        self.assertEqual(task.max_retries, MAX_JOB_RETRIES)
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
