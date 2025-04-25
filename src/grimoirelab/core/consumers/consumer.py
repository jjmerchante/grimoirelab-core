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

from __future__ import annotations

import json
import logging
import time
import typing

from collections import namedtuple
from multiprocessing import Event as ProcessEvent

import redis
import structlog

if typing.TYPE_CHECKING:
    from typing import Iterable
    from multiprocessing.synchronize import Event as ProcessEventType
    from threading import Event as ThreadEventType


ENTRIES_READ_COUNT = 10
RECOVER_IDLE_TIME = 300000  # 5 minutes (in ms)
STREAM_BLOCK_TIMEOUT = 60000  # 1 minute (in ms)

EXPONENTIAL_BACKOFF_FACTOR = 2
MAX_CONNECTION_WAIT_TIME = 60


Entry = namedtuple("Entry", ["message_id", "event"])


class Consumer:
    """Consumer base class to process events from a stream.

    :param connection: Redis connection object.
    :param stream_name: Name of the stream to consume.
    :param consumer_group: Name of the consumer group.
    :param consumer_name: Name of the consumer.
    :param stream_block_timeout: Timeout for blocking read from the stream.
    :param logging_level: Logging level for the consumer.
    """

    def __init__(
        self,
        connection: redis.Redis,
        stream_name: str,
        consumer_group: str,
        consumer_name: str,
        stream_block_timeout: int = STREAM_BLOCK_TIMEOUT,
        logging_level: str | int = logging.INFO,
        stop_event: ProcessEventType | ThreadEventType = None,
    ):
        self.connection = connection
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.stream_block_timeout = stream_block_timeout
        self.logging_level = logging_level
        self.logger = self._create_logger()
        self._stop_event = stop_event or ProcessEvent()

    def start(self, burst: bool = False):
        """Process events from the stream.

        This method first tries to recover entries from the stream that are
        not yet processed by the consumer group in the last RECOVER_IDLE_TIME.

        Once the entries are recovered, it starts to collect new entries
        from the stream blocking for 'stream_block_timeout' if there aren't
        new entries.
        """
        self.logger.info(
            f"Starting consumer '{self.consumer_name}' for '{self.stream_name}:{self.consumer_group}'"
        )

        self._create_consumer_group()

        connection_wait_time = 1
        while True:
            try:
                recovered_entries = self.recover_stream_entries()
                self.process_entries(recovered_entries, recovery=True)

                new_entries = self.fetch_new_entries()
                self.process_entries(new_entries)
            except redis.exceptions.ConnectionError as conn_err:
                self.logger.error(
                    f"Could not connect to Redis instance: {conn_err} Retrying in {connection_wait_time} seconds..."
                )
                time.sleep(connection_wait_time)
                connection_wait_time *= EXPONENTIAL_BACKOFF_FACTOR
                connection_wait_time = min(connection_wait_time, MAX_CONNECTION_WAIT_TIME)
            else:
                connection_wait_time = 1

            if burst or self._stop_event.is_set():
                break

        self.logger.info(f"Consumer '{self.consumer_name}' stopped.")

    def fetch_new_entries(self) -> Iterable[Entry]:
        """Fetch new entries from the stream.

        This method fetches new entries from the stream and yields them
        to the caller.
        If there are no new entries at the start of the call, it will
        block for 'stream_block_timeout' milliseconds.
        When new entries are available, it will yield them to the caller
        and continue to fetch new entries until there are no more entries
        available.
        """
        self.logger.debug(f"Reading new events from '{self.stream_name}:{self.consumer_group}'")

        block_time = self.stream_block_timeout

        while True:
            try:
                response = self.connection.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_name: ">"},
                    count=ENTRIES_READ_COUNT,
                    block=block_time,
                )

                # The response contains an array with the following contents
                # 1) 1) "stream_name"
                #    2) 1) 1) "1-0" (array of arrays containing the key and the entries)
                #          2) 1) "field"
                #             2) "value"
                if response:
                    messages = response[0][1]
                    for message in messages:
                        message_id = message[0]
                        message_data = message[1][b"data"]

                        yield Entry(message_id=message_id, event=json.loads(message_data))

                    # Avoid excessive blocking when no new entries are available
                    block_time = 1000

                else:
                    self.logger.debug(
                        f"No new messages for '{self.stream_name}:{self.consumer_group}'."
                    )
                    break

                if self._stop_event.is_set():
                    break
            except Exception as e:
                self.logger.error(f"Error consuming messages: {e}")
                raise e

    def recover_stream_entries(self, recover_idle_time: int = RECOVER_IDLE_TIME) -> Iterable[Entry]:
        """Transfers ownership of pending entries idle for 'recover_idle_time'."""

        self.logger.debug(
            "recovering events", stream=self.stream_name, consumer_group=self.consumer_group
        )

        while True:
            response = self.connection.xautoclaim(
                name=self.stream_name,
                groupname=self.consumer_group,
                consumername=self.consumer_name,
                min_idle_time=recover_idle_time,
                count=10,
            )
            # The response contains an array with the following contents
            # 1) "0-0" (stream ID to be used as the start argument for the next call)
            # 2) 1) 1) "1609338752495-0" (successfully claimed messages)
            #       2) 1) "field"
            #          2) "value"
            # 3) (empty array) (message IDs that no longer exist in the stream)
            messages = response[1]
            for message in messages:
                message_id = message[0]
                message_data = message[1][b"data"]

                yield Entry(message_id=message_id, event=json.loads(message_data))

            if not messages:
                break

            if self._stop_event.is_set():
                break

        self.logger.debug(
            "events recovered", stream=self.stream_name, consumer_group=self.consumer_group
        )

    def process_entries(self, entries: Iterable[Entry], recovery: bool = False):
        """Process entries (implement this method in subclasses).

        This method is responsible for processing the entries and acknowledging
        them once they are processed calling self.ack_entries().
        If the recovery parameter is set, it means that the entries are being
        recovered and is the second time they are being processed.
        """
        raise NotImplementedError

    def ack_entries(self, message_ids: list):
        """Acknowledge a list of message IDs."""

        pipeline = self.connection.pipeline()

        for message_id in message_ids:
            pipeline.xack(self.stream_name, self.consumer_group, message_id)

        pipeline.execute()

    def stop(self):
        """Stop the consumer gracefully."""

        self._stop_event.set()
        self.logger.info("consumer stopped", consumer=self.consumer_name)

    def _create_logger(self):
        logger = structlog.get_logger(self.__class__.__name__)
        logger.setLevel(self.logging_level)
        return logger

    def _create_consumer_group(self):
        """Create the consumer group if it does not exist."""

        try:
            self.connection.xgroup_create(
                self.stream_name, self.consumer_group, id="0", mkstream=True
            )
        except redis.exceptions.ResponseError as e:
            if str(e) != "BUSYGROUP Consumer Group name already exists":
                raise
