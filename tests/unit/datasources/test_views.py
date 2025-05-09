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

import json

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase, Client
from django.urls import reverse

from grimoirelab.core.datasources.models import Repository
from grimoirelab.core.scheduler.tasks.models import EventizerTask


class TestAddRepository(TestCase):
    """Unit tests for add_repository"""

    def setUp(self):
        self.client = Client()
        self.user = get_user_model().objects.create_user(username='testuser', password='testpassword', is_superuser=True)
        self.client.login(username='testuser', password='testpassword')
        self.url = reverse('add_repository')
        self.valid_data = {
            'uri': "https://example.com/repo.git",
            'datasource_type': 'git',
            'datasource_category': 'commit',
            'scheduler': {
                'job_interval': 86400,
                'job_max_retries': 3,
                'force_run': False
            }
        }
        self.task = EventizerTask.create_task(
            task_args={'uri': 'uri'},
            job_interval=86400,
            job_max_retries=3,
            datasource_type='git',
            datasource_category='commit'
        )

    @patch('grimoirelab.core.datasources.views.schedule_task')
    def test_add_repository_valid(self, mock_schedule_task):
        """Test adding a repository with valid data"""

        mock_schedule_task.return_value = self.task

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'ok',
            'task_id': self.task.uuid,
            'message': f"Repository {self.valid_data['uri']} added correctly"
        })

    def test_add_repository_invalid_json(self):
        """Test adding a repository with invalid JSON"""

        response = self.client.post(
            self.url,
            data="invalid json",
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'detail': 'JSON parse error - Expecting value: line 1 column 1 (char 0)'})

    def test_add_repository_missing_parameters(self):
        """Test adding a repository with missing parameters"""

        invalid_data = self.valid_data.copy()
        del invalid_data['uri']

        response = self.client.post(
            self.url,
            data=json.dumps(invalid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"error": "Missing parameters"})

    def test_add_repository_already_exists(self):
        """Test adding a repository that already exists"""

        # Make the repository already existing
        Repository.objects.create(
            uri="https://example.com/repo.git",
            datasource_type="git",
            datasource_category="commit",
            task=self.task
        )
        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.json(), {"error": "Repository already exists"})

    def test_add_repository_authentication_required(self):
        """Test adding a repository without authentication"""

        self.client.logout()

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_add_repository_permission_denied(self):
        """Test adding a repository with insufficient permissions."""

        # Create a user without permissions
        get_user_model().objects.create_user(username='nopermuser', password='nopermpassword')
        self.client.login(username='nopermuser', password='nopermpassword')

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"message": "You do not have permission to perform this action."})

    @patch('grimoirelab.core.datasources.views.schedule_task')
    def test_add_repository_valid_permissions(self, mock_schedule_task):
        """Test adding a repository with valid permissions."""

        mock_schedule_task.return_value = self.task

        # Create a user with permissions
        user = get_user_model().objects.create_user(username='user', password='password')
        perm = Permission.objects.get(codename='add_repository')
        user.user_permissions.add(perm)
        self.client.login(username='user', password='password')

        response = self.client.post(
            self.url,
            data=json.dumps(self.valid_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'status': 'ok',
            'task_id': self.task.uuid,
            'message': f"Repository {self.valid_data['uri']} added correctly"
        })
