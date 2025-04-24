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

import os
import signal
import threading
import time

import structlog

from grimoirelab.core.consumers.consumer_pool import ConsumerPool
from grimoirelab.core.consumers.consumer import Consumer

from ..base import GrimoireLabTestCase


logger = structlog.get_logger(__name__)


class SampleConsumer(Consumer):
    def process_entries(self, entries, recovery=False):
        for entry in entries:
            logger.info(f"Processing entry: {entry.message_id}")
            self.ack_entries([entry.message_id])


class SampleConsumerPool(ConsumerPool):
    CONSUMER_CLASS = SampleConsumer


class TestConsumerPool(GrimoireLabTestCase):
    """Unit tests for ConsumerPool class"""

    def test_pool_initialization(self):
        """Test whether the pool is initialized correctly"""

        pool = SampleConsumerPool(
            connection=self.conn,
            stream_name="test_stream",
            group_name="test_group",
            num_consumers=10,
            stream_block_timeout=1000,
            verbose=True,
        )

        self.assertEqual(pool.stream_name, "test_stream")
        self.assertEqual(pool.group_name, "test_group")
        self.assertEqual(pool.num_consumers, 10)
        self.assertEqual(pool.stream_block_timeout, 1000)
        self.assertTrue(pool.verbose)
        self.assertEqual(pool.status, ConsumerPool.Status.IDLE)

    def test_clean_up_consumers(self):
        """Test whether the consumers are cleaned up correctly"""

        pool = SampleConsumerPool(
            connection=self.conn,
            stream_name="test_stream",
            group_name="test_group",
            num_consumers=10,
            stream_block_timeout=1000,
            verbose=True,
        )
        pool.start_consumers(burst=False)

        pool.cleanup_consumers()
        self.assertEqual(len(pool._consumers), 10)

        consumer_name = list(pool._consumers.keys())[0]
        pool._consumers[consumer_name].process.kill()
        time.sleep(0.5)

        pool.cleanup_consumers()
        self.assertEqual(len(pool._consumers), 9)

        pool.force_stop()
        pool.cleanup_consumers()
        self.assertEqual(pool.status, ConsumerPool.Status.STOPPED)
        self.assertEqual(len(pool._consumers), 0)

    def test_restore_consumers(self):
        """Test whether consumers are restored correctly"""

        pool = SampleConsumerPool(
            connection=self.conn,
            stream_name="test_stream",
            group_name="test_group",
            num_consumers=10,
            stream_block_timeout=1000,
            verbose=True,
        )
        pool.start_consumers(burst=False)

        pool.cleanup_consumers()
        self.assertEqual(len(pool._consumers), 10)

        consumer_name = list(pool._consumers.keys())[0]
        pool._consumers[consumer_name].process.kill()
        time.sleep(0.5)

        pool.cleanup_consumers()
        self.assertEqual(len(pool._consumers), 9)

        pool.restore_consumers()
        self.assertEqual(len(pool._consumers), 10)

        pool.force_stop()

    def test_stop_signal(self):
        """Test whether the pool stops correctly when a signal is received"""

        def send_sigint_signal(pid: int, after: int):
            time.sleep(after)
            os.kill(pid, signal.SIGTERM)

        pool = SampleConsumerPool(
            connection=self.conn,
            stream_name="test_stream",
            group_name="test_group",
            num_consumers=10,
            stream_block_timeout=1000,
            verbose=True,
        )

        threading.Thread(target=send_sigint_signal, args=(os.getpid(), 0.5)).start()

        pool.start(burst=False)

        self.assertEqual(pool.status, ConsumerPool.Status.STOPPED)

        # Ensure that the consumers are stopped
        pool.force_stop()
