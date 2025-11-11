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

from unittest.mock import patch, MagicMock

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grimoirelab.core.scheduler.models import (
    SchedulerStatus,
    get_all_registered_task_names,
)
from grimoirelab.core.scheduler.tasks.models import EventizerTask, SortingHatTask


class ListTaskTypesApiTest(APITestCase):
    """Unit tests for the List Task Types API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_list_task_types(self):
        """Test that it returns a list of available task types"""

        url = reverse("task-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        names = get_all_registered_task_names()
        for name in names:
            self.assertIn(name, response.data)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse("task-types")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data["detail"], "Authentication credentials were not provided.")


class ListCreateTasksApiTest(APITestCase):
    """Unit tests for the List Create Tasks API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    @patch("grimoirelab.core.scheduler.api.schedule_task")
    def test_create_eventizer_task(self, mock_schedule_task):
        """Test creating an eventizer task"""

        mock_task = MagicMock()
        mock_task.uuid = "test_task_uuid"
        mock_schedule_task.return_value = mock_task

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        data = {
            "datasource_type": "git",
            "datasource_category": "commit",
            "task_args": {"uri": "https://github.com/example/repo.git"},
            "job_interval": 3600,
            "job_max_retries": 3,
            "burst": False,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("created", response.data[0])
        mock_schedule_task.assert_called_once()

    @patch("grimoirelab.core.scheduler.api.schedule_task")
    def test_create_sortinghat_task(self, mock_schedule_task):
        """Test creating a sortinghat task"""

        mock_task = MagicMock()
        mock_task.uuid = "test_task_uuid"
        mock_schedule_task.return_value = mock_task

        url = reverse("tasks", kwargs={"task_type": "sortinghat"})
        data = {
            "job_type": "unify",
            "task_args": {},
            "job_interval": 7200,
            "job_max_retries": 2,
            "burst": True,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("created", response.data[0])
        mock_schedule_task.assert_called_once()

    def test_create_task_invalid_type(self):
        """Test creating a task with an invalid task type"""

        url = reverse("tasks", kwargs={"task_type": "invalid-type"})
        data = {
            "task_args": {},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    @patch("grimoirelab.core.scheduler.api.schedule_task")
    def test_create_task_missing_required_fields(self, mock_schedule_task):
        """Test creating a task with missing required fields"""

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        data = {
            "datasource_type": "git",
            # Missing datasource_category and task_args
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("grimoirelab.core.scheduler.api.schedule_task")
    def test_create_task_schedule_error(self, mock_schedule_task):
        """Test error handling when scheduling task fails"""

        mock_schedule_task.side_effect = Exception("Scheduling failed")

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        data = {
            "datasource_type": "git",
            "datasource_category": "commit",
            "task_args": {"uri": "https://github.com/example/repo.git"},
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("Error scheduling task", response.data["detail"])

    def test_list_eventizer_tasks(self):
        """Test that it returns a list of eventizer tasks"""

        # Create some test tasks
        task1 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo1.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task2 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo2"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="github",
            datasource_category="issue",
        )

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.datasource_type, task_data["datasource_type"])
        self.assertEqual(task1.datasource_category, task_data["datasource_category"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.datasource_type, task_data["datasource_type"])
        self.assertEqual(task2.datasource_category, task_data["datasource_category"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_sortinghat_tasks(self):
        """Test that it returns a list of sortinghat tasks"""

        # Create some test tasks using create_task to properly generate UUIDs
        task1 = SortingHatTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            job_type="unify",
        )
        task2 = SortingHatTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            job_type="affiliate",
        )

        url = reverse("tasks", kwargs={"task_type": "sortinghat"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 2)

        # Check tasks
        task_data = response.data["results"][0]
        self.assertEqual(task1.uuid, task_data["uuid"])
        self.assertEqual(task1.job_type, task_data["job_type"])
        self.assertEqual(task1.task_args, task_data["task_args"])
        self.assertEqual(task1.job_interval, task_data["job_interval"])
        self.assertEqual(task1.job_max_retries, task_data["job_max_retries"])

        task_data = response.data["results"][1]
        self.assertEqual(task2.uuid, task_data["uuid"])
        self.assertEqual(task2.job_type, task_data["job_type"])
        self.assertEqual(task2.task_args, task_data["task_args"])
        self.assertEqual(task2.job_interval, task_data["job_interval"])
        self.assertEqual(task2.job_max_retries, task_data["job_max_retries"])

    def test_list_tasks_with_status_filter(self):
        """Test filtering tasks by status"""

        task1 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo1.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task1.status = SchedulerStatus.NEW
        task1.save()

        task2 = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo2.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )
        task2.status = SchedulerStatus.COMPLETED
        task2.save()

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url, {"status": SchedulerStatus.NEW})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "new")

    def test_list_tasks_pagination(self):
        """Test that tasks are properly paginated"""

        # Create multiple tasks
        for i in range(30):
            EventizerTask.create_task(
                task_args={"uri": f"https://github.com/example/repo{i}.git"},
                job_interval=3600,
                job_max_retries=3,
                datasource_type="git",
                datasource_category="commit",
            )

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url, {"page": 2, "size": 10})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 30)
        self.assertEqual(response.data["page"], 2)
        self.assertEqual(response.data["total_pages"], 3)
        self.assertEqual(len(response.data["results"]), 10)

    def test_list_tasks_invalid_type(self):
        """Test listing tasks with invalid task type"""

        url = reverse("tasks", kwargs={"task_type": "invalid-type"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse("tasks", kwargs={"task_type": "eventizer"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RetrieveDestroyTaskApiTest(APITestCase):
    """Unit tests for the Retrieve Destroy Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_eventizer_task(self):
        """Test retrieving an eventizer task"""

        task = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )

        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["datasource_type"], "git")
        self.assertEqual(response.data["datasource_category"], "commit")

    def test_get_sortinghat_task(self):
        """Test retrieving a sortinghat task"""

        task = SortingHatTask.create_task(
            task_args={},
            job_interval=3600,
            job_max_retries=3,
            job_type="unify",
        )

        url = reverse("task-detail", kwargs={"task_type": "sortinghat", "uuid": task.uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["uuid"], task.uuid)
        self.assertEqual(response.data["job_type"], "unify")

    def test_get_task_not_found(self):
        """Test retrieving a task that doesn't exist"""

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_task_invalid_type(self):
        """Test retrieving a task with invalid task type"""

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "invalid-type", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_delete_task(self):
        """Test deleting a task"""

        task = EventizerTask.create_task(
            task_args={"uri": "https://github.com/example/repo.git"},
            job_interval=3600,
            job_max_retries=3,
            datasource_type="git",
            datasource_category="commit",
        )

        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": task.uuid})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Verify task is deleted
        self.assertFalse(EventizerTask.objects.filter(uuid=task.uuid).exists())

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        fake_uuid = "fake_task_uuid"
        url = reverse("task-detail", kwargs={"task_type": "eventizer", "uuid": fake_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RescheduleTaskApiTest(APITestCase):
    """Unit tests for the Reschedule Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    @patch("grimoirelab.core.scheduler.api.reschedule_task")
    def test_reschedule_task(self, mock_reschedule_task):
        """Test rescheduling a task"""

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("rescheduled", response.data[0])
        mock_reschedule_task.assert_called_once_with(task_uuid)

    @patch("grimoirelab.core.scheduler.api.reschedule_task")
    def test_reschedule_task_not_found(self, mock_reschedule_task):
        """Test rescheduling a task that doesn't exist"""

        from grimoirelab.core.scheduler.errors import NotFoundError

        mock_reschedule_task.side_effect = NotFoundError(element="Task")

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("not found", response.data["detail"])

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("task-reschedule", kwargs={"task_type": "eventizer", "uuid": task_uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CancelTaskApiTest(APITestCase):
    """Unit tests for the Cancel Task API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    @patch("grimoirelab.core.scheduler.api.cancel_task")
    def test_cancel_task(self, mock_cancel_task):
        """Test cancelling a task"""

        task_uuid = "test_task_uuid"
        url = reverse("task-cancel", kwargs={"task_type": "eventizer", "uuid": task_uuid})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("cancelled", response.data[0])
        mock_cancel_task.assert_called_once_with(task_uuid)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("task-cancel", kwargs={"task_type": "eventizer", "uuid": task_uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ListJobsApiTest(APITestCase):
    """Unit tests for the List Jobs API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_list_jobs_invalid_task_type(self):
        """Test listing jobs with invalid task type"""

        task_uuid = "test_task_uuid"
        url = reverse("jobs", kwargs={"task_type": "invalid-type", "task_id": task_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        url = reverse("jobs", kwargs={"task_type": "eventizer", "task_id": task_uuid})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JobDetailApiTest(APITestCase):
    """Unit tests for the Job Detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_job_invalid_task_type(self):
        """Test retrieving job details with invalid task type"""

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-detail",
            kwargs={"task_type": "invalid-type", "task_id": task_uuid, "uuid": job_uuid},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-detail", kwargs={"task_type": "eventizer", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class JobLogsApiTest(APITestCase):
    """Unit tests for the Job Logs API"""

    def setUp(self):
        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_job_logs_invalid_task_type(self):
        """Test retrieving job logs with invalid task type"""

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-logs", kwargs={"task_type": "invalid-type", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Unknown task type", str(response.data))

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        task_uuid = "test_task_uuid"
        job_uuid = "test_job_uuid"
        url = reverse(
            "job-logs", kwargs={"task_type": "eventizer", "task_id": task_uuid, "uuid": job_uuid}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
