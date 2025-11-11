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

import unittest.mock

import django.db

import grimoirelab_toolkit.datetime

from grimoirelab.core.scheduler.models import (
    Job,
    SchedulerStatus,
    Task,
    register_task_model,
    get_registered_task_model,
    get_all_registered_task_models,
    GRIMOIRELAB_TASK_MODELS,
)

from ..base import GrimoireLabTestCase


class DummyTask(Task):
    """Class for testing the task register"""

    TASK_TYPE = "dummy_task"


class AnotherDummyTask(Task):
    """Class for testing the task register"""

    TASK_TYPE = "another_dummy_task"


@unittest.mock.patch("uuid.uuid4", return_value="abcdefg")
class TestTaskModel(GrimoireLabTestCase):
    """Unit tests for task model"""

    def setUp(self):
        """Create the test model"""

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(DummyTask)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(DummyTask)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_create_task(self, mock_uuid):
        """Task is correctly created"""

        task = DummyTask.create_task({"arg": "value"}, 15, 10, burst=True)
        self.assertEqual(task.id, 1)
        self.assertEqual(task.uuid, "abcdefg")
        self.assertEqual(task.task_type, "dummy_task")
        self.assertEqual(task.task_args, {"arg": "value"})
        self.assertEqual(task.job_interval, 15)
        self.assertEqual(task.job_max_retries, 10)
        self.assertEqual(task.burst, True)
        self.assertEqual(task.status, SchedulerStatus.NEW)
        self.assertEqual(task.runs, 0)
        self.assertEqual(task.failures, 0)
        self.assertEqual(task.last_run, None)
        self.assertEqual(task.scheduled_at, None)

    def test_task_id(self, mock_uuid):
        """Task id property is correctly generated"""

        task = DummyTask.create_task({}, 0, 0, burst=False)

        self.assertEqual(task.task_id, "grimoire:task:abcdefg")

    def test_save_run(self, mock_uuid):
        """Task status is correctly updated when save_run is called"""

        task = DummyTask.create_task({}, 0, 0, burst=False)

        before_save_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        task.save_run(SchedulerStatus.COMPLETED)
        after_save_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(task.status, SchedulerStatus.COMPLETED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, before_save_call_dt)
        self.assertLess(task.last_run, after_save_call_dt)

        before_save_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        task.save_run(SchedulerStatus.FAILED)
        after_save_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(task.status, SchedulerStatus.FAILED)
        self.assertEqual(task.runs, 2)
        self.assertEqual(task.failures, 1)
        self.assertGreater(task.last_run, before_save_call_dt)
        self.assertLess(task.last_run, after_save_call_dt)


class TestTaskRegistration(GrimoireLabTestCase):
    """Unit tests for task registration functions"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()

    def tearDown(self):
        GRIMOIRELAB_TASK_MODELS.clear()

    def test_register_task(self):
        """Task is correctly registered and job class is created"""

        task_class, job_class = register_task_model("dummy_task", DummyTask)

        self.assertEqual(task_class, DummyTask)
        self.assertEqual(job_class.__name__, "DummyJob")

        registered_task = GRIMOIRELAB_TASK_MODELS["dummy_task"]
        self.assertEqual(registered_task[0], task_class)
        self.assertEqual(registered_task[1], job_class)

    def test_get_registered_task(self):
        """Task type is correctly retrieved from the registry"""

        t = DummyTask, type("DummyJob", (Job,), {"__module__": __name__})
        GRIMOIRELAB_TASK_MODELS["dummy_task"] = t

        task_class, job_class = get_registered_task_model("dummy_task")

        self.assertEqual(task_class, DummyTask)
        self.assertEqual(job_class.__name__, "DummyJob")

    def test_job_class_type(self):
        """The job created when registering a task is a subclass of Job"""

        task_class, job_class = register_task_model("dummy_task", DummyTask)

        self.assertEqual(task_class, DummyTask)
        self.assertEqual(job_class.__name__, "DummyJob")
        self.assertEqual(issubclass(job_class, Job), True)

    def test_register_task_already_registered(self):
        """A ValueError exception is raised if the given task already exists"""

        register_task_model("dummy_task", DummyTask)

        with self.assertRaises(ValueError):
            register_task_model("dummy_task", DummyTask)

    def test_get_registered_task_not_found(self):
        """A KeyError exception is raised if the given task is not found"""

        with self.assertRaises(KeyError):
            get_registered_task_model("non_existent_task")

    def test_get_all_registered_task_models_empty(self):
        """An empty list is returned when the registry is empty"""

        models = list(get_all_registered_task_models())
        self.assertEqual(models, [])

    def test_get_all_registered_task_models(self):
        """A list with all the registered task is returned"""

        register_task_model("dummy_task", DummyTask)
        register_task_model("another_dummy_task", AnotherDummyTask)

        models = list(get_all_registered_task_models())

        self.assertEqual(len(models), 2)
        self.assertEqual(models[0][0], DummyTask)
        self.assertEqual(models[0][1].__name__, "DummyJob")
        self.assertEqual(models[1][0], AnotherDummyTask)
        self.assertEqual(models[1][1].__name__, "AnotherDummyJob")
