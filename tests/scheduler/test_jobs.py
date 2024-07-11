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
import json
import logging
import os
import pickle
import shutil
import tempfile

import rq
import perceval.backend

from grimoirelab.core.scheduler.jobs import (GrimoireLabJob,
                                             JobLogHandler,
                                             ChroniclerProgress,
                                             chronicler_job)

from ..base import GrimoireLabTestCase


def do_something():
    """Function to run on a job"""

    logger = logging.getLogger(__name__)
    logger.info("This is a log message")

    return "Job executed successfully"


class TestGrimoireLabJob(GrimoireLabTestCase):
    """Unit tests for GrimoireLabJob class"""

    def test_create(self):
        """Tests whether the job creation is correct"""

        job = GrimoireLabJob.create(func=do_something,
                                    connection=self.conn)

        self.assertEqual(job.progress, None)
        self.assertEqual(job.log, [])

    def test_init(self):
        """Tests whether the job initialization is correct"""

        job = GrimoireLabJob(connection=self.conn)

        self.assertEqual(job.progress, None)
        self.assertEqual(job.log, [])

    def test_progress(self):
        """Tests the progress property"""

        job = GrimoireLabJob.create(func=do_something,
                                    connection=self.conn)
        job.progress = 50

        self.assertEqual(job.progress, 50)
        self.assertEqual(job.meta['progress'], 50)

    def test_log(self):
        """Tests the log property"""

        grimoire_job = GrimoireLabJob.create(
            func=do_something,
            connection=self.conn,
            loggers=[__name__]
        )

        logger = logging.getLogger(__name__)
        logger.addHandler(grimoire_job.job_logger)
        logger.setLevel(logging.INFO)

        logger.info("This is a log message")

        self.assertEqual(len(grimoire_job.log), 1)
        self.assertEqual(grimoire_job.log[0]['msg'], "This is a log message")

    def test_job(self):
        """Tests if the job is run and logs are generated"""

        job = GrimoireLabJob.create(func=do_something,
                                    connection=self.conn,
                                    loggers=[__name__])
        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue_job(job)

        self.assertEqual(job.result, "Job executed successfully")
        self.assertEqual(len(job.log), 1)
        self.assertEqual(job.log[0]['msg'], "This is a log message")

        # Check if log handler is removed after execution
        self.assertNotIn(job.job_logger,
                         logging.getLogger(__name__).handlers)


class TestJobLogHandler(GrimoireLabTestCase):
    """Unit tests for JobLogHandler class"""

    def test_init(self):
        """Tests whether the job handler initialization is correct"""

        job = rq.job.Job(connection=self.conn)
        meta_handler = JobLogHandler(job)

        self.assertEqual(meta_handler.job, job)
        self.assertListEqual(meta_handler.job.meta['log'], [])

    def test_emit(self):
        """Tests whether messages are logged correctly"""

        job = rq.job.Job(connection=self.conn)

        meta_handler = JobLogHandler(job)
        logger = logging.getLogger(__name__)
        logger.addHandler(meta_handler)
        logger.setLevel(logging.INFO)

        logger.error("This is an error message")
        logger.warning("This is a warning message")
        logger.info("This is an info message")

        # Check if the logs are saved in the job 'meta' field
        self.assertEqual(len(job.meta['log']), 3)
        self.assertEqual(sorted(list(job.meta['log'][0].keys())),
                         ['created', 'level', 'module', 'msg'])
        self.assertRegex(job.meta['log'][0]['msg'], 'error')
        self.assertRegex(job.meta['log'][1]['msg'], 'warning')
        self.assertRegex(job.meta['log'][2]['msg'], 'info')


