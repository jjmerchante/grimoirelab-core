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
import signal
import time

from collections import namedtuple
from enum import Enum
from multiprocessing import Process, Event
from uuid import uuid4

import django_rq
import redis

from .consumer import Consumer


ConsumerData = namedtuple("ConsumerData", ["name", "pid", "process"])


class ConsumerPool:
    """Base class to create a pool of consumers.

    ConsumerPool allows running multiple consumers in parallel,
    making it useful when multiple consumers share the same
    configuration.

    When started, the ConsumerPool spawns multiple processes,
    each running a specified Consumer class. It continuously
    monitors these processes and respawns them if they stop
    unexpectedly.

    The ConsumerPool can be stopped by sending a SIGINT or SIGTERM
    signal to the process. This will stop all the consumers gracefully
    and exit the process. If the signal is sent again, the ConsumerPool
    will force stop all the consumers and exit the process.

    The ConsumerPool must be subclassed to implement custom behavior
    for the consumers. The subclass must define the CONSUMER_CLASS
    attribute, which must be a subclass of Consumer and the
    extra_consumer_kwargs property, which must return a dictionary
    with extra kwargs to pass to the Consumer.

    :param stream_name: Name of the stream to consume.
    :param group_name: Name of the consumer group.
    :param num_consumers: Number of consumers to run in parallel.
    :param stream_block_timeout: Timeout for blocking read from the stream.
    :param verbose: If True, enable verbose logging.
    """

    CONSUMER_CLASS: type[Consumer]

    Status = Enum("Status", "IDLE STARTED STOPPED")

    def __init__(
        self,
        stream_name: str,
        group_name: str,
        num_consumers: int = 10,
        stream_block_timeout: int = 60000,
        verbose: bool = False,
    ):
        self.stream_name = stream_name
        self.group_name = group_name
        self.num_consumers = num_consumers
        self.log_level = logging.DEBUG if verbose else logging.INFO
        self.logger = self._create_logger()
        self.status = self.Status.IDLE
        self.stream_block_timeout = stream_block_timeout
        self.verbose = verbose
        self._consumers = {}
        self.connection = django_rq.get_connection()
        self._stop_event = Event()

    def start(self, burst: bool = False):
        """Start the consumer pool.

        This method will run indefinitely creating and monitoring
        the consumers in the pool. It will respawn consumers if they
        stop unexpectedly.

        If burst is True, the pool will not respawn consumers, and
        it will exit when all the consumers finish processing the
        stream.

        :param burst: If True, the pool will not respawn consumers
        """
        self.logger.info(f"Starting consumer pool with {self.num_consumers} consumers.")

        self.status = self.Status.STARTED
        self._create_consumer_group()
        self.start_consumers(burst=burst)
        self._setup_signal_handlers()

        while True:
            self.cleanup_consumers()
            if not burst and self.status == self.Status.STARTED:
                self.restore_consumers()

            running = len(self._consumers)
            if running == 0:
                self.logger.info("All consumers stopped, exiting...")
                break
            elif self.status == self.Status.STOPPED:
                self.logger.info(f"Waiting for {running} consumers to stop...")
                time.sleep(0.5)

            time.sleep(0.5)

    @property
    def extra_consumer_kwargs(self):
        """Extra kwargs to pass to the consumer, this must be implemented in subclasses."""

        return {}

    def start_consumers(self, burst: bool = False):
        """Create the consumers in the pool."""

        for _ in range(self.num_consumers):
            self.create_consumer(burst=burst)

    def create_consumer(self, burst: bool = False):
        """Create a consumer and start it."""

        name = f"{self.CONSUMER_CLASS.__name__}:{uuid4().hex}"
        kwargs = {
            "consumer_class": self.CONSUMER_CLASS,
            "stream_name": self.stream_name,
            "consumer_group": self.group_name,
            "consumer_name": name,
            "stream_block_timeout": self.stream_block_timeout,
            "logging_level": self.log_level,
            "stop_event": self._stop_event,
        }
        kwargs.update(self.extra_consumer_kwargs)

        process = Process(target=_run_consumer, name=name, kwargs=kwargs)
        process.start()

        data = ConsumerData(name=name, pid=process.pid, process=process)
        self._consumers[name] = data

        return data

    def _create_consumer_group(self):
        """Create the consumer group if it does not exist."""

        try:
            self.connection.xgroup_create(self.stream_name, self.group_name, id="0", mkstream=True)
        except redis.exceptions.ResponseError as e:
            if str(e) != "BUSYGROUP Consumer Group name already exists":
                raise

    def restore_consumers(self, burst: bool = False):
        """Respawn consumers if needed."""

        running = len(self._consumers)
        respawn = self.num_consumers - running
        if respawn > 0:
            self.logger.warning(f"Respawning {respawn} consumers.")
            for _ in range(respawn):
                self.create_consumer(burst=burst)

    def cleanup_consumers(self):
        """Remove dead consumers from the pool."""

        consumers = list(self._consumers.items())

        for name, consumer in consumers:
            consumer.process.join(timeout=0.1)
            if not consumer.process.is_alive():
                self._consumers.pop(name)

    def _create_logger(self):
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(self.log_level)
        return logger

    def stop(self):
        """Stop the consumer pool gracefully."""

        self.logger.info("Stopping consumer pool...")
        self.status = self.Status.STOPPED

        if self._stop_event.is_set():
            self.force_stop()
        else:
            self._stop_event.set()

    def force_stop(self):
        """Kill all the consumers."""

        self.logger.info("Forcing stop...")
        self.status = self.Status.STOPPED

        for consumer in self._consumers.values():
            try:
                consumer.process.kill()
            except OSError as e:
                pass

    def _request_stop(self, signum, frame):
        """Callback to request the consumer to stop using signals."""

        self.stop()

    def _setup_signal_handlers(self):
        """Set up handlers for termination signals."""

        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, self._request_stop)


def _run_consumer(
    consumer_class: type[Consumer],
    *args,
    **kwargs,
):
    # Ignore SIGINT signal to avoid being killed when pressing Ctrl+C
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    connection = django_rq.get_connection()
    try:
        consumer = consumer_class(connection=connection, *args, **kwargs)
        consumer.start(burst=kwargs.get("burst", False))
    except Exception as e:
        logging.error(f"Consumer {consumer_class.__name__} failed: {e}")
