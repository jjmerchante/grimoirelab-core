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

import hashlib
import json
import logging
import time

import pytest

from grimoirelab.core.consumers.archivist import OpenSearchArchivist, OpenSearchArchivistPool
from .conftest import EVENTS_INDEX, STREAM_NAME, CONSUMER_GROUP, CONSUMER_NAME, opensearch

from ..utils import RedisStream, read_file


def test_archivist_start(redis_conn, opensearch_conn, run_archivist):
    """Test whether an archivist inserts item in OpenSearch"""

    # Create events
    rstream = RedisStream(redis_conn, "test_stream")
    events = json.loads(read_file("tests/integration/data/events.json"))
    for i, event in enumerate(events):
        rstream.add_entry(event=event, message_id=f"{i + 1}-0")

    # Wait for the archivist to process the events
    time.sleep(10)

    # Check if the events are in OpenSearch
    result = opensearch_conn.count(index=EVENTS_INDEX)
    assert result["count"] == len(events)

    # Check if the events are not in Redis
    pending = redis_conn.xpending(STREAM_NAME, CONSUMER_GROUP)
    assert pending["pending"] == 0


def test_insert_many_huge_events(redis_conn, opensearch_conn):
    """Test whether an archivist inserts a huge events in OpenSearch"""

    # Create events
    rstream = RedisStream(redis_conn, "test_stream")
    rstream.create_group(CONSUMER_GROUP)
    event = json.loads(read_file("tests/integration/data/huge_event.json"))
    for i in range(10):
        event["id"] = hashlib.sha1(f"event-{i}".encode("utf-8")).hexdigest()
        rstream.add_entry(event=event, message_id=f"{i + 1}-0")

    archivist = OpenSearchArchivist(
        connection=redis_conn,
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
    new_entries = archivist.fetch_new_entries()
    new_entries = list(new_entries)
    assert len(new_entries) == 10

    # This will fail to insert the huge event in OpenSearch
    archivist.process_entries(new_entries)

    # Check if the events are in OpenSearch
    result = opensearch_conn.count(index=EVENTS_INDEX)
    assert result["count"] == 0

    # Check if the events are still pending
    pending = redis_conn.xpending(STREAM_NAME, CONSUMER_GROUP)
    assert pending["pending"] == 10

    # Simulate the archivist recovering the entries
    recovered_entries = archivist.recover_stream_entries(recover_idle_time=1)
    archivist.process_entries(recovered_entries, recovery=True)

    # Wait for OpenSearch to process the event count
    time.sleep(5)

    # Check if the events are in OpenSearch
    result = opensearch_conn.count(index=EVENTS_INDEX)
    assert result["count"] == 10

    # Check if the events are still pending
    pending = redis_conn.xpending(STREAM_NAME, CONSUMER_GROUP)
    assert pending["pending"] == 0


def test_archivist_pool(redis_conn, opensearch_conn):
    """
    Test whether an archivist pool inserts items in OpenSearch

    :param redis_conn: Redis connection
    :param opensearch_conn: OpenSearch connection
    """
    # Create events
    rstream = RedisStream(redis_conn, STREAM_NAME)
    events = json.loads(read_file("tests/integration/data/events.json"))
    for i, event in enumerate(events):
        rstream.add_entry(event=event, message_id=f"{i + 1}-0")

    pool = OpenSearchArchivistPool(
        connection=redis_conn,
        stream_name=STREAM_NAME,
        group_name=CONSUMER_GROUP,
        num_consumers=5,
        stream_block_timeout=500,
        verbose=True,
        url=f"http://localhost:{opensearch.get_exposed_port(9200)}",
        user="admin",
        password="admin",
        index=EVENTS_INDEX,
        rollover_indices=False,
        bulk_size=100,
        verify_certs=False,
    )
    pool.start(burst=True)

    # Wait the workers to insert the events
    time.sleep(5)

    # Check the events are in OpenSearch
    result = opensearch_conn.count(index=EVENTS_INDEX)
    assert result["count"] == len(events)

    # Check that the events are not in Redis
    pending = redis_conn.xpending(STREAM_NAME, CONSUMER_GROUP)
    assert pending["pending"] == 0


@pytest.mark.parametrize("opensearch_conn", [True], indirect=True)
def test_archivist_pool_with_rollover(redis_conn, opensearch_conn):
    """
    Test whether an archivist pool with rollover inserts items in OpenSearch

    :param redis_conn: Redis connection
    :param opensearch_conn: OpenSearch connection
    """
    # Create events
    rstream = RedisStream(redis_conn, "test_stream")
    events = json.loads(read_file("tests/integration/data/events.json"))
    for i, event in enumerate(events):
        rstream.add_entry(event=event, message_id=f"{i + 1}-0")

    pool = OpenSearchArchivistPool(
        connection=redis_conn,
        stream_name=STREAM_NAME,
        group_name=CONSUMER_GROUP,
        num_consumers=5,
        stream_block_timeout=500,
        verbose=True,
        url=f"http://localhost:{opensearch.get_exposed_port(9200)}",
        user="admin",
        password="admin",
        index=EVENTS_INDEX,
        rollover_indices=True,
        rollover_size="15kb",
        bulk_size=100,
        verify_certs=False,
    )
    pool.start(burst=True)

    # Wait the workers to insert the events
    time.sleep(5)

    # Check the events are in OpenSearch
    result = opensearch_conn.count(index=EVENTS_INDEX)
    assert result["count"] == len(events)

    # Check that the events are not in Redis
    pending = redis_conn.xpending(STREAM_NAME, CONSUMER_GROUP)
    assert pending["pending"] == 0

    # Check a new index was created with the EVENTS_INDEX alias
    indices = opensearch_conn.indices.get_alias(name=EVENTS_INDEX)

    assert len(indices) == 1

    # Check didn't fail to create the rollover policy
    stderr_logs, stdout_logs = opensearch.get_logs()
    expected = (
        f"Index [{EVENTS_INDEX}-000001] matched ISM policy template"
        f" and will be managed by {EVENTS_INDEX}_rollover_policy"
    )
    assert expected in stderr_logs.decode("utf-8")

    # Check policy exists and has expected content
    policy = opensearch_conn.transport.perform_request(
        "GET", f"/_plugins/_ism/policies/{EVENTS_INDEX}_rollover_policy"
    )
    assert policy["policy"]["policy_id"] == f"{EVENTS_INDEX}_rollover_policy"
    assert policy["policy"]["ism_template"][0]["index_patterns"] == [f"{EVENTS_INDEX}-*"]
    assert policy["policy"]["default_state"] == "rollover"
    assert policy["policy"]["states"][0]["name"] == "rollover"
    assert policy["policy"]["states"][0]["actions"][0]["rollover"]["min_size"] == "15kb"
    assert policy["policy"]["states"][0]["actions"][0]["rollover"]["copy_alias"]
