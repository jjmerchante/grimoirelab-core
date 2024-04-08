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
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import datetime
import json
import logging
import os
import pickle
import shutil
import tempfile

import rq
from django.test import TestCase

from grimoirelab.core.scheduler.jobs import JobLogHandler, JobResult, PercevalJob

from .base import TestBaseRQ


class TestJobLogHandler(TestBaseRQ):
    """Unit tests for JobLogHandler class"""

    def test_job_log_handler_init(self):
        """Tests whether the handler has initialized well"""

        job_a = rq.job.Job(connection=self.conn)
        meta_handler = JobLogHandler(job_a)
        self.assertEqual(meta_handler.job, job_a)
        self.assertListEqual(meta_handler.job.meta['log'], [])

    def test_job_log_handler_emit(self):
        """Tests whether the handler catches the messages from the logger that handles"""

        job_a = rq.job.Job(connection=self.conn)

        # Create handler
        meta_handler = JobLogHandler(job_a)

        # Get logger of this current context and add set level to INFO in order to save info and upper
        logger = logging.getLogger(__name__)
        logger.addHandler(meta_handler)
        logger.setLevel(logging.INFO)

        # Write in the logger
        logger.error("Error log to the handler")
        logger.warning("Warning log to the handler")
        logger.info("Info log to the handler")

        # Check if the logs are saved in the job meta field
        self.assertEqual(len(job_a.meta['log']), 3)
        self.assertEqual(sorted(list(job_a.meta['log'][0].keys())), ['created', 'level', 'module', 'msg'])
        self.assertRegex(job_a.meta['log'][0]['msg'], 'Error')
        self.assertRegex(job_a.meta['log'][-1]['msg'], 'Info')


class TestJobResult(TestCase):
    """Unit tests for JobResult class"""

    def test_job_result_init(self):
        result = JobResult('1234567890', 'mytask',
                           'mock_backend', 'category')

        self.assertEqual(result.job_id, '1234567890')
        self.assertEqual(result.task_id, 'mytask')
        self.assertEqual(result.backend, 'mock_backend')
        self.assertEqual(result.category, 'category')
        self.assertEqual(result.summary, None)

    def test_to_dict(self):
        """Test whether a JobResult object is converted to a dict"""

        result = JobResult('1234567890', 'mytask',
                           'mock_backend', 'category')

        expected = {
            'job_id': '1234567890',
            'task_id': 'mytask'
        }

        d = result.to_dict()
        self.assertEqual(d, expected)


