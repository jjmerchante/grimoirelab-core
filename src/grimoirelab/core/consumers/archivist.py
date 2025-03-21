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
import typing
import warnings

import certifi
import urllib3

from opensearchpy import OpenSearch, RequestError
from urllib3.util import create_urllib3_context

from .consumer import Consumer, Entry
from .consumer_pool import ConsumerPool

if typing.TYPE_CHECKING:
    from typing import Iterable


BULK_SIZE = 100

DEFAULT_INDEX = "events"

MAPPING = {
    "mappings": {
        "properties": {
            "time": {
                "type": "date",
                "format": "strict_date_optional_time||epoch_second",
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
                    "mapping": {"type": "keyword"},
                }
            },
            {
                "formatdate": {
                    "match": "*",
                    "match_mapping_type": "date",
                    "mapping": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis",
                    },
                }
            },
        ]
    }
}


class OpenSearchArchivist(Consumer):
    """Store items in OpenSearch.

    This class implements the methods to store the events in an OpenSearch instance.

    :param url: OpenSearch URL
    :param user: OpenSearch username
    :param password: OpenSearch password
    :param index: OpenSearch index name
    :param bulk_size: Number of items to store in a single bulk request
    :param verify_certs: Whether to verify SSL certificates
    :param kwargs: Additional keyword arguments to pass to the parent class
    """
    def __init__(
        self,
        url: str,
        user: str | None = None,
        password: str | None = None,
        index: str = DEFAULT_INDEX,
        bulk_size: int = BULK_SIZE,
        verify_certs: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        auth = None
        if user and password:
            auth = (user, password)

        if not verify_certs:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            warnings.filterwarnings("ignore", message=".*verify_certs.*")

        self.index = index
        self.bulk_size = bulk_size

        self._setup_opensearch(url, auth, verify_certs)

    def process_entries(self, entries: Iterable[Entry], recovery: bool = False) -> None:
        """Process entries and store them in the OpenSearch instance."""

        # This is to ensure the entry didn't fail because it was so big.
        if recovery:
            bulk_size = 1
        else:
            bulk_size = self.bulk_size

        bulk_json = ""
        entry_map = {}
        current = 0
        for entry in entries:
            event = entry.event
            data_json = json.dumps(event)
            bulk_json += '{{"index" : {{"_id" : "{}" }} }}\n'.format(event["id"])
            bulk_json += data_json + "\n"

            entry_map[event["id"]] = entry.message_id
            current += 1

            if current >= bulk_size:
                new_items, failed_ids = self._bulk(body=bulk_json, index=self.index)
                if new_items > 0:
                    # ACK successful items
                    for failed_id in failed_ids:
                        entry_map.pop(failed_id, None)
                    self.ack_entries(list(entry_map.values()))

                entry_map = {}
                current = 0
                bulk_json = ""

        if current > 0:
            new_items, failed_ids = self._bulk(body=bulk_json, index=self.index)
            if new_items > 0:
                # ACK successful items
                for failed_id in failed_ids:
                    entry_map.pop(failed_id, None)
                self.ack_entries(list(entry_map.values()))

    def _create_index(self, index: str) -> None:
        """Create an index in the OpenSearch instance."""

        try:
            self.client.indices.create(index, body=MAPPING)
        except RequestError as e:
            if e.error == "resource_already_exists_exception":
                pass
            else:
                raise

    def _setup_opensearch(self, url: str, auth: tuple[str, str] | None, verify_certs: bool) -> None:
        """Set up the OpenSearch client.

        :param url: OpenSearch URL
        :param auth: Authentication credentials (user, password)
        :param verify_certs: Whether to verify SSL certificates
        """
        context = None
        if verify_certs:
            # Use certificates from the local system and certifi
            context = create_urllib3_context()
            context.load_default_certs()
            context.load_verify_locations(certifi.where())

        self.client = OpenSearch(
            hosts=[url],
            http_auth=auth,
            http_compress=True,
            verify_certs=verify_certs,
            ssl_context=context,
            ssl_show_warn=False,
            max_retries=3,
            retry_on_timeout=True,
        )
        self._create_index(self.index)

    def _bulk(self, body: str, index: str) -> (int, list):
        """Store data in the OpenSearch instance.

        :param body: body of the bulk request
        :param index: index name
        :return number of items inserted, and ids of failed items
        """
        failed_ids = []
        error = None

        try:
            response = self.client.bulk(body=body, index=index)
        except Exception as e:
            self.logger.error(f"Failed to insert data to ES: {e}.")
            return 0, []

        if response["errors"]:
            for item in response["items"]:
                if "error" in item["index"]:
                    failed_ids.append(item["index"]["_id"])
                    error = str(item["index"]["error"])

            # Just print one error message
            self.logger.warning(f"Failed to insert data to ES: {error}.")

        num_inserted = len(response["items"]) - len(failed_ids)
        self.logger.info(f"{num_inserted} items uploaded to ES. {len(failed_ids)} failed.")

        return num_inserted, failed_ids


class OpenSearchArchivistPool(ConsumerPool):
    """Pool of OpenSearch archivist consumers."""

    CONSUMER_CLASS = OpenSearchArchivist

    def __init__(
        self,
        url: str,
        user: str | None = None,
        password: str | None = None,
        index: str = DEFAULT_INDEX,
        bulk_size: int = BULK_SIZE,
        verify_certs: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.url = url
        self.user = user
        self.password = password
        self.index = index
        self.bulk_size = bulk_size
        self.verify_certs = verify_certs

    @property
    def extra_consumer_kwargs(self):
        return {
            "url": self.url,
            "user": self.user,
            "password": self.password,
            "index": self.index,
            "bulk_size": self.bulk_size,
            "verify_certs": self.verify_certs,
        }
