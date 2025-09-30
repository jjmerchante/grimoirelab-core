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
import os
import pickle
import shutil
import tempfile

import rq
import perceval.backend

from grimoirelab.core.scheduler.jobs import GrimoireLabJob
from grimoirelab.core.scheduler.tasks.chronicler import ChroniclerProgress, chronicler_job

from ..base import GrimoireLabTestCase


class TestChroniclerJob(GrimoireLabTestCase):
    """Unit tests for chronicler_job function"""

    def setUp(self):
        self.tmp_path = tempfile.mkdtemp(prefix="grimoirelab_core_")
        self.dir = os.path.dirname(os.path.realpath(__file__))
        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.tmp_path)
        super().tearDown()

    def test_job(self):
        """Test if events are generated using the Git backend"""

        job_args = {
            "datasource_type": "git",
            "datasource_category": "commit",
            "events_stream": "events",
            "stream_max_length": 500,
            "job_args": {
                "uri": "http://example.com/",
                "gitpath": os.path.join(self.dir, "data/git_log.txt"),
            },
        }

        q = rq.Queue("test-queue", job_class=GrimoireLabJob, connection=self.conn, is_async=False)
        job = q.enqueue(
            f=chronicler_job, result_ttl=100, job_timeout=120, job_id="chonicler-git", **job_args
        )

        result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, "git")
        self.assertEqual(result.category, "commit")
        self.assertEqual(result.summary.last_uuid, "1375b60d3c23ac9b81da92523e4144abc4489d4c")
        self.assertEqual(
            result.summary.max_updated_on,
            datetime.datetime(2014, 2, 12, 6, 10, 39, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(
            result.summary.last_updated_on,
            datetime.datetime(2012, 8, 14, 17, 30, 13, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(result.summary.total, 9)
        self.assertEqual(result.summary.max_offset, "ce8e0b86a1e9877f42fe9453ede418519115f367")

        # Check generated events
        events = self.conn.xread({"events": b"0-0"}, count=None, block=0)
        events = [json.loads(e[1][b"data"]) for e in events[0][1]]

        expected = [
            ("2d85a883e0ef63ebf7fa40e372aed44834092592", "org.grimoirelab.events.git.merge"),
            (
                "048d4869b8051acb0196d207c032210a980a7da4",
                "org.grimoirelab.events.git.file.modified",
            ),
            (
                "08db95eaf93968579a681701f347d94455ba6574",
                "org.grimoirelab.events.git.file.replaced",
            ),
            (
                "897e8e648ca4f08578ac07436b10a06f8d60e4a5",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "8b3a99166f4a8022fbaf8b05fd4b72938a487332",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("d7226f6c921128190f644fb659c61b3ef6360b91", "org.grimoirelab.events.git.commit"),
            (
                "c0fd3bbdcbebf0232b010166d132cafecf5943f8",
                "org.grimoirelab.events.git.file.modified",
            ),
            (
                "aa7d368678d181a1833da26e4bfd9c735e7bc211",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "a114769c4588f4be26ed7ae30607a98353061751",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("16c99217dc3185c760cc64985271e2d5b2fbbe39", "org.grimoirelab.events.git.commit"),
            (
                "d34572db2652b86d14e887aa6a469d32a1c1c705",
                "org.grimoirelab.events.git.file.replaced",
            ),
            (
                "19efa5c21da45c94632a5681ce03fd152afa6c29",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "244824994e963ebfbe507ff11780c1878749b0ac",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("81df8221af2e63715ad3ff1f5fd41f9a1f2723e4", "org.grimoirelab.events.git.commit"),
            ("8c5c6442870f9b0b7d36246c8b04d544adbc5c1c", "org.grimoirelab.events.git.file.added"),
            (
                "c10d9226732e9f718f005c9af92bd63a23a203bb",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "7d199934b094511a3c033ca3ffaff3caf8aa62bb",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("504a6e9e5ba7dad1b275489b775d45cc8d77a790", "org.grimoirelab.events.git.commit"),
            ("bb2012e4a54c60c7d91d628b6cd08bbca6a65ee8", "org.grimoirelab.events.git.file.added"),
            (
                "e76fb1acc44ae49d685ce570941b0845317b95e0",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "b956cebb882d278060dc52bbb6a5f10480185363",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("e8460b1df2147e217e12cfa7404191af589f62cb", "org.grimoirelab.events.git.commit"),
            ("93ea3e9c6b1f77f00894b1c361d7ee16a0490299", "org.grimoirelab.events.git.file.deleted"),
            (
                "52e52ed98daa1665af78f8fda9da1915ddb89649",
                "org.grimoirelab.events.git.file.replaced",
            ),
            (
                "c2c2b778fa4ae7f7bce570b29b506c4c291a9318",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "e19fd010dc3bbd31673c2f7075eab4c9588928d2",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("e5ff829d3f1bacf6a6d3e36cd996a1308351f9a5", "org.grimoirelab.events.git.commit"),
            ("5ee17ed5caf8cf3fc33e50ab3b46e2fe66d5cd71", "org.grimoirelab.events.git.file.added"),
            (
                "d5ee352944d5f7b015ffb5891cec94547e3015f4",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "ebde018e3d492b84315b2296dc8501009ba750d3",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("caf05717b6c53143bd29a2140eb9c043aaefb255", "org.grimoirelab.events.git.commit"),
            (
                "7bbe861347f594692c9bb72c2bf0c95a8b252f69",
                "org.grimoirelab.events.git.file.replaced",
            ),
            (
                "cfe5c30ef3711cbe1c10cd949d24f1f6062d3c8c",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "5982a89b69d4c177729638a03fd8642029a20c1e",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
            ("1375b60d3c23ac9b81da92523e4144abc4489d4c", "org.grimoirelab.events.git.commit"),
            ("48335db7cb8e6db4367ac2543d0c92deb2a655ce", "org.grimoirelab.events.git.file.added"),
            ("fa4a64cb04f8c9fef6c0143d874e90e7c5f4f3fc", "org.grimoirelab.events.git.file.added"),
            ("9e5000b81d4d9554587df37f81bf64de10b23ec8", "org.grimoirelab.events.git.file.added"),
            (
                "0ca37c330d0b4b75171b15123299a07fcaf61070",
                "org.grimoirelab.events.git.commit.authored_by",
            ),
            (
                "4c2eb49bbfee27b05cbf0c8f4e83070a88b9aeeb",
                "org.grimoirelab.events.git.commit.committed_by",
            ),
        ]

        for i, event in enumerate(events):
            self.assertEqual(event["id"], expected[i][0])
            self.assertEqual(event["type"], expected[i][1])
            self.assertEqual(event["source"], "http://example.com/")

    def test_job_no_result(self):
        """Execute a job that will not produce any results"""

        job_args = {
            "datasource_type": "git",
            "datasource_category": "commit",
            "events_stream": "events",
            "stream_max_length": 500,
            "job_args": {
                "uri": "http://example.com/",
                "gitpath": os.path.join(self.dir, "data/git_log_empty.txt"),
            },
        }

        q = rq.Queue("test-queue", job_class=GrimoireLabJob, connection=self.conn, is_async=False)
        job = q.enqueue(
            f=chronicler_job, result_ttl=100, job_timeout=120, job_id="chonicler-git", **job_args
        )

        result = job.return_value()

        # Check job result
        self.assertEqual(result.job_id, job.get_id())
        self.assertEqual(result.backend, "git")
        self.assertEqual(result.category, "commit")
        self.assertEqual(result.summary.last_uuid, None)
        self.assertEqual(result.summary.max_updated_on, None)
        self.assertEqual(result.summary.last_updated_on, None)
        self.assertEqual(result.summary.total, 0)
        self.assertEqual(result.summary.max_offset, None)

        # Check no events were generated
        commits = self.conn.lrange("events", 0, -1)
        commits = [pickle.loads(c) for c in commits]
        self.assertListEqual(commits, [])

    def test_backend_not_found(self):
        """Test if it fails when a backend is not found"""

        job_args = {
            "datasource_type": "nobackend",
            "datasource_category": "unknown",
            "events_stream": "events",
            "stream_max_length": 500,
            "job_args": {
                "uri": "http://example.com/",
                "gitpath": os.path.join(self.dir, "data/git_log_empty.txt"),
            },
        }

        q = rq.Queue("test-queue", job_class=GrimoireLabJob, connection=self.conn, is_async=False)
        job = q.enqueue(
            f=chronicler_job, result_ttl=100, job_timeout=120, job_id="chonicler-git", **job_args
        )

        self.assertTrue(job.is_failed)


class TestChroniclerProgress(GrimoireLabTestCase):
    """Unit tests for ChroniclerProgress class"""

    def test_init(self):
        """Tests whether the ChroniclerProgress initialization is correct"""

        progress = ChroniclerProgress("1234567890", "git", "commit", None)

        self.assertEqual(progress.job_id, "1234567890")
        self.assertEqual(progress.backend, "git")
        self.assertEqual(progress.category, "commit")
        self.assertEqual(progress.summary, None)

    def test_from_dict(self):
        """Tests whether the ChroniclerProgress object is created from a dict"""

        job_id = "1234567890"
        backend = "git"
        category = "commit"

        data = {
            "job_id": job_id,
            "backend": backend,
            "category": category,
            "summary": {
                "fetched": 10,
                "skipped": 2,
                "min_updated_on": "2021-01-01 00:00:0+00:00",
                "max_updated_on": "2021-01-02 00:00:0+00:00",
                "last_updated_on": "2021-01-03 00:00:0+00:00",
                "last_uuid": "abc123",
                "min_offset": 1,
                "max_offset": 10,
                "last_offset": 5,
                "extras": {"extra_key": "extra_value"},
            },
        }

        progress = ChroniclerProgress.from_dict(data)

        self.assertEqual(progress.job_id, job_id)
        self.assertEqual(progress.backend, backend)
        self.assertEqual(progress.category, category)
        self.assertEqual(progress.summary.fetched, 10)
        self.assertEqual(progress.summary.skipped, 2)
        self.assertEqual(
            progress.summary.min_updated_on,
            datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(
            progress.summary.max_updated_on,
            datetime.datetime(2021, 1, 2, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(
            progress.summary.last_updated_on,
            datetime.datetime(2021, 1, 3, tzinfo=datetime.timezone.utc),
        )
        self.assertEqual(progress.summary.last_uuid, "abc123")
        self.assertEqual(progress.summary.min_offset, 1)
        self.assertEqual(progress.summary.max_offset, 10)
        self.assertEqual(progress.summary.last_offset, 5)
        self.assertEqual(progress.summary.extras, {"extra_key": "extra_value"})

    def test_to_dict(self):
        """Tests whether the ChroniclerProgress object is converted to a dict"""

        job_id = "12345678"
        backend = "git"
        category = "commit"

        summary = perceval.backend.Summary()
        summary.fetched = 100
        summary.skipped = 10
        summary.last_uuid = "abc123"
        summary.min_offset = 10
        summary.max_offset = 80
        summary.last_offset = 75
        summary.extras = {"key": "value"}
        summary.min_updated_on = datetime.datetime(2022, 1, 1, tzinfo=datetime.timezone.utc)
        summary.max_updated_on = datetime.datetime(2022, 1, 31, tzinfo=datetime.timezone.utc)
        summary.last_updated_on = datetime.datetime(2022, 1, 15, tzinfo=datetime.timezone.utc)

        progress = ChroniclerProgress(job_id, backend, category, summary)

        expected = {
            "job_id": job_id,
            "backend": backend,
            "category": category,
            "summary": {
                "fetched": 100,
                "skipped": 10,
                "last_uuid": "abc123",
                "min_offset": 10,
                "max_offset": 80,
                "last_offset": 75,
                "extras": {"key": "value"},
                "min_updated_on": datetime.datetime(
                    2022, 1, 1, tzinfo=datetime.timezone.utc
                ).timestamp(),
                "max_updated_on": datetime.datetime(
                    2022, 1, 31, tzinfo=datetime.timezone.utc
                ).timestamp(),
                "last_updated_on": datetime.datetime(
                    2022, 1, 15, tzinfo=datetime.timezone.utc
                ).timestamp(),
            },
        }

        d = progress.to_dict()
        self.assertEqual(d, expected)
