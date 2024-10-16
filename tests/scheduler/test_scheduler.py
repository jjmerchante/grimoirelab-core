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

import datetime
import django.db
import django_rq.workers

import grimoirelab_toolkit.datetime

from grimoirelab.core.scheduler.db import find_job
from grimoirelab.core.scheduler.models import (
    Task,
    SchedulerStatus,
    register_task_model,
    GRIMOIRELAB_TASK_MODELS)
from grimoirelab.core.scheduler.scheduler import (
    schedule_task,
    _enqueue_task,
    _on_success_callback,
    _on_failure_callback
)

from ..base import GrimoireLabTestCase


class SchedulerTestTask(Task):
    """Class for testing purposes"""

    TASK_TYPE = 'test_task'

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return 'testing'

    @staticmethod
    def job_function(*args, **kwargs):
        def add_numbers(a, b):
            return a + b
        return add_numbers(*args, **kwargs)

    @staticmethod
    def on_success_callback(*args, **kwargs):
        def on_success(job, connection, result, *args, **kwargs):
            job_db = find_job(job.id)
            job_db.save_run(SchedulerStatus.COMPLETED, result=result)
            print(f"Task completed successfully with result: {result}")
        return on_success(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        def on_failure(job, connection, result, *args, **kwargs):
            job_db = find_job(job.id)
            job_db.save_run(SchedulerStatus.FAILED, result=result)
            print(f"Task failed with error: {result}")
        return on_failure(*args, **kwargs)


class TestScheduleTask(GrimoireLabTestCase):
    """Unit tests for scheduling tasks"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        task_class, job_class = register_task_model('test_task', SchedulerTestTask)

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(job_class)
                schema_editor.delete_model(task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(task_class)
            schema_editor.create_model(job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_schedule_task(self):
        """A task is enqueued and a job is created and executed"""

        task_args = {
            'a': 1,
            'b': 2,
        }

        # Enqueue the task
        enqueued_at = grimoirelab_toolkit.datetime.datetime_utcnow()
        task = schedule_task('test_task', task_args)

        # Check if a new job is created and the task is enqueued
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertGreaterEqual(task.scheduled_at, enqueued_at)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker('testing')
        processed = worker.work(burst=True, with_scheduler=True)
        after_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(processed, True)

        # Check task and task state after execution
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.COMPLETED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, before_run_call_dt)
        self.assertLess(task.last_run, after_run_call_dt)

    def test_schedule_task_parameters(self):
        """Task parameters are correctly set"""

        task_args = {
            'a': 1,
            'b': 2,
        }

        task = schedule_task(
            'test_task', task_args,
            job_interval=360, job_max_retries=10, burst=True
        )

        # Check initial state of the task
        self.assertEqual(task.task_id, f'grimoire:task:{task.uuid}')
        self.assertEqual(task.task_args, task_args)
        self.assertEqual(task.job_interval, 360)
        self.assertEqual(task.job_max_retries, 10)
        self.assertEqual(task.burst, True)

    def test_enqueue_task(self):
        """A task is enqueued and a job is created and executed using _enqueue_task"""

        task_args = {
            'a': 1,
            'b': 2,
        }
        task = SchedulerTestTask.create_task(task_args, 360, 10)

        # Check initial state of the task
        self.assertEqual(task.task_id, f'grimoire:task:{task.uuid}')
        self.assertEqual(task.status, SchedulerStatus.NEW)
        self.assertEqual(task.task_args, task_args)
        self.assertEqual(task.job_interval, 360)
        self.assertEqual(task.job_max_retries, 10)
        self.assertEqual(task.burst, False)

        # Enqueue the task
        enqueued_at = grimoirelab_toolkit.datetime.datetime_utcnow()
        job = _enqueue_task(task, scheduled_at=None)

        # Check if a new job is created and the task is enqueued
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(job.job_num, 1)
        self.assertEqual(job.queue, 'testing')
        self.assertEqual(job.task, task)
        self.assertGreaterEqual(job.scheduled_at, enqueued_at)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker(job.queue)
        processed = worker.work(burst=True, with_scheduler=True)
        after_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(processed, True)

        # Check task and task state after execution
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.COMPLETED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, before_run_call_dt)
        self.assertLess(task.last_run, after_run_call_dt)

        # Check job state after execution
        job.refresh_from_db()
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)
        self.assertEqual(job.result, 3)
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)

    @unittest.mock.patch('django_rq.get_queue')
    def test_error_enqueuing_task(self, mock_get_queue):
        """An exception is raised when an error occurs enqueuing the task"""

        mock_get_queue.side_effect = Exception("Error getting queue")

        with self.assertRaisesRegex(Exception, "Error getting queue"):
            task_args = {
                'a': 1,
                'b': 2,
            }
            task = SchedulerTestTask.create_task(task_args, 360, 10)
            _enqueue_task(task, scheduled_at=None)


class OnSuccessCallbackTestTask(Task):
    """Class for testing on success callback calls"""

    TASK_TYPE = 'callback_test_task'

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return 'testing'

    @staticmethod
    def job_function(*args, **kwargs):
        def add_numbers(a, b):
            return a + b
        return add_numbers(*args, **kwargs)

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)


class TestOnSuccessCallback(GrimoireLabTestCase):
    """Unit tests for the default on_success_callback function"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        self.task_class, self.job_class = register_task_model(
            'callback_test_task', OnSuccessCallbackTestTask
        )

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.job_class)
                schema_editor.delete_model(self.task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(self.task_class)
            schema_editor.create_model(self.job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_on_failure_callback(self):
        """The failure callback re-schedules the task"""

        task_args = {
            'a': 1,
            'b': 2,
        }
        task = OnSuccessCallbackTestTask.create_task(task_args, 360, 10)
        job = _enqueue_task(task, scheduled_at=None)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker(job.queue)
        processed = worker.work(burst=True, with_scheduler=True)
        after_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(processed, True)

        # Check job state after execution
        job.refresh_from_db()
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)
        self.assertEqual(job.result, 3)
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)

        # The callback was called and the task was scheduled again
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, before_run_call_dt)
        self.assertLess(task.last_run, after_run_call_dt)

        # A new job was created
        self.assertEqual(self.job_class.objects.count(), 2)

    def test_burst_mode(self):
        """Task is not re-scheduled when burst mode is on"""

        task_args = {
            'a': 1,
            'b': 2,
        }
        task = OnSuccessCallbackTestTask.create_task(task_args, 360, 10, burst=True)
        job = _enqueue_task(task, scheduled_at=None)

        # Run the job
        worker = django_rq.workers.get_worker(job.queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, True)

        # The callback was called and the task was scheduled again
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.COMPLETED)

        # No new job was created
        self.assertEqual(self.job_class.objects.count(), 1)

    @unittest.mock.patch('grimoirelab.core.scheduler.scheduler.datetime_utcnow')
    def test_interval_between_jobs(self, mock_utcnow):
        """Task is re-scheduled to run after the given interval"""

        dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        mock_utcnow.return_value = dt

        task_args = {
            'a': 1,
            'b': 2,
        }
        job_interval = 3600

        task = OnSuccessCallbackTestTask.create_task(task_args, job_interval, 10)
        job = _enqueue_task(task, scheduled_at=None)

        # Run the job
        worker = django_rq.workers.get_worker(job.queue)
        processed = worker.work(burst=True, with_scheduler=True)
        self.assertEqual(processed, True)

        # The callback was called and the task was scheduled again
        # with a new time
        expected = dt + datetime.timedelta(seconds=job_interval)

        task.refresh_from_db()
        self.assertEqual(task.scheduled_at, expected)
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(task.failures, 0)

        # New job was created
        self.assertEqual(self.job_class.objects.count(), 2)


