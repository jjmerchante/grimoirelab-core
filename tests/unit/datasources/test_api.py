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
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grimoirelab.core.datasources.models import Ecosystem

INVALID_NAME_ERROR = ('Field may only contain alphanumeric characters or hyphens. '
                      'It may only start with a letter and cannot end with a hyphen.')


class EcosystemListApiTest(APITestCase):
    """Unit tests for the Ecosystem API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_create_ecosystem(self):
        """Test creating an ecosystem"""

        url = reverse('ecosystem-list')
        data = {
            'name': 'example-ecosystem123',
            'title': 'Example Ecosystem',
            'description': 'lorem ipsum'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'example-ecosystem123')
        self.assertEqual(response.data['title'], 'Example Ecosystem')
        self.assertEqual(response.data['description'], 'lorem ipsum')

    def test_unique_name(self):
        """Test the unique contraint for the name field"""

        Ecosystem.objects.create(name='example-ecosystem')

        url = reverse('ecosystem-list')
        data = {
            'name': 'example-ecosystem',
            'title': 'Example Ecosystem',
            'description': 'lorem ipsum'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {'name': ['ecosystem with this name already exists.']})

    def test_invalid_name(self):
        """Test that non alphanumeric or hyphen characters are invalid"""

        url = reverse('ecosystem-list')
        data = {
            'name': 'example!',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_invalid_name_first_character(self):
        """Test that it returns an error if the first character is not a letter"""

        url = reverse('ecosystem-list')
        data = {
            'name': '123example-ecosystem',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_invalid_name_last_character(self):
        """Test that it returns an error if it ends with a hyphen"""

        url = reverse('ecosystem-list')
        data = {
            'name': 'example-',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_ecosystem_list(self):
        """Test that it returns a list of ecosystems"""

        Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        Ecosystem.objects.create(name='ecosystem2', title='Ecosystem 2', description='lorem ipsum')

        url = reverse('ecosystem-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        ecosystem = response.data['results'][0]
        self.assertEqual(ecosystem['name'], 'ecosystem1')
        self.assertEqual(ecosystem['title'], 'Ecosystem 1')
        self.assertEqual(ecosystem['description'], None)

        ecosystem = response.data['results'][1]
        self.assertEqual(ecosystem['name'], 'ecosystem2')
        self.assertEqual(ecosystem['title'], 'Ecosystem 2')
        self.assertEqual(ecosystem['description'], 'lorem ipsum')

    def test_ecosystem_list_pagination(self):
        """Test that it returns a paginated list of ecosystems"""

        Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        Ecosystem.objects.create(name='ecosystem2', title='Ecosystem 2', description='lorem ipsum')
        Ecosystem.objects.create(name='ecosystem3', title='Ecosystem 3')

        url = reverse('ecosystem-list')
        response = self.client.get(url, {'page': 2, 'size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_pages'], 3)
        self.assertEqual(len(response.data['results']), 1)

        ecosystem = response.data['results'][0]
        self.assertEqual(ecosystem['name'], 'ecosystem2')
        self.assertEqual(ecosystem['title'], 'Ecosystem 2')
        self.assertEqual(ecosystem['description'], 'lorem ipsum')

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('ecosystem-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')


class EcosystemDetailApiTest(APITestCase):
    """Unit tests for the Ecosystem detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_ecosystem(self):
        """Test that it returns an ecosystem"""

        Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-ecosystem')
        self.assertEqual(response.data['title'], 'Example Ecosystem')
        self.assertEqual(response.data['description'], None)

    def test_ecosystem_not_found(self):
        """Test if it returns an error if the ecosystem does not exist"""

        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No Ecosystem matches the given query.')

    def test_update_ecosystem(self):
        """Test that it updates an ecosystem"""

        Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        data = {
            'description': 'lorem ipsum'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-ecosystem')
        self.assertEqual(response.data['title'], 'Example Ecosystem')
        self.assertEqual(response.data['description'], 'lorem ipsum')

    def test_update_ecosystem_invalid_name(self):
        """Test that it returns an error if the updated name is invalid"""

        Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        data = {
            'name': '123example-ecosystem'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_update_ecosystem_duplicated_name(self):
        """Test that it returns an error if the updated name already exists"""

        Ecosystem.objects.create(name='example-ecosystem-1')

        Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        data = {
            'name': 'example-ecosystem-1'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], ['ecosystem with this name already exists.'])

    def test_delete_ecosystem(self):
        """Test that it deletes an ecosystem"""

        Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        url = reverse('ecosystem-detail', kwargs={'name': 'example-ecosystem'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(ObjectDoesNotExist):
            Ecosystem.objects.get(name='example-ecosystem')
