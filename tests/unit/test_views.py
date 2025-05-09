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

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, Client


class TestViews(TestCase):
    """Unit tests for views."""

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='testuser',
            password='testpassword'
        )
        self.client = Client()

    def test_api_login(self):
        """Test the api_login view."""

        url = reverse('api_login')
        data = {
            'username': 'testuser',
            'password': 'testpassword'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.data)
        self.assertIn('isAdmin', response.data)

    def test_api_login_invalid(self):
        """Test the api_login view with invalid credentials."""

        url = reverse('api_login')
        data = {
            'username': 'testuser',
            'password': 'wrongpassword'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertIn('errors', response.data)
        self.assertEqual(response.data['errors'], 'Invalid credentials.')

    def test_change_password(self):
        """Test the change_password view."""

        self.client.login(username='testuser', password='testpassword')

        url = reverse('password_change')
        data = {
            'old_password': 'testpassword',
            'new_password1': 'TestNewPassword123',
            'new_password2': 'TestNewPassword123'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertIn('updated', response.data)
        self.assertEqual(response.data['updated'], 'testuser')

        # Check if the password has been changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('TestNewPassword123'))

    def test_change_password_invalid(self):
        """Test the change_password view with invalid data."""

        self.client.login(username='testuser', password='testpassword')

        url = reverse('password_change')
        data = {
            'old_password': 'wrongpassword',
            'new_password1': 'TestNewPassword123',
            'new_password2': 'TestNewPassword123'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('errors', response.data)
