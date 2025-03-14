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
import typing

import certifi
import redis
import rq.job
import urllib3

from django.conf import settings
from opensearchpy import OpenSearch, RequestError
from urllib3.util import create_urllib3_context


if typing.TYPE_CHECKING:
    from typing import Any


logger = logging.getLogger('archivist')


def archivist_job(
    storage_type: str,
    storage_url: str,
    storage_username: str,
    storage_password: str,
    storage_db_name: str,
    storage_verify_certs: bool,
    redis_group: str,
    consumer_name: str,
    events_queue: str,
    limit: int = settings.GRIMOIRELAB_ARCHIVIST['EVENTS_PER_JOB'],
    block_timeout: int = settings.GRIMOIRELAB_ARCHIVIST['BLOCK_TIMEOUT']
) -> ArchivistProgress:
    """Fetch and archive events.

    It will fetch events from a Redis stream and store them in a
    storage system.

    :param storage_type: type of the storage system (e.g., 'opensearch')
    :param storage_url: URL of the storage system
    :param storage_username: Username to use when authentication is required
    :param storage_password: Password to use when authentication is required
    :param storage_db_name: Name of the database to use
    :param storage_verify_certs: Verify certificates when connecting to the storage system
    :param redis_group: Redis group name to use for fetching events
    :param consumer_name: Name of the consumer
    :param events_queue: Redis stream where the events are fetched
    :param limit: Maximum number of events to fetch and store
    :param block_timeout: Time (ms) to block when fetching events, None for not blocking,
        0 for blocking indefinitely.
    """
    rq_job = rq.get_current_job()

    progress = ArchivistProgress(
        rq_job.get_id(),
        storage_type,
        redis_group,
        consumer_name
    )
    rq_job.progress = progress

    Storage = get_storage_backend(storage_type)
    storage = Storage(url=storage_url,
                      user=storage_username,
                      password=storage_password,
                      db_name=storage_db_name,
                      verify_certs=storage_verify_certs)
    events = events_consumer(rq_job.connection,
                             consumer_name,
                             events_queue,
                             redis_group,
                             limit,
                             block_timeout)

    progress.total = storage.store(events)

    return progress


def _create_consumer_group(
        connection: redis.Redis,
        stream_name: str,
        group_name: str
) -> None:
    """Create a consumer group if it does not exist

    :param connection: Redis connection
    :param stream_name: Name of the stream
    :param group_name: Name of the group
    """
    try:
        connection.xgroup_create(stream_name, group_name, id='0', mkstream=True)
    except redis.exceptions.ResponseError as e:
        if str(e) != 'BUSYGROUP Consumer Group name already exists':
            raise


def _recover_stream_entries(
        connection: redis.Redis,
        consumer_name: str,
        stream_name: str,
        group_name: str
) -> dict:
    """
    Transfers ownership of pending stream entries idle
    for 5m that match the specified criteria

    :param connection: Redis connection
    :param consumer_name: Name of the consumer
    :param stream_name: Name of the stream
    """
    logger.info(f"Recovering events from '{stream_name}' group '{group_name}'")

    while True:
        response = connection.xautoclaim(name=stream_name,
                                         groupname=group_name,
                                         consumername=consumer_name,
                                         min_idle_time=5 * 60 * 1000,
                                         count=10)

        # The response contains an array with the following contents
        # 1) "0-0" (stream ID to be used as the start argument for the next call)
        # 2) 1) 1) "1609338752495-0" (successfully claimed messages)
        #       2) 1) "field"
        #          2) "value"
        # 3) (empty array) (message IDs that no longer exist in the stream)
        messages = response[1]
        for message in messages:
            message_id = message[0]
            message_data = message[1][b'data']

            yield json.loads(message_data)

            connection.xack(stream_name, group_name, message_id)

        if response[0] == b"0-0":
            break


def events_consumer(
        connection: redis.Redis,
        consumer_name: str,
        stream_name: str,
        group_name: str,
        limit: int,
        block_timeout: int,
) -> iter(dict):
    """Get items from a Redis stream given a group and a consumer name

    :param connection: Redis connection
    :param consumer_name: Name of the consumer
    :param stream_name: Name of the stream
    :param group_name: Name of the group
    :param limit: Maximum number of items to fetch
    :param block_timeout: Time to block when fetching events, None for not blocking,
        0 for blocking indefinitely
    """
    _create_consumer_group(connection, stream_name, group_name)

    yield from _recover_stream_entries(connection=connection,
                                       consumer_name=consumer_name,
                                       group_name=group_name,
                                       stream_name=stream_name)

    logger.info(f"Fetching events from '{stream_name}' group "
                f"'{group_name}' as '{consumer_name}'")

    total = 0
    while True:
        try:
            response = connection.xreadgroup(groupname=group_name,
                                             consumername=consumer_name,
                                             streams={stream_name: '>'},
                                             count=10,
                                             block=block_timeout)

            # The response contains an array with the following contents
            # 1) 1) "mystream" (name of the stream)
            #    2) 1) 1) "1-0" (array of arrays containing the key and the entries)
            #          2) 1) "field"
            #             2) "value"
            if response:
                messages = response[0][1]
                for message in messages:
                    total += 1
                    message_id = message[0]
                    message_data = message[1][b'data']

                    yield json.loads(message_data)

                    connection.xack(stream_name, group_name, message_id)

            else:
                logger.info(f"No new messages for '{stream_name}:{group_name}:{consumer_name}'.")
                break

            if total >= limit:
                logger.info(f"{total} items inserted. Stop the job.")
                break

        except Exception as e:
            logger.error(f"Error consuming messages: {e}")
            raise e


