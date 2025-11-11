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
import rq.job

import grimoirelab_toolkit.datetime

from grimoirelab.core.scheduler.db import find_job
from grimoirelab.core.scheduler.errors import NotFoundError
from grimoirelab.core.scheduler.models import (
    Task,
    SchedulerStatus,
    register_task_model,
    GRIMOIRELAB_TASK_MODELS,
)
from grimoirelab.core.scheduler.scheduler import (
    schedule_task,
    cancel_task,
    maintain_tasks,
    reschedule_task,
    _enqueue_task,
    _on_success_callback,
    _on_failure_callback,
)

from ..base import GrimoireLabTestCase


class SchedulerTestTask(Task):
    """Class for testing purposes"""

    TASK_TYPE = "test_task"

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return "testing"

    @staticmethod
    def job_function(*args, **kwargs):
        def add_numbers(a, b):
            return a + b

        return add_numbers(*args, **kwargs)

    @staticmethod
    def on_success_callback(*args, **kwargs):
        def on_success(job, connection, result, *args, **kwargs):
            job_db = find_job(job.id)
            job_db.save_run(SchedulerStatus.COMPLETED, progress=result)

        return on_success(*args, **kwargs)

    @staticmethod
    def on_failure_callback(*args, **kwargs):
        def on_failure(job, connection, t, value, traceback):
            job_db = find_job(job.id)
            job_db.save_run(SchedulerStatus.FAILED, progress=t)

        return on_failure(*args, **kwargs)


class OnSuccessCallbackTestTask(Task):
    """Class for testing on success callback calls"""

    TASK_TYPE = "callback_test_task"

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return "testing"

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


class OnFailureCallbackTestTask(Task):
    """Class for testing on failure callback calls"""

    TASK_TYPE = "failure_test_task"

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return True

    @property
    def default_job_queue(self):
        return "testing"

    @staticmethod
    def job_function(*args, **kwargs):
        raise Exception("Error")

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(job, connection, t, value, traceback, *args, **kwargs):
        job.progress = str(t)
        return _on_failure_callback(job, connection, t, value, traceback, *args, **kwargs)