class TestChroniclerJob(GrimoireLabTestCase):
    """Unit tests for chronicler_job function"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix='grimoirelab_core_')
        self.dir = os.path.dirname(os.path.realpath(__file__))
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.tmp_path)
        super().tearDown()

    def test_job(self):
        """Test if events are generated using the Git backend"""

        job_args = {
            'datasource_type': 'git',
            'datasource_category': 'commit',
            'events_queue': 'events',
            'job_args': {
                'uri': 'http://example.com/',
                'gitpath': os.path.join(self.dir, 'data/git_log.txt')
            }
        }

        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue(f=chronicler_job,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='chonicler-git',
                        **job_args)

        result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, 'git')
        self.assertEqual(result.category, 'commit')
        self.assertEqual(result.summary.last_uuid,
                         '1375b60d3c23ac9b81da92523e4144abc4489d4c')
        self.assertEqual(result.summary.max_updated_on,
                         datetime.datetime(2014, 2, 12, 6, 10, 39,
                                           tzinfo=datetime.timezone.utc))
        self.assertEqual(result.summary.last_updated_on,
                         datetime.datetime(2012, 8, 14, 17, 30, 13,
                                           tzinfo=datetime.timezone.utc))
        self.assertEqual(result.summary.total, 9)
        self.assertEqual(result.summary.max_offset,
                         'ce8e0b86a1e9877f42fe9453ede418519115f367')

        # Check generated events
        events = self.conn.lrange('events', 0, -1)
        events = [json.loads(e) for e in events]

        expected = [
            ('2d85a883e0ef63ebf7fa40e372aed44834092592', 'org.grimoirelab.events.git.merge'),
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
            ('9e5000b81d4d9554587df37f81bf64de10b23ec8', 'org.grimoirelab.events.git.file.added')
        ]

        for i, event in enumerate(events):
            self.assertEqual(event['id'], expected[i][0])
            self.assertEqual(event['type'], expected[i][1])
            self.assertEqual(event['source'], 'http://example.com/')

    def test_job_no_result(self):
        """Execute a job that will not produce any results"""

        job_args = {
            'datasource_type': 'git',
            'datasource_category': 'commit',
            'events_queue': 'events',
            'job_args': {
                'uri': 'http://example.com/',
                'gitpath': os.path.join(self.dir, 'data/git_log_empty.txt')
            }
        }

        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue(f=chronicler_job,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='chonicler-git',
                        **job_args)

        result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, 'git')
        self.assertEqual(result.category, 'commit')
        self.assertEqual(result.summary.last_uuid, None)
        self.assertEqual(result.summary.max_updated_on, None)
        self.assertEqual(result.summary.last_updated_on, None)
        self.assertEqual(result.summary.total, 0)
        self.assertEqual(result.summary.max_offset, None)

        # Check no events were generated
        commits = self.conn.lrange('events', 0, -1)
        commits = [pickle.loads(c) for c in commits]
        self.assertListEqual(commits, [])

    def test_backend_not_found(self):
        """Test if it fails when a backend is not found"""

        job_args = {
            'datasource_type': 'nobackend',
            'datasource_category': 'unknown',
            'events_queue': 'events',
            'job_args': {
                'uri': 'http://example.com/',
                'gitpath': os.path.join(self.dir, 'data/git_log_empty.txt')
            }
        }

        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue(f=chronicler_job,
                        result_ttl=100,
                        job_timeout=120,
                        job_id='chonicler-git',
                        **job_args)

        self.assertTrue(job.is_failed)


class TestChroniclerProgress(GrimoireLabTestCase):
    """Unit tests for ChroniclerProgress class"""

    def test_init(self):
        """Tests whether the ChroniclerProgress initialization is correct"""

        progress = ChroniclerProgress('1234567890', 'git', 'commit', None)

        self.assertEqual(progress.job_id, '1234567890')
        self.assertEqual(progress.backend, 'git')
        self.assertEqual(progress.category, 'commit')
        self.assertEqual(progress.summary, None)

    def test_to_dict(self):
        """Tests whether the ChroniclerProgress object is converted to a dict"""

        job_id = '1234567890'
        backend = 'git'
        category = 'commit'

        summary = perceval.backend.Summary()
        summary.fetched = 100
        summary.skipped = 10
        summary.last_uuid = 'abc123'
        summary.min_offset = '00000000'
        summary.max_offset = 'ffffffff'
        summary.last_offset = '12345678'
        summary.extras = {'key': 'value'}
        summary.min_updated_on = datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)
        summary.max_updated_on = datetime.datetime(2022, 1, 31, tzinfo=datetime.timezone.utc)
        summary.last_updated_on = datetime.datetime(2022, 1, 15, tzinfo=datetime.timezone.utc)

        progress = ChroniclerProgress(job_id, backend, category, summary)

        expected = {
            'job_id': job_id,
            'fetched': 100,
            'skipped': 10,
            'last_uuid': 'abc123',
            'min_offset': '00000000',
            'max_offset': 'ffffffff',
            'last_offset': '12345678',
            'extras': {'key': 'value'},
            'min_updated_on': datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc).timestamp(),
            'max_updated_on': datetime.datetime(2022, 1, 31, tzinfo=datetime.timezone.utc).timestamp(),
            'last_updated_on': datetime.datetime(2022, 1, 15, tzinfo=datetime.timezone.utc).timestamp()
        }

        d = progress.to_dict()
        self.assertEqual(d, expected)
