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

from django.test import TestCase
from django.db.utils import IntegrityError

from grimoirelab.core.datasources.models import Repository, Ecosystem
from grimoirelab.core.scheduler.tasks.models import EventizerTask


class RepositoryModelTest(TestCase):
    """Unit tests for Repository model"""

    def setUp(self):
        self.task = EventizerTask.create_task(
            task_args={'uri': 'uri'},
            job_interval=86400,
            job_max_retries=3,
            datasource_type='git',
            datasource_category='commit'
        )

    def test_create_repository(self):
        """Test creating a repository"""

        repository = Repository.objects.create(
            uri="http://example.com",
            datasource_type="type1",
            datasource_category="category1",
            task=self.task
        )
        self.assertEqual(repository.uri, "http://example.com")
        self.assertEqual(repository.datasource_type, "type1")
        self.assertEqual(repository.datasource_category, "category1")
        self.assertEqual(repository.task, self.task)

    def test_unique_together_constraint(self):
        """Test the unique_together constraint"""

        Repository.objects.create(
            uri="http://example.com",
            datasource_type="type1",
            datasource_category="category1",
            task=self.task
        )
        with self.assertRaises(IntegrityError):
            Repository.objects.create(
                uri="http://example.com",
                datasource_type="type1",
                datasource_category="category1",
                task=self.task
            )

    def test_repository_without_task(self):
        """Test creating a repository without a task"""

        repository = Repository.objects.create(
            uri="http://example.com",
            datasource_type="type1",
            datasource_category="category1",
            task=None
        )
        self.assertIsNone(repository.task)


class EcosystemModelTest(TestCase):
    """Unit tests for the Ecosystem model"""

    def test_create_ecosystem(self):
        """Test creating an ecosystem"""
        ecosystem = Ecosystem.objects.create(
            name="example-ecosystem",
            title="Example Ecosystem",
            description="lorem ipsum"
        )
        self.assertEqual(ecosystem.name, "example-ecosystem")
        self.assertEqual(ecosystem.title, "Example Ecosystem")
        self.assertEqual(ecosystem.description, "lorem ipsum")

    def test_unique_name(self):
        """Test the unique contraint"""

        Ecosystem.objects.create(
            name="example-ecosystem",
            title="Example Ecosystem",
            description="lorem ipsum"
        )
        with self.assertRaises(IntegrityError):
            Ecosystem.objects.create(name="example-ecosystem")