class TestPercevalJob(TestBaseRQ):
    """Unit tests for PercevalJob class"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix='grimoire_sched_')
        self.dir = os.path.dirname(os.path.realpath(__file__))
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.tmp_path)
        super().tearDown()

    def test_backend_not_found(self):
        """Test if it fails when a backend is not found"""

        job_args = {
            'qitems': 'items',
            'task_id': 'mytask',
            'backend': 'random-backend',
            'category': 'unknown',
            'backend_args': {}
        }
        q = rq.Queue('my-queue',
                     job_class=PercevalJob,
                     connection=self.conn,
                     is_async=False)
        job = q.enqueue(f=PercevalJob.run,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='job-backend-error',
                        **job_args)

        self.assertTrue(job.is_failed)

    def test_git_job(self):
        """Test run method using the Git backend"""

        job_args = {
            'qitems': 'items',
            'task_id': 'mytask',
            'backend': 'git',
            'category': 'commit',
            'backend_args': {
                'uri': 'http://example.com/',
                'gitpath': os.path.join(self.dir, 'data/git_log.txt')
            }
        }

        q = rq.Queue('my-queue',
                     job_class=PercevalJob,
                     connection=self.conn,
                     is_async=False)
        job = q.enqueue(f=PercevalJob.run,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='job-id-1',
                        **job_args)

        result = job.return_value()
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.task_id, 'mytask')
        self.assertEqual(result.backend, 'git')
        self.assertEqual(result.category, 'commit')
        self.assertEqual(result.summary.last_uuid, '1375b60d3c23ac9b81da92523e4144abc4489d4c')
        self.assertEqual(result.summary.max_updated_on,
                         datetime.datetime(2014, 2, 12, 6, 10, 39,
                                           tzinfo=datetime.timezone.utc))
        self.assertEqual(result.summary.last_updated_on,
                         datetime.datetime(2012, 8, 14, 17, 30, 13,
                                           tzinfo=datetime.timezone.utc))
        self.assertEqual(result.summary.total, 9)
        self.assertEqual(result.summary.max_offset, 'ce8e0b86a1e9877f42fe9453ede418519115f367')

        events = self.conn.lrange('items', 0, -1)
        events = [json.loads(e) for e in events]

        expected = [('2d85a883e0ef63ebf7fa40e372aed44834092592', 'org.grimoirelab.events.git.merge'),
                    ('048d4869b8051acb0196d207c032210a980a7da4', 'org.grimoirelab.events.git.file.modified'),
                    ('08db95eaf93968579a681701f347d94455ba6574', 'org.grimoirelab.events.git.file.replaced'),
                    ('d7226f6c921128190f644fb659c61b3ef6360b91', 'org.grimoirelab.events.git.commit'),
                    ('c0fd3bbdcbebf0232b010166d132cafecf5943f8', 'org.grimoirelab.events.git.file.modified'),
                    ('16c99217dc3185c760cc64985271e2d5b2fbbe39', 'org.grimoirelab.events.git.commit'),
                    ('ef282262cd85859b7ff2230828da6314b8230263', 'org.grimoirelab.events.git.file.replaced'),
                    ('81df8221af2e63715ad3ff1f5fd41f9a1f2723e4', 'org.grimoirelab.events.git.commit'),
                    ('8c5c6442870f9b0b7d36246c8b04d544adbc5c1c', 'org.grimoirelab.events.git.file.added'),
                    ('504a6e9e5ba7dad1b275489b775d45cc8d77a790', 'org.grimoirelab.events.git.commit'),
                    ('bb2012e4a54c60c7d91d628b6cd08bbca6a65ee8', 'org.grimoirelab.events.git.file.added'),
                    ('e8460b1df2147e217e12cfa7404191af589f62cb', 'org.grimoirelab.events.git.commit'),
                    ('93ea3e9c6b1f77f00894b1c361d7ee16a0490299', 'org.grimoirelab.events.git.file.deleted'),
                    ('526635a03e351ba1e45964c45b695906a17f5493', 'org.grimoirelab.events.git.file.replaced'),
                    ('e5ff829d3f1bacf6a6d3e36cd996a1308351f9a5', 'org.grimoirelab.events.git.commit'),
                    ('5ee17ed5caf8cf3fc33e50ab3b46e2fe66d5cd71', 'org.grimoirelab.events.git.file.added'),
                    ('caf05717b6c53143bd29a2140eb9c043aaefb255', 'org.grimoirelab.events.git.commit'),
                    ('1c837b8c685112760eb5829c3da7c495f67e7c44', 'org.grimoirelab.events.git.file.replaced'),
                    ('1375b60d3c23ac9b81da92523e4144abc4489d4c', 'org.grimoirelab.events.git.commit'),
                    ('48335db7cb8e6db4367ac2543d0c92deb2a655ce', 'org.grimoirelab.events.git.file.added'),
                    ('fa4a64cb04f8c9fef6c0143d874e90e7c5f4f3fc', 'org.grimoirelab.events.git.file.added'),
                    ('9e5000b81d4d9554587df37f81bf64de10b23ec8', 'org.grimoirelab.events.git.file.added')]

        for i, event in enumerate(events):
            self.assertEqual(event['id'], expected[i][0])
            self.assertEqual(event['type'], expected[i][1])
            self.assertEqual(event['source'], 'http://example.com/')

    def test_git_job_no_result(self):
        """Execute a Git backend job that will not produce any results"""

        job_args = {
            'qitems': 'items',
            'task_id': 'mytask',
            'backend': 'git',
            'category': 'commit',
            'backend_args': {
                'uri': 'http://example.com/',
                'gitpath': os.path.join(self.dir, 'data/git_log_empty.txt'),
                'from_date': datetime.datetime(2020, 1, 1, 1, 1, 1)
            }
        }

        q = rq.Queue('my-queue',
                     job_class=PercevalJob,
                     connection=self.conn,
                     is_async=False)
        job = q.enqueue(f=PercevalJob.run,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='job-id-1',
                        **job_args)

        result = job.return_value()
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.task_id, 'mytask')
        self.assertEqual(result.backend, 'git')
        self.assertEqual(result.category, 'commit')
        self.assertEqual(result.summary.last_uuid, None)
        self.assertEqual(result.summary.max_updated_on, None)
        self.assertEqual(result.summary.last_updated_on, None)
        self.assertEqual(result.summary.total, 0)
        self.assertEqual(result.summary.max_offset, None)

        commits = self.conn.lrange('items', 0, -1)
        commits = [pickle.loads(c) for c in commits]
        self.assertListEqual(commits, [])