class TestScheduleTask(GrimoireLabTestCase):
    """Unit tests for scheduling tasks"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        task_class, job_class = register_task_model("test_task", SchedulerTestTask)

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
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
            "a": 1,
            "b": 2,
        }

        # Enqueue the task
        enqueued_at = grimoirelab_toolkit.datetime.datetime_utcnow()
        task = schedule_task("test_task", task_args)

        # Check if a new job is created and the task is enqueued
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertGreaterEqual(task.scheduled_at, enqueued_at)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker("testing")
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
            "a": 1,
            "b": 2,
        }

        task = schedule_task(
            "test_task", task_args, job_interval=360, job_max_retries=10, burst=True
        )

        # Check initial state of the task
        self.assertEqual(task.task_id, f"grimoire:task:{task.uuid}")
        self.assertEqual(task.task_args, task_args)
        self.assertEqual(task.job_interval, 360)
        self.assertEqual(task.job_max_retries, 10)
        self.assertEqual(task.burst, True)

    def test_enqueue_task(self):
        """A task is enqueued and a job is created and executed using _enqueue_task"""

        task_args = {
            "a": 1,
            "b": 2,
        }
        task = SchedulerTestTask.create_task(task_args, 360, 10)

        # Check initial state of the task
        self.assertEqual(task.task_id, f"grimoire:task:{task.uuid}")
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
        self.assertEqual(job.queue, "testing")
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
        self.assertEqual(job.progress, 3)
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)
        self.assertGreater(job.started_at, before_run_call_dt)
        self.assertLess(job.started_at, job.finished_at)

    @unittest.mock.patch("django_rq.get_queue")
    def test_error_enqueuing_task(self, mock_get_queue):
        """An exception is raised when an error occurs enqueuing the task"""

        mock_get_queue.side_effect = Exception("Error getting queue")

        with self.assertRaisesRegex(Exception, "Error getting queue"):
            task_args = {
                "a": 1,
                "b": 2,
            }
            task = SchedulerTestTask.create_task(task_args, 360, 10)
            _enqueue_task(task, scheduled_at=None)


class TestMaintainTasks(GrimoireLabTestCase):
    """Class for testing the maintenance of tasks"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        task_class_sched, job_class_sched = register_task_model("test_task", SchedulerTestTask)
        task_class_callback, job_class_callback = register_task_model(
            "callback_test_task", OnSuccessCallbackTestTask
        )

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(job_class_sched)
                schema_editor.delete_model(task_class_sched)
                schema_editor.delete_model(job_class_callback)
                schema_editor.delete_model(task_class_callback)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(task_class_sched)
            schema_editor.create_model(job_class_sched)
            schema_editor.create_model(task_class_callback)
            schema_editor.create_model(job_class_callback)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_maintain_tasks_reschedule(self):
        """Tasks with inconsistent state are re-scheduled"""

        task_args = {
            "a": 1,
            "b": 2,
        }

        task1 = schedule_task("test_task", task_args)
        task2 = schedule_task("test_task", task_args)

        # Delete one of the jobs manually to create the inconsistent state
        job_db = task2.jobs.first()
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        job_rq.delete()

        # Run the maintenance tasks
        before_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        maintain_tasks()
        after_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        # Check if jobs were re-scheduled

        # Task1 wasn't re-scheduled
        job_db = task1.jobs.first()
        self.assertLessEqual(job_db.last_modified, before_dt)
        self.assertLessEqual(job_db.last_modified, after_dt)

        # Task2 was re-scheduled
        job_db = task2.jobs.first()
        self.assertGreaterEqual(job_db.last_modified, before_dt)
        self.assertLessEqual(job_db.last_modified, after_dt)
        self.assertEqual(job_db.status, SchedulerStatus.CANCELED)

        # Task2 has a new job
        self.assertEqual(task2.jobs.count(), 2)
        job_db = task2.jobs.last()
        self.assertEqual(job_db.status, SchedulerStatus.ENQUEUED)

        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        self.assertEqual(job_rq.id, job_db.uuid)

    def test_maintain_tasks_reschedule_multiple_jobs(self):
        """Tasks with multiple finished jobs are re-scheduled"""

        task_args = {
            "a": 1,
            "b": 2,
        }

        task = schedule_task("callback_test_task", task_args, job_interval=0)
        worker = django_rq.workers.get_worker(task.default_job_queue)
        worker.work(burst=True, with_scheduler=True)
        worker.work(burst=True, with_scheduler=True)
        worker.work(burst=True, with_scheduler=True)

        # Three jobs were processed and one is still pending
        self.assertEqual(task.jobs.count(), 4)

        # Delete the last jobs manually to create the inconsistent state
        job_db = task.jobs.last()
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        job_rq.delete()

        # Run the maintenance tasks
        before_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        maintain_tasks()
        after_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        # Task was re-scheduler
        job_db = task.jobs.last()
        self.assertGreaterEqual(job_db.last_modified, before_dt)
        self.assertLessEqual(job_db.last_modified, after_dt)

        # New job was created
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        self.assertEqual(job_rq.id, job_db.uuid)

        worker.work(burst=True, with_scheduler=True)
        self.assertEqual(task.jobs.count(), 6)

    def test_maintain_tasks_reschedule_expired_scheduled_at(self):
        """Tasks with inconsistent state with expired scheduled time are re-scheduled with current time"""

        task_args = {
            "a": 1,
            "b": 2,
        }

        before_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        task = schedule_task("test_task", task_args)
        before_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        # Delete job manually to create the inconsistent state
        job_db = task.jobs.first()
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        job_rq.delete()

        # Run the maintenance tasks
        before_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        maintain_tasks()
        after_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        # Check if jobs were re-scheduled with a different time
        job_db = task.jobs.last()
        self.assertLessEqual(task.scheduled_at, before_dt)
        self.assertLessEqual(task.scheduled_at, after_dt)

        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        self.assertEqual(job_rq.id, job_db.uuid)

    def test_maintain_tasks_reschedule_non_expired_scheduled_at(self):
        """Tasks with inconsistent state are re-scheduled keeping the same scheduled time"""

        task_args = {
            "a": 1,
            "b": 2,
        }
        schedule_time = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)

        task = SchedulerTestTask.create_task(task_args, 360, 10)
        job_db = _enqueue_task(task, scheduled_at=schedule_time)

        # Delete job manually to create the inconsistent state
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        job_rq.delete()

        # Run the maintenance tasks
        maintain_tasks()

        # Check if jobs were re-scheduled with a different time
        job_db = task.jobs.last()
        self.assertLessEqual(task.scheduled_at, schedule_time)

        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        self.assertEqual(job_rq.id, job_db.uuid)


