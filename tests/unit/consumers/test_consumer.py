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
import multiprocessing
import time

from unittest.mock import MagicMock, patch

import redis

from grimoirelab.core.consumers.consumer import Consumer, Entry

from ..base import GrimoireLabTestCase
from ...utils import RedisStream


class SampleConsumer(Consumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.entries = []

    def process_entries(self, entries, recovery=False):
        for entry in entries:
            logging.info(f"Processing entry: {entry.message_id}")
            self.entries.append(entry)
            self.ack_entries([entry.message_id])


class TestConsumer(GrimoireLabTestCase):
    """Unit tests for Consumer class"""

    def test_consumer_initialization(self):
        """Test whether the consumer is initialized correctly"""

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )

        self.assertEqual(consumer.stream_name, "test_stream")
        self.assertEqual(consumer.consumer_group, "test_group")
        self.assertEqual(consumer.consumer_name, "test_consumer")
        self.assertEqual(consumer.stream_block_timeout, 1000)
        self.assertEqual(consumer.logging_level, "DEBUG")

    def test_fetch_new_entries(self):
        """Test whether the consumer fetches entries from the stream"""

        expected_entries = [
            Entry(message_id="1-0", event={"key": "value_1"}),
            Entry(message_id="2-0", event={"key": "value_2"}),
            Entry(message_id="3-0", event={"key": "value_3"}),
        ]

        stream = RedisStream(self.conn, "test_stream")
        stream.create_group("test_group")
        for entry in expected_entries:
            stream.add_entry(event=entry.event, message_id=entry.message_id)

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        entries = list(consumer.fetch_new_entries())

        self.assertEqual(len(entries), len(expected_entries))

        for entry, expected_entry in zip(entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

    def test_recover_entries(self):
        """Test whether the consumer recovers entries from the stream"""

        expected_entries = [
            Entry(message_id="1-0", event={"key": "value_1"}),
            Entry(message_id="2-0", event={"key": "value_2"}),
            Entry(message_id="3-0", event={"key": "value_3"}),
        ]

        stream = RedisStream(self.conn, "test_stream")
        stream.create_group("test_group")
        for entry in expected_entries:
            stream.add_entry(event=entry.event, message_id=entry.message_id)

        # Read the entries to claim them
        stream.read_group("test_group", "test_consumer", 3)

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        # No entries should be available
        entries = list(consumer.fetch_new_entries())
        self.assertEqual(len(entries), 0)

        entries = list(consumer.recover_stream_entries())
        self.assertEqual(len(entries), 0)

        # Change min_idle_time to 2s to recover the entries
        time.sleep(0.1)
        entries = list(consumer.recover_stream_entries(recover_idle_time=100))

        self.assertEqual(len(entries), len(expected_entries))
        for entry, expected_entry in zip(entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

    def test_ack_entries(self):
        """Test whether the consumer acknowledges entries"""

        stream = RedisStream(self.conn, "test_stream")
        stream.create_group("test_group")
        stream.add_entry(event={"key": "value_1"}, message_id="1-0")
        stream.add_entry(event={"key": "value_2"}, message_id="2-0")

        consumer = Consumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        entries = list(consumer.fetch_new_entries())
        self.assertEqual(len(entries), 2)

        pending = self.conn.xpending("test_stream", "test_group")
        self.assertEqual(pending["pending"], 2)

        ids = [entry.message_id for entry in entries]
        consumer.ack_entries(ids)

        # Entries are acknowledged
        pending = self.conn.xpending("test_stream", "test_group")
        self.assertEqual(pending["pending"], 0)

    def test_stop_consumer(self):
        """Test whether the consumer stops correctly"""

        stop_event = multiprocessing.Event()

        def start_consumer():
            consumer = SampleConsumer(
                connection=self.conn,
                stream_name="test_stream",
                consumer_group="test_group",
                consumer_name="test_consumer",
                stream_block_timeout=500,
                logging_level="DEBUG",
                stop_event=stop_event,
            )
            consumer.start()

        consumer_process = multiprocessing.Process(target=start_consumer)
        consumer_process.start()

        stop_event.set()

        consumer_process.join(2)

        self.assertFalse(consumer_process.is_alive())

    def test_different_consumer_groups(self):
        """Test whether different consumer groups fetches the same entries"""

        expected_entries = [
            Entry(message_id="1-0", event={"key": "value_1"}),
            Entry(message_id="2-0", event={"key": "value_2"}),
            Entry(message_id="3-0", event={"key": "value_3"}),
        ]

        stream = RedisStream(self.conn, "test_stream")
        for entry in expected_entries:
            stream.add_entry(event=entry.event, message_id=entry.message_id)

        # First consumer from group_1
        consumer_1 = SampleConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="group_1",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        consumer_1.start(burst=True)

        self.assertEqual(len(consumer_1.entries), len(expected_entries))

        for entry, expected_entry in zip(consumer_1.entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

        # Second consumer from group_2
        consumer_2 = SampleConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="group_2",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )
        consumer_2.start(burst=True)

        self.assertEqual(len(consumer_2.entries), len(expected_entries))

        for entry, expected_entry in zip(consumer_2.entries, expected_entries):
            self.assertEqual(entry.message_id.decode(), expected_entry.message_id)
            self.assertDictEqual(entry.event, expected_entry.event)

    def test_consumer_exponential_backoff(self):
        """Test whether the consumer implements exponential backoff on Redis connection errors"""

        # Create a mock consumer instance
        consumer = SampleConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level="DEBUG",
        )

        # Setup the mock for redis client to raise ConnectionError
        consumer.recover_stream_entries = MagicMock(
            side_effect=[
                redis.exceptions.ConnectionError("fail 1"),
                redis.exceptions.ConnectionError("fail 2"),
                redis.exceptions.ConnectionError("fail 3"),
                [],
            ]
        )  # Succeeds on 4th call

        consumer.fetch_new_entries = MagicMock(return_value=[])
        consumer.process_entries = MagicMock()
        consumer.logger = MagicMock()

        # Mock time.sleep to avoid real waiting
        with patch("time.sleep") as sleep_mock:
            try:
                consumer.start(burst=False)
            except StopIteration:
                # the recover_stream_entries mock will eventually fail
                pass

            # Check that sleep was called with exponential backoff times
            sleep_mock.assert_any_call(1)
            sleep_mock.assert_any_call(2)
            sleep_mock.assert_any_call(4)

            # Check that the logger recorded the connection errors
            consumer.logger.error.assert_any_call(
                "Could not connect to Redis instance: fail 1 Retrying in 1 seconds..."
            )
            consumer.logger.error.assert_any_call(
                "Could not connect to Redis instance: fail 2 Retrying in 2 seconds..."
            )
            consumer.logger.error.assert_any_call(
                "Could not connect to Redis instance: fail 3 Retrying in 4 seconds..."
            )
