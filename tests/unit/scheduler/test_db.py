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

import django.db
import django.test.utils

from grimoirelab.core.scheduler.db import (
    find_tasks_by_status,
    find_task,
    find_job
)
from grimoirelab.core.scheduler.errors import NotFoundError
from grimoirelab.core.scheduler.models import (
    SchedulerStatus,
    Task,
    register_task_model,
    GRIMOIRELAB_TASK_MODELS
)

from ..base import GrimoireLabTestCase


class DummyTaskDB(Task):
    """Class for testing the task register"""

    TASK_TYPE = 'dummy_task'


class AnotherDummyTaskDB(Task):
    """Class for testing the task register"""

    TASK_TYPE = 'another_dummy_task'


class TestFindTasksByStatus(GrimoireLabTestCase):
    """Unit tests for find_task_by_status function"""

    @classmethod
    def setUpClass(cls):
        _, cls.DummyJobClass = register_task_model('dummy_task', DummyTaskDB)
        _, cls.AnotherDummyJobClass = register_task_model('another_dummy_task', AnotherDummyTaskDB)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        GRIMOIRELAB_TASK_MODELS.clear()
        super().tearDownClass()

    def setUp(self):
        """Create the test model"""

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.DummyJobClass)
                schema_editor.delete_model(DummyTaskDB)
                schema_editor.delete_model(self.AnotherDummyJobClass)
                schema_editor.delete_model(AnotherDummyTaskDB)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(DummyTaskDB)
            schema_editor.create_model(self.DummyJobClass)
            schema_editor.create_model(AnotherDummyTaskDB)
            schema_editor.create_model(self.AnotherDummyJobClass)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_find_tasks_by_status(self):
        """Find a task by status"""

        dummy_task = DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        dummy_task.status = SchedulerStatus.NEW
        dummy_task.save()

        another_dummy_task = AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        another_dummy_task.status = SchedulerStatus.NEW
        another_dummy_task.save()

        task = AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        task.status = SchedulerStatus.RUNNING
        task.save()

        task = DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        task.status = SchedulerStatus.FAILED
        task.save()

        expected = {
            dummy_task, another_dummy_task, task
        }

        result = find_tasks_by_status([SchedulerStatus.NEW, SchedulerStatus.FAILED])
        self.assertSetEqual(set(result), expected)

    def test_find_tasks_empty(self):
        """No tasks are found for a given status"""

        dummy_task = DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        dummy_task.status = SchedulerStatus.NEW
        dummy_task.save()

        another_dummy_task = AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        another_dummy_task.status = SchedulerStatus.RUNNING
        another_dummy_task.save()

        result = find_tasks_by_status([SchedulerStatus.FAILED])
        self.assertSetEqual(set(result), set())


class TestFindTask(GrimoireLabTestCase):
    """Unit tests for find_task function"""

    @classmethod
    def setUpClass(cls):
        _, cls.DummyJobClass = register_task_model('dummy_task', DummyTaskDB)
        _, cls.AnotherDummyJobClass = register_task_model('another_dummy_task', AnotherDummyTaskDB)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        GRIMOIRELAB_TASK_MODELS.clear()
        super().tearDownClass()

    def setUp(self):
        """Create the test model"""

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.DummyJobClass)
                schema_editor.delete_model(DummyTaskDB)
                schema_editor.delete_model(self.AnotherDummyJobClass)
                schema_editor.delete_model(AnotherDummyTaskDB)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(DummyTaskDB)
            schema_editor.create_model(self.DummyJobClass)
            schema_editor.create_model(AnotherDummyTaskDB)
            schema_editor.create_model(self.AnotherDummyJobClass)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_find_task(self):
        """Find a task by its uuid"""

        dummy_task = DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        another_dummy_task = AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )

        result = find_task(dummy_task.uuid)
        self.assertEqual(result, dummy_task)

        result = find_task(another_dummy_task.uuid)
        self.assertEqual(result, another_dummy_task)

    def test_find_task_not_found(self):
        """An exception is raised when the job is not found"""

        DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )

        with self.assertRaises(NotFoundError):
            find_task('abcdefgh')


class TestFindJob(GrimoireLabTestCase):
    """Unit tests for find_job function"""

    @classmethod
    def setUpClass(cls):
        _, cls.DummyJobClass = register_task_model('dummy_task', DummyTaskDB)
        _, cls.AnotherDummyJobClass = register_task_model('another_dummy_task', AnotherDummyTaskDB)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        GRIMOIRELAB_TASK_MODELS.clear()
        super().tearDownClass()

    def setUp(self):
        """Create the test model"""

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.DummyJobClass)
                schema_editor.delete_model(DummyTaskDB)
                schema_editor.delete_model(self.AnotherDummyJobClass)
                schema_editor.delete_model(AnotherDummyTaskDB)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(DummyTaskDB)
            schema_editor.create_model(self.DummyJobClass)
            schema_editor.create_model(AnotherDummyTaskDB)
            schema_editor.create_model(self.AnotherDummyJobClass)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_find_job(self):
        """Find a job by its uuid"""

        dummy_task = DummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )

        job_1 = self.DummyJobClass.objects.create(
            uuid='abcdefgh',
            job_num=1,
            task=dummy_task
        )
        job_2 = self.DummyJobClass.objects.create(
            uuid='12345678',
            job_num=2,
            task=dummy_task
        )

        another_dummy_task = AnotherDummyTaskDB.create_task(
            {'arg': 'value'}, 15, 10
        )
        job_a = self.AnotherDummyJobClass.objects.create(
            uuid='jklmnopq',
            job_num=1,
            task=another_dummy_task
        )

        result = find_job('abcdefgh')
        self.assertEqual(result, job_1)

        result = find_job('12345678')
        self.assertEqual(result, job_2)

        result = find_job('jklmnopq')
        self.assertEqual(result, job_a)

    def test_find_job_not_found(self):
        """An exception is raised when the job is not found"""

        with self.assertRaises(NotFoundError):
            find_job('abcdefgh')