class TestCancelTask(GrimoireLabTestCase):
    """Unit tests for canceling tasks"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        self.task_class, self.job_class = register_task_model(
            "callback_test_task", OnSuccessCallbackTestTask
        )

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.job_class)
                schema_editor.delete_model(self.task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(self.task_class)
            schema_editor.create_model(self.job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_cancel_task(self):
        """A task is correctly canceled, including jobs"""

        task_args = {
            "a": 1,
            "b": 2,
        }
        task1 = schedule_task("callback_test_task", task_args)
        schedule_task("callback_test_task", task_args)

        # Run the job
        worker = django_rq.workers.get_worker("testing")
        worker.work(burst=True, with_scheduler=True)

        # Check jobs after execution
        self.assertEqual(self.job_class.objects.count(), 4)

        # Two jobs were created for task1:
        # one finished and other is scheduled
        uuids = [job.uuid for job in self.job_class.objects.filter(task=task1).all()]
        self.assertEqual(len(uuids), 2)

        for job_uuid in uuids:
            rq.job.Job.fetch(job_uuid, connection=django_rq.get_connection())

        # Cancel task
        cancel_task(task1.uuid)

        # All the jobs are available
        self.assertEqual(self.job_class.objects.count(), 4)

        # Scheduled job from task2 is now canceled
        jobs_canceled = self.job_class.objects.filter(task=task1, status=SchedulerStatus.CANCELED)
        self.assertEqual(len(jobs_canceled), 1)

        # Jobs are removed from rq
        for job_uuid in uuids:
            with self.assertRaises(rq.exceptions.NoSuchJobError):
                rq.job.Job.fetch(job_uuid, connection=django_rq.get_connection())

        # Task is canceled
        task1.refresh_from_db()
        self.assertEqual(task1.status, SchedulerStatus.CANCELED)

    def test_no_task_found(self):
        """An exception is raised when the task doesn't exist"""

        schedule_task("callback_test_task", {})

        with self.assertRaises(NotFoundError):
            cancel_task("non-existent-task-uuid")


class TestRescheduleTask(GrimoireLabTestCase):
    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        task_class, job_class = register_task_model("test_task", SchedulerTestTask)

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(job_class)
                schema_editor.delete_model(task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(task_class)
            schema_editor.create_model(job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_reschedule_task_completed(self):
        """Test a task is rescheduled correctly"""

        task_args = {
            "a": 1,
            "b": 2,
        }

        # Enqueue the task
        enqueued_at = grimoirelab_toolkit.datetime.datetime_utcnow()
        task = schedule_task("test_task", task_args)

        # Check if a new job is created and the task is enqueued
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertGreaterEqual(task.scheduled_at, enqueued_at)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker("testing")
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

        # Reschedule the completed task
        enqueued_at = grimoirelab_toolkit.datetime.datetime_utcnow()
        reschedule_task(task.uuid)

        # Check if the task is rescheduled
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertGreater(task.scheduled_at, enqueued_at)

        # Run the job
        before_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        worker = django_rq.workers.get_worker("testing")
        processed = worker.work(burst=True, with_scheduler=True)
        after_run_call_dt = grimoirelab_toolkit.datetime.datetime_utcnow()

        self.assertEqual(processed, True)

        # Check task and task state after execution
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.COMPLETED)
        self.assertEqual(task.runs, 2)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, before_run_call_dt)
        self.assertLess(task.last_run, after_run_call_dt)

    def test_reschedule_task_enqueued(self):
        """Test if rescheduling a task enqueued change the scheduled time"""

        # Enqueue the task
        task_args = {
            "a": 1,
            "b": 2,
        }
        first_schedule_time = datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)

        task = SchedulerTestTask.create_task(task_args, 360, 10)
        _enqueue_task(task, scheduled_at=first_schedule_time)

        # Check initial state of the task
        self.assertEqual(task.task_id, f"grimoire:task:{task.uuid}")
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(task.scheduled_at, first_schedule_time)

        # Reschedule the task
        reschedule_task(task.uuid)
        second_schedule_time = grimoirelab_toolkit.datetime.datetime_utcnow()

        # Check if the task is rescheduled
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertLess(task.scheduled_at, second_schedule_time)

    def test_reschedule_inconsistent_task(self):
        """Test if reschedules a task with an inconsistent state"""

        # Enqueue the task
        task_args = {
            "a": 1,
            "b": 2,
        }

        task = SchedulerTestTask.create_task(task_args, 360, 10)
        job_db = _enqueue_task(task)

        # Check initial state of the task
        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)

        # Delete job manually to create the inconsistent state
        job_rq = rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())
        job_rq.delete()

        # Make sure the job was deleted
        with self.assertRaises(rq.exceptions.NoSuchJobError):
            rq.job.Job.fetch(job_db.uuid, connection=django_rq.get_connection())

        # Reschedule the task
        scheduled_date = grimoirelab_toolkit.datetime.datetime_utcnow()
        reschedule_task(task.uuid)

        # Check if the task is rescheduled
        task.refresh_from_db()
        job_db = task.jobs.order_by("-scheduled_at").first()

        self.assertEqual(task.status, SchedulerStatus.ENQUEUED)
        self.assertEqual(job_db.status, SchedulerStatus.ENQUEUED)
        self.assertGreater(task.scheduled_at, scheduled_date)

        # Run the job
        worker = django_rq.workers.get_worker("testing")
        processed = worker.work(burst=True, with_scheduler=True)

        self.assertEqual(processed, True)

        # Check task and task state after execution
        task.refresh_from_db()
        self.assertEqual(task.status, SchedulerStatus.COMPLETED)
        self.assertEqual(task.runs, 1)
        self.assertEqual(task.failures, 0)
        self.assertGreater(task.last_run, scheduled_date)


