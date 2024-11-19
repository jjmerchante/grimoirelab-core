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

import logging

import rq

from grimoirelab.core.scheduler.jobs import (
    GrimoireLabJob,
    JobLogHandler
)

from ..base import GrimoireLabTestCase


def do_something():
    """Function to run on a job"""

    logger = logging.getLogger(__name__)
    logger.info("This is a log message")

    return "Job executed successfully"


def do_something_and_fail():
    """Function to run on a job"""

    logger = logging.getLogger(__name__)
    logger.info("This is a log message")

    raise Exception("Unexpected error")


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

        grimoire_job.add_log({'msg': "This is a log message"})

        self.assertEqual(len(grimoire_job.log), 1)
        self.assertEqual(grimoire_job.log[0]['msg'], "This is a log message")

    def test_job(self):
        """Tests if the job is run and logs are generated"""

        job = GrimoireLabJob.create(func=do_something,
                                    connection=self.conn,
                                    loggers=[__name__, 'grimoirelab.core.scheduler.jobs'])
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
        self.assertNotIn(job._job_logger,
                         logging.getLogger(__name__).handlers)

    def test_job_capture_exception(self):
        """Checks if the job captures exceptions and logs them"""

        job = GrimoireLabJob.create(func=do_something_and_fail,
                                    connection=self.conn,
                                    loggers=[__name__, 'grimoirelab.core.scheduler.jobs'])
        q = rq.Queue(
            'test-queue',
            job_class=GrimoireLabJob,
            connection=self.conn,
            is_async=False
        )
        job = q.enqueue_job(job)

        self.assertEqual(job.result, None)
        self.assertEqual(len(job.log), 2)
        self.assertEqual(job.log[0]['msg'], "This is a log message")
        self.assertRegex(job.log[1]['msg'], "Traceback")


class TestJobLogHandler(GrimoireLabTestCase):
    """Unit tests for JobLogHandler class"""

    def test_init(self):
        """Tests whether the job handler initialization is correct"""

        job = GrimoireLabJob(connection=self.conn)
        meta_handler = JobLogHandler(job)

        self.assertEqual(meta_handler.job, job)
        self.assertListEqual(meta_handler.job.log, [])

    def test_emit(self):
        """Tests whether messages are logged correctly"""

        job = GrimoireLabJob(connection=self.conn)

        meta_handler = JobLogHandler(job)
        logger = logging.getLogger(__name__)
        logger.addHandler(meta_handler)
        logger.setLevel(logging.INFO)

        logger.error("This is an error message")
        logger.warning("This is a warning message")
        logger.info("This is an info message")

        # Check if the logs are saved in the job 'meta' field
        self.assertEqual(len(job.log), 3)
        self.assertEqual(sorted(list(job.log[0].keys())),
                         ['created', 'level', 'module', 'msg'])
        self.assertRegex(job.log[0]['msg'], 'error')
        self.assertRegex(job.log[1]['msg'], 'warning')
        self.assertRegex(job.log[2]['msg'], 'info')
