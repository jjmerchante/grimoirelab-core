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

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from grimoirelab.core.datasources.models import Ecosystem, Project, Repository, DataSet
from grimoirelab.core.datasources.utils import generate_uuid
from grimoirelab.core.scheduler.tasks.models import EventizerTask

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


class ProjectListApiTest(APITestCase):
    """Unit tests for the Project API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_create_project(self):
        """Test creating a project"""

        Ecosystem.objects.create(name='ecosystem1')
        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': 'example-project',
            'title': 'Example Project',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], 'Example Project')
        self.assertEqual(response.data['parent_project'], None)
        self.assertEqual(len(response.data['subprojects']), 0)
        self.assertEqual(len(response.data['repos']), 0)

    def test_create_project_parent(self):
        """Test creating a project with a parent project"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1')
        parent_project = Project.objects.create(name="parent-project", ecosystem=ecosystem)
        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': 'example-project',
            'title': 'Example Project',
            'parent_project': parent_project.id
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], 'Example Project')
        self.assertEqual(response.data['parent_project'], parent_project.id)
        self.assertEqual(len(response.data['subprojects']), 0)
        self.assertEqual(len(response.data['repos']), 0)

    def test_unique_together(self):
        """Test the unique together constraint"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1')
        Project.objects.create(name="example-project", ecosystem=ecosystem)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': 'example-project',
            'title': 'Example Project',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], ["Ecosystem 'ecosystem1' already has a project named 'example-project'"])

    def test_invalid_name(self):
        """Test that non alphanumeric or hyphen characters are invalid"""

        Ecosystem.objects.create(name='ecosystem1')
        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': 'example@',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_invalid_name_first_character(self):
        """Test that it returns an error if the first character is not a letter"""

        Ecosystem.objects.create(name='ecosystem1')
        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': '123example-project',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_invalid_name_last_character(self):
        """Test that it returns an error if it ends with a hyphen"""

        Ecosystem.objects.create(name='ecosystem1')
        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        data = {
            'name': 'example-',
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_ecosystem_projects_list(self):
        """Test that it returns a list of projects for an ecosystem"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        project1 = Project.objects.create(name="project1",
                                          title="Project 1",
                                          ecosystem=ecosystem)
        project2 = Project.objects.create(name="project2",
                                          title="Project 2",
                                          ecosystem=ecosystem)
        project3 = Project.objects.create(name="project3",
                                          title="Project 3",
                                          parent_project=project2,
                                          ecosystem=ecosystem)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        project = response.data['results'][0]
        self.assertEqual(project['id'], project1.id)
        self.assertEqual(project['name'], 'project1')
        self.assertEqual(project['title'], 'Project 1')
        self.assertEqual(project['parent_project'], None)
        self.assertEqual(len(project['subprojects']), 0)
        self.assertEqual(len(project['repos']), 0)

        project = response.data['results'][1]
        self.assertEqual(project['id'], project2.id)
        self.assertEqual(project['name'], 'project2')
        self.assertEqual(project['title'], 'Project 2')
        self.assertEqual(len(project['subprojects']), 1)
        self.assertEqual(project['parent_project'], None)
        self.assertEqual(project['subprojects'][0], project3.name)
        self.assertEqual(len(project['repos']), 0)

    def test_projects_parent_id_filter(self):
        """Test that it returns a list of projects filtered by parent_id"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        project1 = Project.objects.create(name="project1",
                                          title="Project 1",
                                          ecosystem=ecosystem)
        project2 = Project.objects.create(name="project2",
                                          title="Project 2",
                                          ecosystem=ecosystem)
        project3 = Project.objects.create(name="project3",
                                          title="Project 3",
                                          parent_project=project2,
                                          ecosystem=ecosystem)
        project4 = Project.objects.create(name="project4",
                                          title="Project 4",
                                          parent_project=project3,
                                          ecosystem=ecosystem)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        response = self.client.get(url, {'parent_id': project2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        project = response.data['results'][0]
        self.assertEqual(project['id'], project3.id)
        self.assertEqual(project['name'], 'project3')
        self.assertEqual(project['title'], 'Project 3')
        self.assertEqual(project['parent_project'], project2.id)
        self.assertEqual(len(project['subprojects']), 1)
        self.assertEqual(project['subprojects'][0], project4.name)
        self.assertEqual(len(project['repos']), 0)

    def test_projects_term_filter(self):
        """Test that it returns a list of projects filtered by term"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        project1 = Project.objects.create(name="example-project1",
                                          title="Project 1",
                                          ecosystem=ecosystem)
        project2 = Project.objects.create(name="project2",
                                          title="Project 2",
                                          ecosystem=ecosystem)
        project3 = Project.objects.create(name="project3",
                                          title="Example project 3",
                                          parent_project=project2,
                                          ecosystem=ecosystem)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        response = self.client.get(url, {'term': 'example'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        project = response.data['results'][0]
        self.assertEqual(project['id'], project1.id)
        self.assertEqual(project['name'], 'example-project1')
        self.assertEqual(project['title'], 'Project 1')
        self.assertEqual(project['parent_project'], None)
        self.assertEqual(len(project['subprojects']), 0)
        self.assertEqual(len(project['repos']), 0)

        project = response.data['results'][1]
        self.assertEqual(project['id'], project3.id)
        self.assertEqual(project['name'], 'project3')
        self.assertEqual(project['title'], 'Example project 3')
        self.assertEqual(project['parent_project'], project2.id)
        self.assertEqual(len(project['subprojects']), 0)
        self.assertEqual(len(project['repos']), 0)

    def test_project_list_pagination(self):
        """Test that it returns a paginated list of projects"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        project1 = Project.objects.create(name="project1",
                                          title="Project 1",
                                          ecosystem=ecosystem)
        project2 = Project.objects.create(name="project2",
                                          title="Project 2",
                                          ecosystem=ecosystem)
        project3 = Project.objects.create(name="project3",
                                          title="Project 3",
                                          ecosystem=ecosystem)
        project4 = Project.objects.create(name="project4",
                                          title="Project 4",
                                          ecosystem=ecosystem)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        response = self.client.get(url, {'page': 2, 'size': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 4)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_pages'], 4)
        self.assertEqual(len(response.data['results']), 1)

        project = response.data['results'][0]
        self.assertEqual(project['id'], project2.id)
        self.assertEqual(project['name'], 'project2')
        self.assertEqual(project['title'], 'Project 2')
        self.assertEqual(len(project['subprojects']), 0)
        self.assertEqual(project['parent_project'], None)
        self.assertEqual(len(project['repos']), 0)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('projects-list', kwargs={'ecosystem_name': 'ecosystem1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')


class ProjectDetailApiTest(APITestCase):
    """Unit tests for the Project detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)

    def test_get_project(self):
        """Test that it returns a project"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        project = Project.objects.create(name="example-project",
                               title="Example Project",
                               ecosystem=ecosystem)
        Project.objects.create(name="subproject",
                               title="Example Subproject",
                               parent_project=project,
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'ecosystem1', 'name': 'example-project'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], 'Example Project')
        self.assertEqual(response.data['parent_project'], None)
        self.assertEqual(len(response.data['subprojects']), 1)
        self.assertEqual(len(response.data['repos']), 0)
        subproject = response.data['subprojects'][0]
        self.assertEqual(subproject['name'], 'subproject')
        self.assertEqual(subproject['title'], 'Example Subproject')
        self.assertEqual(subproject['subprojects'], [])
        self.assertEqual(len(subproject['repos']), 0)

    def test_get_subproject(self):
        """Test that it returns a subproject"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        parent_project = Project.objects.create(name="parent-project",
                                                title="Parent project",
                                                ecosystem=ecosystem)
        Project.objects.create(name="example-project",
                               title="Example Project",
                               parent_project=parent_project,
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'ecosystem1', 'name': 'example-project'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], 'Example Project')
        self.assertEqual(response.data['subprojects'], [])
        self.assertEqual(len(response.data['repos']), 0)
        self.assertEqual(response.data['parent_project']['id'], parent_project.id)
        self.assertEqual(response.data['parent_project']['name'], 'parent-project')
        self.assertEqual(response.data['parent_project']['title'], 'Parent project')
        self.assertEqual(response.data['parent_project']['subprojects'], ['example-project'])

    def test_project_not_found(self):
        """Test if it returns an error if the project does not exist"""

        url = reverse('projects-detail', kwargs={'ecosystem_name': 'ecosystem1', 'name': 'example-project'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No Project matches the given query.')

    def test_update_project(self):
        """Test that it updates a project"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        Project.objects.create(name="example-project",
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'ecosystem1', 'name': 'example-project'})
        data = {
            'title': 'Example title'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], 'Example title')

    def test_update_parent_project(self):
        """Test that it updates a project's parent"""

        ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        parent_project = Project.objects.create(name="parent-project",
                                                title="Parent project",
                                                ecosystem=ecosystem)
        Project.objects.create(name="example-project",
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'ecosystem1', 'name': 'example-project'})
        data = {
            'parent_project': parent_project.id
        }
        response = self.client.patch(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'example-project')
        self.assertEqual(response.data['title'], None)
        self.assertEqual(response.data['subprojects'], [])
        self.assertEqual(response.data['parent_project']['id'], parent_project.id)
        self.assertEqual(response.data['parent_project']['name'], 'parent-project')
        self.assertEqual(response.data['parent_project']['title'], 'Parent project')
        self.assertEqual(response.data['parent_project']['subprojects'], ['example-project'])

    def test_update_project_invalid_name(self):
        """Test that it returns an error if the updated name is invalid"""

        ecosystem = Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        Project.objects.create(name="example-project",
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'example-ecosystem', 'name': 'example-project'})
        data = {
            'name': '123example-project'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_json = response.json()
        self.assertEqual(response_json['name'], [INVALID_NAME_ERROR])

    def test_delete_project(self):
        """Test that it deletes a project"""

        ecosystem = Ecosystem.objects.create(name='example-ecosystem', title='Example Ecosystem')
        Project.objects.create(name="example-project",
                               ecosystem=ecosystem)
        url = reverse('projects-detail', kwargs={'ecosystem_name': 'example-ecosystem', 'name': 'example-project'})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(ObjectDoesNotExist):
            Project.objects.get(name='example-project')

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('projects-detail', kwargs={'ecosystem_name': 'example-ecosystem', 'name': 'example-project'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')


class RepoListApiTest(APITestCase):
    """Unit tests for the Repository API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)
        self.ecosystem = Ecosystem.objects.create(name='ecosystem1')
        self.project = Project.objects.create(name='project1', ecosystem=self.ecosystem)
        self.task = EventizerTask.create_task(
            task_args={'uri': 'uri'},
            job_interval=86400,
            job_max_retries=3,
            datasource_type='git',
            datasource_category='commit'
        )
        self.valid_data = {
            'uri': 'https://example.com/repo.git',
            'datasource_type': 'git',
            'category': 'commit',
            'scheduler': {
                'job_interval': 86400,
                'job_max_retries': 3,
                'force_run': False
            }
        }

    @patch('grimoirelab.core.datasources.api.schedule_task')
    def test_create_repository(self, mock_schedule_task):
        """Test creating a repository"""

        mock_schedule_task.return_value = self.task
        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'project1'})
        data = {
            'uri': 'https://example.com/repo.git',
            'datasource_type': 'git',
            'category': 'commit',
            'scheduler': {
                'job_interval': 86400,
                'job_max_retries': 3,
                'force_run': False
            }
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['uri'], 'https://example.com/repo.git')
        self.assertEqual(response.data['datasource_type'], 'git')
        self.assertEqual(len(response.data['categories']), 1)
        dataset = response.data['categories'][0]
        self.assertEqual(dataset['category'], 'commit')
        self.assertEqual(dataset['task']['uuid'], self.task.uuid)
        self.assertEqual(dataset['task']['job_interval'], 86400)

    @patch('grimoirelab.core.datasources.api.schedule_task')
    def test_create_repo_dataset(self, mock_schedule_task):
        """Test creating a dataset for a repo when it already exists"""

        mock_schedule_task.return_value = self.task
        uuid = generate_uuid('https://example.com/repo.git', 'git')
        repository = Repository.objects.create(uri='https://example.com/repo.git', datasource_type='git', uuid=uuid)
        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'project1'})

        response = self.client.post(url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['uuid'], repository.uuid)
        self.assertEqual(response.data['uri'], 'https://example.com/repo.git')
        self.assertEqual(response.data['datasource_type'], 'git')
        self.assertEqual(len(response.data['categories']), 1)
        dataset = response.data['categories'][0]
        self.assertEqual(dataset['category'], 'commit')
        self.assertEqual(dataset['task']['uuid'], self.task.uuid)
        self.assertEqual(dataset['task']['job_interval'], 86400)

    def test_add_repo_missing_parameters(self):
        """Test adding a repository with missing parameters"""

        data = {
            'datasource_type': 'git',
            'category': 'commit',
            'scheduler': {
                'job_interval': 86400,
                'job_max_retries': 3,
                'force_run': False
            }
        }
        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'project1'})
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {'uri': ['This field is required.']})

    def test_add_dataset_already_exists(self):
        """Test adding a dataset that already exists"""

        repository = Repository.objects.create(
            uri='https://example.com/repo.git',
            datasource_type="git"
        )
        DataSet.objects.create(
            project=self.project,
            repository=repository,
            category='commit',
            task=self.task
        )
        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'project1'})
        response = self.client.post(url, self.valid_data, format='json')

        self.assertEqual(response.status_code, 422)
        error = "Repository 'https://example.com/repo.git' with category 'commit' already exists in project."
        self.assertEqual(response.json(), {'non_field_errors': [error]})

    def test_add_repo_authentication_required(self):
        """Test adding a repo without authentication"""

        self.client.logout()

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'project1'})
        response = self.client.post(url, self.valid_data, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"detail": "Authentication credentials were not provided."})

    def test_project_repo_list(self):
        """Test that it returns a list of repositories for a project"""

        repository1 = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category1',
        )
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category2'
        )
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category3'
        )

        repository2 = Repository.objects.create(uuid='BBB', uri='https://example.com/repo-2.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository2,
            category='category1',
        )

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        repo = response.data['results'][0]
        self.assertEqual(repo['uuid'], 'AAA')
        self.assertEqual(repo['uri'], 'https://example.com/repo.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 3)
        self.assertEqual(repo['categories'][0]['category'], 'category1')
        self.assertEqual(repo['categories'][1]['category'], 'category2')
        self.assertEqual(repo['categories'][2]['category'], 'category3')

        repo = response.data['results'][1]
        self.assertEqual(repo['uuid'], 'BBB')
        self.assertEqual(repo['uri'], 'https://example.com/repo-2.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 1)
        self.assertEqual(repo['categories'][0]['category'], 'category1')

    def test_project_repo_list_filter_category(self):
        """Test that it returns a list of repositories for a project filtered by category"""

        repository1 = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category1',
        )
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category2'
        )
        repository2 = Repository.objects.create(uuid='BBB', uri='https://example.com/repo-2', datasource_type="github")
        DataSet.objects.create(
            project=self.project,
            repository=repository2,
            category='category1',
        )
        repository3 = Repository.objects.create(uuid='CCC', uri='https://example.com/repo-3.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository3,
            category='category2',
        )

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'category': 'category1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        repo = response.data['results'][0]
        self.assertEqual(repo['uuid'], 'AAA')
        self.assertEqual(repo['uri'], 'https://example.com/repo.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 2)
        self.assertEqual(repo['categories'][0]['category'], 'category1')
        self.assertEqual(repo['categories'][1]['category'], 'category2')

        repo = response.data['results'][1]
        self.assertEqual(repo['uuid'], 'BBB')
        self.assertEqual(repo['uri'], 'https://example.com/repo-2')
        self.assertEqual(repo['datasource_type'], 'github')
        self.assertEqual(len(repo['categories']), 1)
        self.assertEqual(repo['categories'][0]['category'], 'category1')

    def test_project_repo_list_filter_datasource(self):
        """Test that it returns a list of repositoriess for a project filtered by datasource type"""

        repository1 = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category1',
        )
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category2'
        )
        repository2 = Repository.objects.create(uuid='BBB', uri='https://example.com/repo-2', datasource_type="github")
        DataSet.objects.create(
            project=self.project,
            repository=repository2,
            category='category1',
        )
        repository3 = Repository.objects.create(uuid='CCC', uri='https://example.com/repo-3.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository3,
            category='category2',
        )

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'datasource_type': 'git'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        repo = response.data['results'][0]
        self.assertEqual(repo['uuid'], 'AAA')
        self.assertEqual(repo['uri'], 'https://example.com/repo.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 2)
        self.assertEqual(repo['categories'][0]['category'], 'category1')
        self.assertEqual(repo['categories'][1]['category'], 'category2')

        repo = response.data['results'][1]
        self.assertEqual(repo['uuid'], 'CCC')
        self.assertEqual(repo['uri'], 'https://example.com/repo-3.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 1)
        self.assertEqual(repo['categories'][0]['category'], 'category2')

    def test_project_repo_list_filter_uri(self):
        """Test that it returns a list of repositories for a project filtered by uri"""

        repository1 = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category1',
        )
        repository2 = Repository.objects.create(uuid='BBB', uri='https://example.com/repo-2', datasource_type="github")
        DataSet.objects.create(
            project=self.project,
            repository=repository2,
            category='category1',
        )
        repository3 = Repository.objects.create(uuid='CCC', uri='https://example.com/repo-3.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository3,
            category='category2',
        )

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'uri': 'https://example.com/repo-2'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        repo = response.data['results'][0]
        self.assertEqual(repo['uuid'], 'BBB')
        self.assertEqual(repo['uri'], 'https://example.com/repo-2')
        self.assertEqual(repo['datasource_type'], 'github')
        self.assertEqual(len(repo['categories']), 1)
        self.assertEqual(repo['categories'][0]['category'], 'category1')

    def test_repo_list_pagination(self):
        """Test that it returns a paginated list of repositories"""

        repository1 = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository1,
            category='category1',
        )
        repository2 = Repository.objects.create(uuid='BBB', uri='https://example.com/repo-2', datasource_type="github")
        DataSet.objects.create(
            project=self.project,
            repository=repository2,
            category='category1',
        )
        repository3 = Repository.objects.create(uuid='CCC', uri='https://example.com/repo-3.git', datasource_type="git")
        DataSet.objects.create(
            project=self.project,
            repository=repository3,
            category='category2',
        )

        url = reverse('repo-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'page': 2, 'size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_pages'], 2)

        repo = response.data['results'][0]
        self.assertEqual(repo['uuid'], 'CCC')
        self.assertEqual(repo['uri'], 'https://example.com/repo-3.git')
        self.assertEqual(repo['datasource_type'], 'git')
        self.assertEqual(len(repo['categories']), 1)
        self.assertEqual(repo['categories'][0]['category'], 'category2')


class RepoDetailApiTest(APITestCase):
    """Unit tests for the Repository detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)
        self.ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        self.project = Project.objects.create(name="example-project",
                                              title="Example Project",
                                              ecosystem=self.ecosystem)
        self.repository = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        self.dataset = DataSet.objects.create(project=self.project, repository=self.repository, category='category1')

    def test_get_repo(self):
        """Test that it returns a repository"""

        url = reverse('repo-detail', kwargs={'ecosystem_name': self.ecosystem.name,
                                             'project_name': self.project.name,
                                             'uuid': self.repository.uuid})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['uuid'], 'AAA')
        self.assertEqual(response.data['uri'], 'https://example.com/repo.git')
        self.assertEqual(response.data['datasource_type'], 'git')
        self.assertEqual(len(response.data['categories']), 1)
        self.assertEqual(response.data['categories'][0]['id'], self.dataset.id)
        self.assertEqual(response.data['categories'][0]['category'], 'category1')
        self.assertEqual(response.data['categories'][0]['task'], None)

    def test_repo_not_found(self):
        """Test if it returns an error if the repository does not exist"""

        url = reverse('repo-detail',
                      kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'example-project-2', 'uuid': 'AAA'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No Project matches the given query.')

        url = reverse('repo-detail',
                      kwargs={'ecosystem_name': 'ecosystem1', 'project_name': 'example-project', 'uuid': 12345})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No Repository matches the given query.')

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('repo-detail',
                      kwargs={'ecosystem_name': self.ecosystem.name, 'project_name': self.project.name, 'uuid': 'AAA'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')


class CategoryDetailApiTest(APITestCase):
    """Unit tests for the Category detail API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)
        self.ecosystem = Ecosystem.objects.create(name='ecosystem1', title='Ecosystem 1')
        self.project = Project.objects.create(name="example-project",
                                              title="Example Project",
                                              ecosystem=self.ecosystem)
        self.repository = Repository.objects.create(uuid='AAA', uri='https://example.com/repo.git', datasource_type="git")
        self.dataset = DataSet.objects.create(project=self.project, repository=self.repository, category='category1')

    def test_get_category(self):
        """Test that it returns a dataset"""

        url = reverse('category-detail', kwargs={'ecosystem_name': self.ecosystem.name,
                                                 'project_name': self.project.name,
                                                 'uuid': self.repository.uuid,
                                                 'category': 'category1'})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.dataset.id)
        self.assertEqual(response.data['category'], 'category1')
        self.assertEqual(response.data['task'], None)

    def test_category_not_found(self):
        """Test if it returns an error if the dataset does not exist"""

        url = reverse('category-detail', kwargs={'ecosystem_name': 'ecosystem1',
                                                 'project_name': 'example-project-2',
                                                 'uuid': 'AAA',
                                                 'category': 'category1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No Project matches the given query.')

        url = reverse('category-detail', kwargs={'ecosystem_name': 'ecosystem1',
                                                 'project_name': 'example-project',
                                                 'uuid': 'AAA',
                                                 'category': 'category2'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['detail'], 'No DataSet matches the given query.')

    def test_delete_dataset(self):
        """Test that it deletes a dataset"""

        url = reverse('category-detail', kwargs={'ecosystem_name': self.ecosystem.name,
                                                 'project_name': self.project.name,
                                                 'uuid': self.repository.uuid,
                                                 'category': self.dataset.category})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(ObjectDoesNotExist):
            DataSet.objects.get(id=self.dataset.id)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('category-detail', kwargs={'ecosystem_name': self.ecosystem.name,
                                                 'project_name': self.project.name,
                                                 'uuid': 'AAA',
                                                 'category': 'category1'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')


class ProjectChildrenApiTest(APITestCase):
    """Unit tests for the ProjectChildren API"""

    def setUp(self):
        user = get_user_model().objects.create(username='test', is_superuser=True)
        self.client.force_authenticate(user=user)
        self.ecosystem = Ecosystem.objects.create(name='ecosystem1')
        self.project = Project.objects.create(name='project1', ecosystem=self.ecosystem)

        self.subproject1 = Project.objects.create(parent_project=self.project, name='subproject1', ecosystem=self.ecosystem)
        Project.objects.create(parent_project=self.subproject1, name='subproject2', ecosystem=self.ecosystem)

        self.repository1 = Repository.objects.create(uri='https://example.com/repo.git', datasource_type="git")
        DataSet.objects.create(project=self.project, repository=self.repository1, category='category1')

        self.repository2 = Repository.objects.create(uri='https://example.com/repo2.git', datasource_type="git")
        DataSet.objects.create(project=self.project, repository=self.repository2, category='category1')
        DataSet.objects.create(project=self.subproject1, repository=self.repository2, category='category1')

    def test_project_children_list(self):
        """Test that it returns a list of children for a project"""

        url = reverse('children-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        project = response.data['results'][0]
        self.assertEqual(project['id'], self.subproject1.id)
        self.assertEqual(project['type'], 'project')
        self.assertEqual(project['name'], 'subproject1')
        self.assertEqual(project['subprojects'], 1)
        self.assertEqual(project['repos'], 1)

        repository = response.data['results'][1]
        self.assertEqual(repository['id'], self.repository1.id)
        self.assertEqual(repository['type'], 'repository')
        self.assertEqual(repository['uri'], 'https://example.com/repo.git')
        self.assertEqual(repository['categories'], 1)

        repository = response.data['results'][2]
        self.assertEqual(repository['id'], self.repository2.id)
        self.assertEqual(repository['type'], 'repository')
        self.assertEqual(repository['uri'], 'https://example.com/repo2.git')
        self.assertEqual(repository['categories'], 2)

    def test_project_children_filter_term(self):
        """Test that it returns a list of children for a project filtered by term"""

        url = reverse('children-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'term': 'repo'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(response.data['page'], 1)
        self.assertEqual(response.data['total_pages'], 1)

        repository = response.data['results'][0]
        self.assertEqual(repository['id'], self.repository1.id)
        self.assertEqual(repository['type'], 'repository')
        self.assertEqual(repository['uri'], 'https://example.com/repo.git')
        self.assertEqual(repository['categories'], 1)

        repository = response.data['results'][1]
        self.assertEqual(repository['id'], self.repository2.id)
        self.assertEqual(repository['type'], 'repository')
        self.assertEqual(repository['uri'], 'https://example.com/repo2.git')
        self.assertEqual(repository['categories'], 2)

    def test_project_children_list_pagination(self):
        """Test that it returns a paginated list of children for a project"""

        url = reverse('children-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url, {'page': 2, 'size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['page'], 2)
        self.assertEqual(response.data['total_pages'], 2)

        repository = response.data['results'][0]
        self.assertEqual(repository['id'], self.repository2.id)
        self.assertEqual(repository['type'], 'repository')
        self.assertEqual(repository['uri'], 'https://example.com/repo2.git')
        self.assertEqual(repository['categories'], 2)

    def test_unauthenticated_request(self):
        """Test that it returns an error if no credentials were provided"""

        self.client.force_authenticate(user=None)

        url = reverse('children-list', kwargs={'ecosystem_name': 'ecosystem1', 'project_name': self.project.name})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')
