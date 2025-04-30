# -*- coding: utf-8 -*-
#
# Copyright (C) GrimoireLab Developers
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

import logging
import multiprocessing
import os
import subprocess

import pytest

from opensearchpy import OpenSearch
from redis import Redis
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.mysql import MySqlContainer
from testcontainers.opensearch import OpenSearchContainer
from testcontainers.redis import RedisContainer
from grimoirelab.core.consumers.archivist import OpenSearchArchivist


STREAM_NAME = "test_stream"
CONSUMER_GROUP = "test_group"
CONSUMER_NAME = "test_consumer"
EVENTS_INDEX = "test_index"


mysql = MySqlContainer("mariadb:latest", root_password="root").with_exposed_ports(3306)
redis = RedisContainer().with_exposed_ports(6379)
opensearch = OpenSearchContainer().with_exposed_ports(9200)


@pytest.fixture(scope="module")
def setup_mysql(request):
    mysql.start()

    def remove_container():
        mysql.stop()

    request.addfinalizer(remove_container)


@pytest.fixture(scope="module")
def setup_redis(request):
    redis.start()

    def remove_container():
        redis.stop()

    request.addfinalizer(remove_container)


@pytest.fixture(scope="module")
def setup_opensearch(request):
    opensearch.start()

    def remove_container():
        opensearch.stop()

    request.addfinalizer(remove_container)
    wait_for_logs(opensearch, ".*recovered .* indices into cluster_state.*")


@pytest.fixture(scope="module", autouse=True)
def setup_containers(setup_opensearch, setup_redis, setup_mysql):
    yield


@pytest.fixture(scope="module")
def grimoirelab_config():
    """Fixture to set up the GrimoireLab configuration."""

    os.environ["DJANGO_SETTINGS_MODULE"] = "grimoirelab.core.config.settings"
    os.environ["GRIMOIRELAB_REDIS_PORT"] = str(redis.get_exposed_port(6379))
    os.environ["GRIMOIRELAB_DB_PORT"] = str(mysql.get_exposed_port(3306))
    os.environ["GRIMOIRELAB_DB_PASSWORD"] = mysql.root_password
    os.environ["GRIMOIRELAB_ARCHIVIST_STORAGE_URL"] = f"http://localhost:{opensearch.get_exposed_port(9200)}"
    os.environ["GRIMOIRELAB_USER_PASSWORD"] = "admin"
    os.environ["GRIMOIRELAB_ARCHIVIST_BLOCK_TIMEOUT"] = "1000"

    subprocess.run(["grimoirelab", "admin", "setup"])
    subprocess.run(["grimoirelab", "admin", "create-user", "--username", "admin", "--no-interactive"])


@pytest.fixture
def run_archivist():
    """Fixture to run the archivist in a separate process."""

    def _run_archivist(redis_host, redis_port):
        conn = Redis(
            host=redis_host,
            port=redis_port,
        )

        archivist = OpenSearchArchivist(
            connection=conn,
            stream_name=STREAM_NAME,
            consumer_group=CONSUMER_GROUP,
            consumer_name=CONSUMER_NAME,
            stream_block_timeout=500,
            logging_level=logging.DEBUG,
            url=f"http://localhost:{opensearch.get_exposed_port(9200)}",
            user="admin",
            password="admin",
            index=EVENTS_INDEX,
            bulk_size=100,
            verify_certs=False,
        )
        archivist.start()

    redis_host = redis.get_container_host_ip()
    redis_port = redis.get_exposed_port(6379)
    process = multiprocessing.Process(target=_run_archivist, args=(redis_host, redis_port))
    process.start()

    yield process

    # Cleanup
    process.kill()
    process.join(0.1)
    process.close()


@pytest.fixture
def redis_conn():
    """Fixture to create a Redis connection."""

    conn = Redis(
        host=redis.get_container_host_ip(),
        port=redis.get_exposed_port(6379),
    )

    yield conn

    # Cleanup
    conn.flushdb()


@pytest.fixture
def opensearch_conn():
    """Fixture to create an OpenSearch connection."""

    conn = OpenSearch(
        hosts=[f"http://localhost:{opensearch.get_exposed_port(9200)}"],
        http_auth=("admin", "admin"),
        verify_certs=False,
    )

    yield conn

    # Cleanup
    conn.indices.delete(index=EVENTS_INDEX, ignore=[400, 404])