class ArchivistProgress:
    """Class to store the progress of an Archivist job.

    It stores the summary of the job.

    :param job_id: job identifier
    :param backend: backend used to store the events
    :param group: group used to fetch the events
    """
    def __init__(self,
                 job_id: str,
                 backend: str,
                 group: str,
                 consumer_name: str,
                 total: int = 0) -> None:
        self.job_id = job_id
        self.backend = backend
        self.group = group
        self.consumer_name = consumer_name
        self.total = total

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchivistProgress:
        """Create a new instance from a dictionary."""

        return cls(
            data['job_id'],
            data['backend'],
            data['group'],
            data['consumer_name'],
            data['total']
        )

    def to_dict(self) -> dict[str, str | int]:
        """Convert object to a dict."""

        result = {
            'job_id': self.job_id,
            'backend': self.backend,
            'group': self.group,
            'consumer_name': self.consumer_name,
            'total': self.total
        }

        return result


class StorageBackend:
    """Base class for storage backends.

    This class defines the methods that should be implemented by
    a storage backend.

    :param url: URL of the storage backend
    """
    def __init__(
        self,
        url: str,
        db_name: str,
        user: str | None = None,
        password: str | None = None,
        verify_certs: bool = False
    ) -> None:
        self.url = url
        self.user = user
        self.password = password
        self.db_name = db_name
        self.verify_certs = verify_certs

    def store(self, data: dict[str, Any]) -> int:
        """Store data in the storage backend.

        :param data: Data to store

        :return: Number of items stored
        """
        raise NotImplementedError

    def close(self) -> None:
        """Close the connection to the storage backend."""

        pass


def get_storage_backend(storage_type: str) -> typing.Type[StorageBackend]:
    """Get the storage backend based on the type.

    :param storage_type: Type of the storage backend
    """
    if storage_type == 'opensearch':
        return OpenSearchStorage
    else:
        raise ValueError(f"Storage type '{storage_type}' not supported")


class OpenSearchStorage(StorageBackend):
    """Storage backend for OpenSearch.

    This class implements the methods to store data in an OpenSearch
    instance.

    :param url: URL of the OpenSearch instance
    """
    MAPPING = {
        "mappings": {
            "properties": {
                "time": {
                    "type": "date",
                    "format": "strict_date_optional_time||epoch_second"
                },
                "data": {
                    "properties": {
                        "message": {
                            "type": "text",
                            "index": True
                        },
                        "AuthorDate": {
                            "type": "date",
                            "format":
                                "EEE MMM d HH:mm:ss yyyy Z||EEE MMM d HH:mm:ss yyyy||strict_date_optional_time||epoch_millis"
                        },
                        "CommitDate": {
                            "type": "date",
                            "format":
                                "EEE MMM d HH:mm:ss yyyy Z||EEE MMM d HH:mm:ss yyyy||strict_date_optional_time||epoch_millis"
                        }
                    }
                }
            },
            "dynamic_templates": [
                {
                    "notanalyzed": {
                        "match": "*",
                        "match_mapping_type": "string",
                        "mapping": {
                            "type": "keyword"
                        }
                    }
                },
                {
                    "formatdate": {
                        "match": "*",
                        "match_mapping_type": "date",
                        "mapping": {
                            "type": "date",
                            "format": "strict_date_optional_time||epoch_millis"
                        }
                    }
                }
            ]
        }
    }

    def __init__(
            self,
            url: str,
            db_name: str,
            user: str | None = None,
            password: str | None = None,
            verify_certs: bool = False
    ) -> None:
        super().__init__(url=url, db_name=db_name, user=user, password=password, verify_certs=verify_certs)

        if not verify_certs:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        auth = None
        if user and password:
            auth = (user, password)

        context = None
        if self.verify_certs:
            # Use certificates from the local system and certifi
            context = create_urllib3_context()
            context.load_default_certs()
            context.load_verify_locations(certifi.where())

        self.client = OpenSearch(
            hosts=[url],
            http_auth=auth,
            verify_certs=self.verify_certs,
            ssl_context=context,
        )
        self._create_index(db_name)
        self.max_items_bulk = 100

    def _create_index(self, index_name: str) -> None:
        """Create an index in the OpenSearch instance.

        :param index_name: Name of the index
        """
        try:
            self.client.indices.create(index_name, body=self.MAPPING)
        except RequestError as e:
            if e.error == 'resource_already_exists_exception':
                pass
            else:
                raise

    def _bulk(self, body: str, index: str) -> int:
        """Store data in the OpenSearch instance.

        :param body: Data to store
        :param index: Name of the index
        """
        failed_items = []

        response = self.client.bulk(body=body, index=index)

        if response['errors']:
            # Due to multiple errors that may be thrown when inserting bulk data, only the first error is returned
            failed_items = [item['index'] for item in response['items'] if 'error' in item['index']]
            error = str(failed_items[0]['error'])

            logger.error(f"Failed to insert data to ES: {error}")

        inserted_items = len(response['items']) - len(failed_items)

        logger.info(f"{inserted_items} items uploaded to ES")

        return inserted_items

    def store(self, events: iter) -> None:
        """Store data in the OpenSearch instance.

        :param events: Events to store
        """
        current = 0
        new_items = 0

        bulk_json = ""
        for event in events:
            data_json = json.dumps(event)
            bulk_json += '{{"index" : {{"_id" : "{}" }} }}\n'.format(event['id'])
            bulk_json += data_json + "\n"
            current += 1

            if current >= self.max_items_bulk:
                new_items += self._bulk(body=bulk_json, index=self.db_name)
                current = 0
                bulk_json = ""

        if current > 0:
            new_items += self._bulk(body=bulk_json, index=self.db_name)

        return new_items
