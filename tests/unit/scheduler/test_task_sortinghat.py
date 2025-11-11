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

import datetime
import time

from unittest.mock import patch

from django.test import override_settings
from django.contrib.auth import get_user_model
from django_rq import get_worker
from rq.scheduler import RQScheduler
from sortinghat.core.models import AffiliationRecommendation, MergeRecommendation
from sortinghat.core.context import SortingHatContext
from sortinghat.core import api as sh_api

from grimoirelab.core.scheduler.models import (
    SchedulerStatus,
    get_registered_task_model,
    register_task_model,
)
from grimoirelab.core.scheduler.scheduler import schedule_task
from grimoirelab.core.scheduler.tasks.models import SortingHatTask

from ..base import GrimoireLabTestCase


class TestSortingHatTask(GrimoireLabTestCase):
    """Unit tests for SortingHat task functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS is empty from other tests
        # so we need to ensure SortingHatTask is registered
        try:
            register_task_model(SortingHatTask.TASK_TYPE, SortingHatTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        super().setUp()
        self.system_user = get_user_model().objects.create_user(
            username="grimoire-bot",
            email="grimoirelab@example.com",
            password=None,
        )

    def test_create_task(self):
        """Test creating a SortingHat task"""

        task_args = {"tenant": "test_tenant"}
        job_interval = 3600
        job_max_retries = 3
        job_type = "unify"

        task = SortingHatTask.create_task(
            task_args=task_args,
            job_interval=job_interval,
            job_max_retries=job_max_retries,
            job_type=job_type,
        )

        self.assertEqual(task.task_args, task_args)
        self.assertEqual(task.job_interval, job_interval)
        self.assertEqual(task.job_max_retries, job_max_retries)
        self.assertEqual(task.job_type, SortingHatTask.JobType.UNIFY.value)
        self.assertEqual(task.TASK_TYPE, "sortinghat")
        self.assertFalse(task.burst)
        self.assertTrue(SortingHatTask.objects.filter(uuid=task.uuid).exists())

    def test_create_task_invalid_job_type(self):
        """Test creating a SortingHat task with invalid job type"""

        with self.assertRaises(ValueError) as context:
            SortingHatTask.create_task(
                task_args={},
                job_interval=3600,
                job_max_retries=3,
                job_type="invalid_job",
            )

        self.assertIn("'invalid_job' is not a valid SortingHatTask.JobType", str(context.exception))

    def test_create_task_missing_job_type(self):
        """Test creating a SortingHat task without job type"""

        with self.assertRaises(ValueError):
            SortingHatTask.create_task(
                task_args={},
                job_interval=3600,
                job_max_retries=3,
            )

    def test_prepare_job_parameters(self):
        """Test prepare_job_parameters method"""

        task_args = {"param1": "value1"}
        task = SortingHatTask.create_task(
            task_args=task_args,
            job_interval=3600,
            job_max_retries=3,
            job_type="unify",
        )

        job_params = task.prepare_job_parameters()

        self.assertIn("ctx", job_params)
        self.assertIsInstance(job_params["ctx"], SortingHatContext)
        self.assertEqual(job_params["ctx"].user, self.system_user)
        self.assertEqual(job_params["param1"], "value1")
        self.assertEqual(job_params["job_type"], "unify")

    @patch("grimoirelab.core.scheduler.tasks.models.find_import_identities_backends")
    def test_prepare_job_parameters_import_identities_with_from_date(self, mock_backends):
        """Test prepare_job_parameters for import_identities with from_date support"""

        # Mock the import backend to support from_date
        mock_backends.return_value = {
            "test_backend": {
                "class": "TestBackend",
                "args": ["url", "from_date"],
            }
        }

        # Create a task with previous completed job
        task = SortingHatTask.create_task(
            task_args={"backend_name": "test_backend"},
            job_interval=3600,
            job_max_retries=3,
            job_type=SortingHatTask.JobType.IMPORT_IDENTITIES,
        )
        SortingHatJob = get_registered_task_model(SortingHatTask.TASK_TYPE)[1]
        completed_job = SortingHatJob.objects.create(
            task=task,
            job_num=1,
            status=SchedulerStatus.COMPLETED,
            started_at=datetime.datetime(2023, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc),
        )

        job_params = task.prepare_job_parameters()

        # Check that from_date is added
        self.assertIn("from_date", job_params)
        self.assertEqual(job_params["from_date"], completed_job.started_at.isoformat())

    @patch("grimoirelab.core.scheduler.tasks.models.find_import_identities_backends")
    def test_prepare_job_parameters_import_identities_without_from_date(self, mock_backends):
        """Test prepare_job_parameters for import_identities without from_date support"""

        # Mock the import backend without from_date support
        mock_backends.return_value = {"test_backend": {"class": "TestBackend", "args": ["url"]}}

        task = SortingHatTask.create_task(
            task_args={"backend_name": "test_backend"},
            job_interval=3600,
            job_max_retries=3,
            job_type="import_identities",
        )

        job_params = task.prepare_job_parameters()

        # Check that from_date is not added
        self.assertNotIn("from_date", job_params)

    @override_settings(GRIMOIRELAB_Q_SORTINGHAT_JOBS="test-sortinghat-queue")
    def test_default_job_queue(self):
        """Test that the default job queue is set correctly"""

        task = SortingHatTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            job_type="unify",
        )
        self.assertEqual(task.default_job_queue, "test-sortinghat-queue")


def wait_for_job_completion(job, timeout=5):
    """Utility function to wait for a job to complete"""

    start_time = time.time()
    while job.status not in [SchedulerStatus.COMPLETED, SchedulerStatus.FAILED]:
        if time.time() - start_time > timeout:
            raise TimeoutError("Job did not complete within the specified timeout")
        time.sleep(0.2)
        job.refresh_from_db()


class TestSortingHatJobs(GrimoireLabTestCase):
    """Integration tests for SortingHat tasks"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # GRIMOIRELAB_TASK_MODELS is empty from other tests
        # so we need to ensure SortingHatTask is registered
        try:
            register_task_model(SortingHatTask.TASK_TYPE, SortingHatTask)
        except ValueError:
            # Already registered
            pass

    def setUp(self):
        super().setUp()
        self.worker = get_worker("sortinghat_jobs")
        self.scheduler = RQScheduler(["sortinghat_jobs"], connection=self.worker.connection)
        self.scheduler.acquire_locks()
        self.system_user = get_user_model().objects.create_user(
            username="grimoire-bot",
            email="grimoirelab@example.com",
            password=None,
        )
        self.ctx = SortingHatContext(self.system_user, None, "default")

        # Test data from https://github.com/chaoss/grimoirelab-sortinghat

        # Organizations and domains
        sh_api.add_organization(self.ctx, "Example")
        sh_api.add_domain(self.ctx, "Example", "example.com", is_top_domain=True)

        sh_api.add_organization(self.ctx, "Example Int.")
        sh_api.add_domain(self.ctx, "Example Int.", "u.example.com", is_top_domain=True)
        sh_api.add_domain(self.ctx, "Example Int.", "es.u.example.com")
        sh_api.add_domain(self.ctx, "Example Int.", "en.u.example.com")

        sh_api.add_organization(self.ctx, "Bitergia")
        sh_api.add_domain(self.ctx, "Bitergia", "bitergia.com")
        sh_api.add_domain(self.ctx, "Bitergia", "bitergia.org")

        sh_api.add_organization(self.ctx, "LibreSoft")

        # Individual 1
        self.john_smith = sh_api.add_identity(
            self.ctx, email="jsmith@example.com", name="John Smith", source="scm"
        )
        self.js2 = sh_api.add_identity(
            self.ctx, name="John Smith", source="scm", uuid=self.john_smith.uuid
        )
        self.js3 = sh_api.add_identity(
            self.ctx, username="jsmith", source="scm", uuid=self.john_smith.uuid
        )

        # Individual 2
        self.jsmith = sh_api.add_identity(
            self.ctx, name="J. Smith", username="john_smith", source="alt"
        )
        self.jsm2 = sh_api.add_identity(
            self.ctx, name="John Smith", username="jsmith", source="alt", uuid=self.jsmith.uuid
        )
        self.jsm3 = sh_api.add_identity(
            self.ctx, email="jsmith@example.com", source="alt", uuid=self.jsmith.uuid
        )

        # Individual 3
        self.jane_rae = sh_api.add_identity(self.ctx, name="Janer Rae", source="mls")
        self.jr2 = sh_api.add_identity(
            self.ctx,
            email="jane.rae@example.net",
            name="Jane Rae Doe",
            source="mls",
            uuid=self.jane_rae.uuid,
        )

        # Individual 4
        self.js_alt = sh_api.add_identity(
            self.ctx, name="J. Smith", username="john_smith", source="scm"
        )
        self.js_alt2 = sh_api.add_identity(
            self.ctx,
            email="J_Smith@example.com",
            username="john_smith",
            source="mls",
            uuid=self.js_alt.uuid,
        )

    def tearDown(self):
        self.scheduler.release_locks()

    def test_affiliate_job(self):
        """Test the execution of an affiliate job"""

        task_args = {}
        task = schedule_task(
            SortingHatTask.TASK_TYPE,
            task_args,
            burst=True,
            job_type=SortingHatTask.JobType.AFFILIATE,
        )

        self.scheduler.enqueue_scheduled_jobs()
        self.worker.work(burst=True)

        job = task.jobs.first()
        if not job:
            self.fail("No job created for the task")
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)

        self.john_smith.refresh_from_db()
        self.jsmith.refresh_from_db()
        self.jane_rae.refresh_from_db()
        self.js_alt.refresh_from_db()

        # Check that identities have been affiliated correctly
        enrollments_db = self.john_smith.individual.enrollments.all()
        self.assertEqual(len(enrollments_db), 1)
        enrollment_db = enrollments_db[0]
        self.assertEqual(enrollment_db.group.name, "Example")
        self.assertEqual(
            enrollment_db.start, datetime.datetime(1900, 1, 1, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            enrollment_db.end, datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
        )

        enrollments_db = self.jsmith.individual.enrollments.all()
        self.assertEqual(len(enrollments_db), 1)
        enrollment_db = enrollments_db[0]
        self.assertEqual(enrollment_db.group.name, "Example")
        self.assertEqual(
            enrollment_db.start, datetime.datetime(1900, 1, 1, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            enrollment_db.end, datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
        )

        enrollments_db = self.jane_rae.individual.enrollments.all()
        self.assertEqual(len(enrollments_db), 0)

        enrollments_db = self.js_alt.individual.enrollments.all()
        self.assertEqual(len(enrollments_db), 1)
        enrollment_db = enrollments_db[0]
        self.assertEqual(enrollment_db.group.name, "Example")
        self.assertEqual(
            enrollment_db.start, datetime.datetime(1900, 1, 1, tzinfo=datetime.timezone.utc)
        )
        self.assertEqual(
            enrollment_db.end, datetime.datetime(2100, 1, 1, tzinfo=datetime.timezone.utc)
        )

    def test_unify_job(self):
        """Test the execution of a unify job"""

        task_args = {"criteria": ["email", "name", "username"]}
        task = schedule_task(
            SortingHatTask.TASK_TYPE, task_args, burst=True, job_type=SortingHatTask.JobType.UNIFY
        )

        self.scheduler.enqueue_scheduled_jobs()
        self.worker.work(burst=True)

        job = task.jobs.first()
        if not job:
            self.fail("No job created for the task")
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)

        self.john_smith.refresh_from_db()
        self.jsmith.refresh_from_db()
        self.jane_rae.refresh_from_db()
        self.js_alt.refresh_from_db()

        # Check that identities have been unified correctly
        self.assertEqual(self.john_smith.individual, self.jsmith.individual)
        self.assertEqual(self.john_smith.individual, self.js_alt.individual)
        self.assertNotEqual(self.john_smith.individual, self.jane_rae.individual)

    def test_recommend_affiliations(self):
        """Test the execution of a recommend_affiliations job"""

        task_args = {}
        task = schedule_task(
            SortingHatTask.TASK_TYPE,
            task_args,
            burst=True,
            job_type=SortingHatTask.JobType.RECOMMEND_AFFILIATIONS,
        )

        self.scheduler.enqueue_scheduled_jobs()
        self.worker.work(burst=True)

        job = task.jobs.first()
        if not job:
            self.fail("No job created for the task")
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)

        # Check that recommended affiliations have been created
        self.assertEqual(AffiliationRecommendation.objects.count(), 3)

        recommendation = AffiliationRecommendation.objects.get(
            individual__mk=self.john_smith.individual.mk
        )
        self.assertEqual(recommendation.organization.name, "Example")
        self.assertEqual(recommendation.applied, None)

        recommendation = AffiliationRecommendation.objects.get(
            individual__mk=self.jsmith.individual.mk
        )
        self.assertEqual(recommendation.organization.name, "Example")
        self.assertEqual(recommendation.applied, None)

        recommendation = AffiliationRecommendation.objects.get(
            individual__mk=self.js_alt.individual.mk
        )
        self.assertEqual(recommendation.organization.name, "Example")
        self.assertEqual(recommendation.applied, None)

    def test_recommend_matches(self):
        """Test the execution of a recommend_matches job"""

        task_args = {
            "source_uuids": None,
            "target_uuids": None,
            "criteria": ["email", "name", "username"],
        }
        task = schedule_task(
            SortingHatTask.TASK_TYPE,
            task_args,
            burst=True,
            job_type=SortingHatTask.JobType.RECOMMEND_MATCHES,
        )

        self.scheduler.enqueue_scheduled_jobs()
        self.worker.work(burst=True)

        job = task.jobs.first()
        if not job:
            self.fail("No job created for the task")
        self.assertEqual(job.status, SchedulerStatus.COMPLETED)

        # Check that recommended matches have been created
        self.assertEqual(MergeRecommendation.objects.count(), 2)

        self.assertTrue(
            MergeRecommendation.objects.filter(
                individual1__mk=self.jsmith.individual.mk,
                individual2__mk=self.john_smith.individual.mk,
            ).exists()
        )
        self.assertTrue(
            MergeRecommendation.objects.filter(
                individual1__mk=self.js_alt.individual.mk, individual2__mk=self.jsmith.individual.mk
            ).exists()
        )
