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

import rq

from grimoirelab.core.scheduler.jobs import GrimoireLabJob
from grimoirelab.core.scheduler.tasks.archivist import (
    ArchivistProgress,
    StorageBackend,
    archivist_job
)

from ..base import GrimoireLabTestCase


class MockStorageBackend(StorageBackend):
    """Class to store events in the class itself for later inspection"""

    events = []

    def store(self, events: iter) -> int:
        events = [e for e in events]
        MockStorageBackend.events.extend(events)
        return len(events)

    @classmethod
    def get_events(cls):
        return cls.events

    @classmethod
    def clear_events(cls):
        cls.events = []


class TestArchivistJob(GrimoireLabTestCase):
    """Unit tests for archivist_job function"""

    def setUp(self):
        MockStorageBackend.clear_events()
        super().setUp()

    def tearDown(self):
        MockStorageBackend.clear_events()
        super().tearDown()

    def test_job(self):
        """Test if events are stored correctly"""

        # Add some sample events to the stream
        expected_events = [
            {'uuid': '1', 'timestamp': '2021-01-01T00:00:00Z', 'data': 'event 1'},
            {'uuid': '2', 'timestamp': '2021-01-02T00:00:00Z', 'data': 'event 2'},
            {'uuid': '3', 'timestamp': '2021-01-03T00:00:00Z', 'data': 'event 3'},
            {'uuid': '4', 'timestamp': '2021-01-04T00:00:00Z', 'data': 'event 4'},
            {'uuid': '5', 'timestamp': '2021-01-05T00:00:00Z', 'data': 'event 5'},
            {'uuid': '6', 'timestamp': '2021-01-06T00:00:00Z', 'data': 'event 6'},
            {'uuid': '7', 'timestamp': '2021-01-07T00:00:00Z', 'data': 'event 7'},
            {'uuid': '8', 'timestamp': '2021-01-08T00:00:00Z', 'data': 'event 8'},
            {'uuid': '9', 'timestamp': '2021-01-09T00:00:00Z', 'data': 'event 9'},
            {'uuid': '10', 'timestamp': '2021-01-10T00:00:00Z', 'data': 'event 10'},
        ]

        for e in expected_events:
            message = {
                'data': json.dumps(e)
            }
            self.conn.xadd('test-events', message, maxlen=len(expected_events))

        # Create the job
        job_args = {
            'storage_type': 'mock_storage',
            'storage_url': 'example.com',
            'storage_username': 'user',
            'storage_password': 'password',
            'storage_db_name': 'mock_db',
            'storage_verify_certs': True,
            'redis_group': 'archivist',
            'consumer_name': 'consumer_1',
            'events_queue': 'test-events',
            'limit': 10
        }
        with patch('grimoirelab.core.scheduler.tasks.archivist.get_storage_backend',
                   return_value=MockStorageBackend):
            q = rq.Queue(
                'test-queue',
                job_class=GrimoireLabJob,
                connection=self.conn,
                is_async=False
            )
            job = q.enqueue(f=archivist_job,
                            result_ttl=100,
                            job_timeout=120,
                            job_id='archive-events',
                            **job_args)
            result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, 'mock_storage')
        self.assertEqual(result.group, 'archivist')
        self.assertEqual(result.consumer_name, 'consumer_1')
        self.assertEqual(result.total, len(expected_events))

        stored_events = MockStorageBackend.get_events()
        for result_event, event in zip(stored_events, expected_events):
            self.assertDictEqual(result_event, event)

    def test_job_no_result(self):
        """Execute a job that will not produce any results"""

        job_args = {
            'storage_type': 'mock_storage',
            'storage_url': 'example.com',
            'storage_username': 'user',
            'storage_password': 'password',
            'storage_db_name': 'mock_db',
            'storage_verify_certs': True,
            'redis_group': 'archivist',
            'consumer_name': 'consumer_1',
            'events_queue': 'test-events',
            'block_timeout': None,
            'limit': 10
        }
        with patch('grimoirelab.core.scheduler.tasks.archivist.get_storage_backend',
                   return_value=MockStorageBackend):
            q = rq.Queue(
                'test-queue',
                job_class=GrimoireLabJob,
                connection=self.conn,
                is_async=False
            )
            job = q.enqueue(f=archivist_job,
                            result_ttl=100,
                            job_timeout=120,
                            job_id='archive-events',
                            **job_args)

            result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, 'mock_storage')
        self.assertEqual(result.group, 'archivist')
        self.assertEqual(result.consumer_name, 'consumer_1')
        self.assertEqual(result.total, 0)

        stored_events = MockStorageBackend.get_events()
        self.assertEqual(len(stored_events), 0)

    def test_backend_not_found(self):
        """Test if it fails when a storage_type is not found"""

        job_args = {
            'storage_type': 'nobackend',
            'storage_url': 'example.com',
            'storage_username': 'user',
            'storage_password': 'password',
            'storage_db_name': 'mock_db',
            'storage_verify_certs': True,
            'redis_group': 'archivist',
            'consumer_name': 'consumer_1',
            'events_queue': 'test-events',
        }
        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue(f=archivist_job,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='archive-events',
                        **job_args)
        self.assertTrue(job.is_failed)


class TestArchivistProgress(GrimoireLabTestCase):
    """Unit tests for ArchivistProgress class"""

    def test_init(self):
        """Tests whether the ArchivistProgress initialization is correct"""

        progress = ArchivistProgress(job_id='1234567890', backend='opensearch',
                                     group='storage_grp', consumer_name='consumer_1',
                                     total=100)

        self.assertEqual(progress.job_id, '1234567890')
        self.assertEqual(progress.backend, 'opensearch')
        self.assertEqual(progress.group, 'storage_grp')
        self.assertEqual(progress.consumer_name, 'consumer_1')
        self.assertEqual(progress.total, 100)

    def test_from_dict(self):
        """Tests whether the ArchivistProgress object is created from a dict"""

        job_id = '1234567890'
        backend = 'opensearch'
        group = 'storage_grp'
        consumer_name = 'consumer_1'
        total = 100

        data = {
            'job_id': job_id,
            'backend': backend,
            'group': group,
            'consumer_name': consumer_name,
            'total': total
        }

        progress = ArchivistProgress.from_dict(data)

        self.assertEqual(progress.job_id, job_id)
        self.assertEqual(progress.backend, backend)
        self.assertEqual(progress.group, group)
        self.assertEqual(progress.consumer_name, consumer_name)
        self.assertEqual(progress.total, total)

    def test_to_dict(self):
        """Tests whether the ArchivistProgress object is converted to a dict"""

        job_id = '12345678'
        backend = 'git'
        group = 'storage_grp'
        consumer_name = 'consumer_1'
        total = 100

        progress = ArchivistProgress(job_id, backend, group, consumer_name, total)

        expected = {
            'job_id': job_id,
            'backend': backend,
            'group': group,
            'consumer_name': consumer_name,
            'total': total
        }

        d = progress.to_dict()
        self.assertEqual(d, expected)