class TestOnSuccessCallback(GrimoireLabTestCase):
    """Unit tests for the default on_success_callback function"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        self.task_class, self.job_class = register_task_model(
            "callback_test_task", OnSuccessCallbackTestTask
        )

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
            with django.db.connection.schema_editor() as schema_editor:
                schema_editor.delete_model(self.job_class)
                schema_editor.delete_model(self.task_class)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(self.task_class)
            schema_editor.create_model(self.job_class)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_on_success_callback(self):
        """The success callback re-schedules the task"""

        task_args = {
            "a": 1,
            "b": 2,
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
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)
        self.assertGreater(job.started_at, before_run_call_dt)
        self.assertLess(job.started_at, job.finished_at)

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
            "a": 1,
            "b": 2,
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

    @unittest.mock.patch("grimoirelab.core.scheduler.scheduler.datetime_utcnow")
    def test_interval_between_jobs(self, mock_utcnow):
        """Task is re-scheduled to run after the given interval"""

        dt = grimoirelab_toolkit.datetime.datetime_utcnow()
        mock_utcnow.return_value = dt

        task_args = {
            "a": 1,
            "b": 2,
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


class OnFailureNoRetryTestTask(Task):
    """Class for testing on failure callback calls with no retry"""

    TASK_TYPE = "no_retry_test_task"

    def prepare_job_parameters(self):
        return self.task_args

    def can_be_retried(self):
        return False

    @property
    def default_job_queue(self):
        return "testing"

    @staticmethod
    def job_function(*args, **kwargs):
        raise Exception("Error")

    @staticmethod
    def on_success_callback(*args, **kwargs):
        return _on_success_callback(*args, **kwargs)

    @staticmethod
    def on_failure_callback(job, connection, t, value, traceback, *args, **kwargs):
        job.progress = str(t)
        return _on_failure_callback(job, connection, t, value, traceback, *args, **kwargs)


class TestOnFailureCallback(GrimoireLabTestCase):
    """Unit tests for the default on_failure_callback function"""

    def setUp(self):
        GRIMOIRELAB_TASK_MODELS.clear()
        self.task_class, self.job_class = register_task_model(
            "failure_test_task", OnFailureCallbackTestTask
        )

        def cleanup_test_model():
            GRIMOIRELAB_TASK_MODELS.clear()
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
            "a": 1,
            "b": 2,
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
        self.assertEqual(job.progress, "<class 'Exception'>")
        self.assertGreater(job.finished_at, before_run_call_dt)
        self.assertLess(job.finished_at, after_run_call_dt)
        self.assertGreater(job.started_at, before_run_call_dt)
        self.assertLess(job.started_at, job.finished_at)

        # A new job was created
        self.assertEqual(self.job_class.objects.count(), 2)

    def test_maximum_tries(self):
        """The task is not re-scheduled after a number of tries"""

        task_args = {
            "a": 1,
            "b": 2,
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
        task_class, job_class = register_task_model("no_retry_test_task", OnFailureNoRetryTestTask)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.create_model(task_class)
            schema_editor.create_model(job_class)

        # Schedule the task
        task_args = {
            "a": 1,
            "b": 2,
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
        self.assertEqual(job.progress, "<class 'Exception'>")

        # Only one job was created
        self.assertEqual(job_class.objects.count(), 1)

        with django.db.connection.schema_editor() as schema_editor:
            schema_editor.delete_model(job_class)
            schema_editor.delete_model(task_class)
