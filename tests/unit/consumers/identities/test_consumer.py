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

from grimoirelab.core.consumers.identities.consumer import SortingHatConsumer
from grimoirelab.core.consumers.consumer import Entry

from ...base import GrimoireLabTestCase


class TestSortingHatConsumer(GrimoireLabTestCase):
    def test_initialization(self):
        """Test whether the SortingHatConsumer is initialized correctly"""

        consumer = SortingHatConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
        )

        self.assertEqual(consumer.stream_name, "test_stream")
        self.assertEqual(consumer.consumer_group, "test_group")
        self.assertEqual(consumer.consumer_name, "test_consumer")

    @patch("grimoirelab.core.consumers.identities.consumer.find_identities_extractors")
    @patch("grimoirelab.core.consumers.identities.consumer.get_user_model")
    @patch("grimoirelab.core.consumers.identities.consumer.SortingHatContext")
    def test_process_entries_success(
        self, mock_sh_context, mock_get_user_model, mock_find_extractors
    ):
        """Test whether entries are processed correctly when extractor succeeds"""

        # Mock user and context
        mock_user = MagicMock()
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user
        mock_get_user_model.return_value = mock_user_model

        mock_context = MagicMock()
        mock_sh_context.return_value = mock_context

        # Mock extractor
        mock_extractor = MagicMock()
        mock_commit = MagicMock(return_value=mock_extractor)
        mock_issue = MagicMock(return_value=mock_extractor)
        mock_find_extractors.return_value = {"commit": mock_commit, "issue": mock_issue}

        entries = [
            Entry(message_id="1-0", event={"id": "event_1", "type": "commit"}),
            Entry(message_id="2-0", event={"id": "event_2", "type": "commit"}),
            Entry(message_id="3-0", event={"id": "event_3", "type": "issue"}),
        ]

        consumer = SortingHatConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
        )

        # Mock the ack_entries method to check the calls
        consumer.ack_entries = MagicMock()

        consumer.process_entries(entries)

        # Verify extractors were called correctly
        self.assertEqual(mock_commit.call_count, 2)
        self.assertEqual(mock_issue.call_count, 1)

        # Verify events were processed
        mock_extractor.process.assert_any_call({"id": "event_1", "type": "commit"})
        mock_extractor.process.assert_any_call({"id": "event_2", "type": "commit"})
        mock_extractor.process.assert_any_call({"id": "event_3", "type": "issue"})

        # Verify all entries were acknowledged, even those without extractor
        consumer.ack_entries.assert_any_call(["1-0"])
        consumer.ack_entries.assert_any_call(["2-0"])
        consumer.ack_entries.assert_any_call(["3-0"])

    @patch("grimoirelab.core.consumers.identities.consumer.find_identities_extractors")
    @patch("grimoirelab.core.consumers.identities.consumer.get_user_model")
    @patch("grimoirelab.core.consumers.identities.consumer.SortingHatContext")
    def test_process_entries_unknown_extractor(
        self, mock_sh_context, mock_get_user_model, mock_find_extractors
    ):
        """Test whether entries with unknown extractors are acknowledged but not processed"""

        # Mock user and context
        mock_user = MagicMock()
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user
        mock_get_user_model.return_value = mock_user_model

        mock_context = MagicMock()
        mock_sh_context.return_value = mock_context

        # Mock extractor - only has git-commit extractor
        mock_extractor = MagicMock()
        mock_extractor_class = MagicMock(return_value=mock_extractor)
        mock_find_extractors.return_value = {"commit": mock_extractor_class}

        entries = [
            Entry(message_id="1-0", event={"id": "event_1", "type": "commit"}),
            Entry(message_id="2-0", event={"id": "event_2", "type": "unknown"}),
        ]

        consumer = SortingHatConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
        )

        # Mock the ack_entries method to check the calls
        consumer.ack_entries = MagicMock()

        consumer.process_entries(entries)

        # Verify only known extractor was called
        mock_extractor_class.assert_called_once()
        mock_extractor.process.assert_called_once_with({"id": "event_1", "type": "commit"})

        # Verify both entries were acknowledged (unknown types are acked without processing)
        consumer.ack_entries.assert_any_call(["1-0"])
        consumer.ack_entries.assert_any_call(["2-0"])

    @patch("grimoirelab.core.consumers.identities.consumer.find_identities_extractors")
    @patch("grimoirelab.core.consumers.identities.consumer.get_user_model")
    @patch("grimoirelab.core.consumers.identities.consumer.SortingHatContext")
    def test_process_entries_extractor_error(
        self, mock_sh_context, mock_get_user_model, mock_find_extractors
    ):
        """Test whether entries are handled correctly when extractor raises exception"""

        # Mock user and context
        mock_user = MagicMock()
        mock_user_model = MagicMock()
        mock_user_model.objects.get.return_value = mock_user
        mock_get_user_model.return_value = mock_user_model

        mock_context = MagicMock()
        mock_sh_context.return_value = mock_context

        # Mock extractor that raises an exception
        mock_extractor = MagicMock()
        mock_extractor.process.side_effect = [None, Exception("Processing error"), None]
        mock_extractor_class = MagicMock(return_value=mock_extractor)
        mock_find_extractors.return_value = {"commit": mock_extractor_class}

        entries = [
            Entry(message_id="1-0", event={"id": "event_1", "type": "commit"}),
            Entry(message_id="2-0", event={"id": "event_2", "type": "commit"}),
            Entry(message_id="3-0", event={"id": "event_3", "type": "commit"}),
        ]

        consumer = SortingHatConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
        )

        # Mock the ack_entries method to check the calls
        consumer.ack_entries = MagicMock()

        consumer.process_entries(entries)

        # Verify all extractors were called
        self.assertEqual(mock_extractor_class.call_count, 3)
        self.assertEqual(mock_extractor.process.call_count, 3)

        # Verify only successful entries were acknowledged (entry 2 failed)
        consumer.ack_entries.assert_any_call(["1-0"])
        consumer.ack_entries.assert_any_call(["3-0"])