class OnFailureCallbackTestTask(Task):
    """Class for testing on failure callback calls"""

    TASK_TYPE = 'failure_test_task'

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return 'testing'

    @staticmethod
    def job_function(*args, **kwargs):
        raise Exception("Error")

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)


class OnFailureNoRetryTestTask(Task):
    """Class for testing on failure callback calls with no retry"""

    TASK_TYPE = 'no_retry_test_task'

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return False

    @property
    def default_job_queue(self):
        return 'testing'

    @staticmethod
    def job_function(*args, **kwargs):
        raise Exception("Error")

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        return _on_failure_callback(*args, **kwargs)


class TestOnFailureCallback(GrimoireLabTestCase):
    """Unit tests for the default on_failure_callback function"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        self.task_class, self.job_class = register_task_model(
            'failure_test_task', OnFailureCallbackTestTask
        )

        def cleanup_test_model():
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.job_class)
                schema_editor.delete_model(self.task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(self.task_class)
            schema_editor.create_model(self.job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_on_failure_callback(self):
        """The failure callback re-schedules the task"""

        task_args = {
            'a': 1,
            'b': 2,
        }
        task = OnFailureCallbackTestTask.create_task(task_args, 360, 10)
        job = _enqueue_task(task, scheduled_at=None)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker(job.queue)
        processed = worker.work(burst=True, with_scheduler=True)
        after_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(processed, True)

        # The callback was called and the task was scheduled again
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 1)
        self.assertGreater(task.last_run, before_run_call_dt)
        self.assertLess(task.last_run, after_run_call_dt)

        # Check job state after execution
        job.refresh_from_db()
        self.assertEqual(job.status, SchedulerStatus.FAILED)
        self.assertEqual(job.result, None)
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)

        # A new job was created
        self.assertEqual(self.job_class.objects.count(), 2)

    def test_maximum_tries(self):
        """The task is not re-scheduled after a number of tries"""

        task_args = {
            'a': 1,
            'b': 2,
        }
        max_tries = 3
        task = OnFailureCallbackTestTask.create_task(task_args, 0, max_tries)
        job = _enqueue_task(task, scheduled_at=None)

        # Update failures data to make it stop
        task.failures = 2
        task.runs = 2
        task.save()

        worker = django_rq.workers.get_worker(job.queue)
        worker.work(burst=True, with_scheduler=True)

        # The callback was called and the task was scheduled again
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.FAILED)
        self.assertEqual(task.runs, 3)
        self.assertEqual(task.failures, 3)

    def test_no_retry(self):
        """The task can't be retried"""

        # Register the class to test retrying
        task_class, job_class = register_task_model(
            'no_retry_test_task', OnFailureNoRetryTestTask
        )

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(task_class)
            schema_editor.create_model(job_class)

        # Schedule the task
        task_args = {
            'a': 1,
            'b': 2,
        }
        max_tries = 3
        task = OnFailureNoRetryTestTask.create_task(task_args, 0, max_tries)
        job = _enqueue_task(task, scheduled_at=None)

        worker = django_rq.workers.get_worker(job.queue)
        worker.work(burst=True, with_scheduler=True)

        # The callback was called and the task was scheduled again
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.FAILED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 1)

        # Check job state after execution
        job.refresh_from_db()
        self.assertEqual(job.status, SchedulerStatus.FAILED)
        self.assertEqual(job.result, None)

        # Only one job was created
        self.assertEqual(job_class.objects.count(), 1)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.delete_model(job_class)
            schema_editor.delete_model(task_class)
