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

from unittest.mock import patch, MagicMock

from grimoirelab.core.consumers.archivist import OpenSearchArchivist, Entry

from ..base import GrimoireLabTestCase


class TestOpenSearchArchivist(GrimoireLabTestCase):
    @patch("grimoirelab.core.consumers.archivist.OpenSearch")
    def test_initialization(self, mock_opensearch):
        """Test whether the OpenSearchArchivist is initialized correctly"""

        mock_client = MagicMock()
        mock_opensearch.return_value = mock_client

        archivist = OpenSearchArchivist(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
            url="https://localhost:9200",
            user="user",
            password="password",
            index="test_index",
            bulk_size=50,
            verify_certs=False,
        )

        self.assertEqual(archivist.index, "test_index")
        self.assertEqual(archivist.bulk_size, 50)

        mock_opensearch.assert_called_once_with(
            hosts=["https://localhost:9200"],
            http_auth=("user", "password"),
            http_compress=True,
            verify_certs=False,
            ssl_context=None,
            ssl_show_warn=False,
            max_retries=3,
            retry_on_timeout=True,
        )

    @patch("grimoirelab.core.consumers.archivist.OpenSearch")
    def test_process_entries(self, mock_opensearch):
        """Test whether entries are processed correctly"""

        mock_client = MagicMock()
        mock_opensearch.return_value = mock_client
        mock_client.bulk.return_value = {
            "items": [
                {"index": {"status": 201, "_id": "value_1"}},
                {"index": {"status": 201, "_id": "value_2"}},
                {"index": {"status": 201, "_id": "value_3"}},
            ],
            "errors": False,
        }
        entries = [
            Entry(message_id="1-0", event={"id": "value_1"}),
            Entry(message_id="2-0", event={"id": "value_2"}),
            Entry(message_id="3-0", event={"id": "value_3"}),
        ]

        archivist = OpenSearchArchivist(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
            url="https://localhost:9200",
            user="user",
            password="password",
            index="test_index",
            bulk_size=50,
            verify_certs=False,
        )
        # Mock the ack_entries method to check the calls
        archivist.ack_entries = MagicMock()

        archivist.process_entries(entries)

        mock_client.bulk.assert_called_once_with(
            body=(
                '{"index" : {"_id" : "value_1" } }\n'
                '{"id": "value_1"}\n'
                '{"index" : {"_id" : "value_2" } }\n'
                '{"id": "value_2"}\n'
                '{"index" : {"_id" : "value_3" } }\n'
                '{"id": "value_3"}\n'
            ),
            index="test_index",
        )
        archivist.ack_entries.assert_called_once_with(["1-0", "2-0", "3-0"])

    @patch("grimoirelab.core.consumers.archivist.OpenSearch")
    def test_process_entries_failed(self, mock_opensearch):
        """Test whether entries are processed and failed entries aren't acked"""

        mock_client = MagicMock()
        mock_opensearch.return_value = mock_client
        mock_client.bulk.return_value = {
            "items": [
                {"index": {"status": 201, "_id": "value_1"}},
                {"index": {"status": 400, "_id": "value_2", "error": "error"}},
                {"index": {"status": 201, "_id": "value_3"}},
            ],
            "errors": True,
        }
        entries = [
            Entry(message_id="1-0", event={"id": "value_1"}),
            Entry(message_id="2-0", event={"id": "value_2"}),
            Entry(message_id="3-0", event={"id": "value_3"}),
        ]

        archivist = OpenSearchArchivist(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
            url="https://localhost:9200",
            user="user",
            password="password",
            index="test_index",
            bulk_size=50,
            verify_certs=False,
        )
        # Mock the ack_entries method to check the calls
        archivist.ack_entries = MagicMock()

        archivist.process_entries(entries)

        mock_client.bulk.assert_called_once_with(
            body=(
                '{"index" : {"_id" : "value_1" } }\n'
                '{"id": "value_1"}\n'
                '{"index" : {"_id" : "value_2" } }\n'
                '{"id": "value_2"}\n'
                '{"index" : {"_id" : "value_3" } }\n'
                '{"id": "value_3"}\n'
            ),
            index="test_index",
        )
        archivist.ack_entries.assert_called_once_with(["1-0", "3-0"])
