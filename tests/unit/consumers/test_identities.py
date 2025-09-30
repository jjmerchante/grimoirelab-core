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

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model

from chronicler.events.core.git import GIT_EVENT_COMMIT_COMMITTED_BY
from grimoirelab.core.consumers.identities import SortingHatConsumer, GIT_EVENT_COMMIT_AUTHORED_BY
from grimoirelab.core.consumers.consumer import Entry

from sortinghat.core.models import Individual

from ..base import GrimoireLabTestCase


class TestSortingHatConsumer(GrimoireLabTestCase):
    """Test SortingHatConsumer class"""

    def setUp(self):
        super().setUp()

        self.system_user, _ = get_user_model().objects.get_or_create(
            username=settings.SYSTEM_BOT_USER,
            defaults={"is_staff": False, "is_superuser": False, "is_active": True},
        )

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

    def test_process_entries_success(self):
        """Test whether entries are processed correctly when extractor succeeds"""

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
        with patch.object(consumer, "ack_entries") as mock_ack:
            consumer.process_entries(entries)

            # Verify all entries were acknowledged
            mock_ack.assert_called_with(["1-0", "2-0", "3-0"])

    def test_process_identities(self):
        """Test whether entries with identities are processed"""

        entries = [
            Entry(
                message_id="1-0",
                event={
                    "id": "event_1",
                    "type": GIT_EVENT_COMMIT_AUTHORED_BY,
                    "source": "https://github.com/chaoss/example.git",
                    "linked_event": "commit_12345",
                    "data": {
                        "source": "git",
                        "username": "johndoe",
                        "email": "johndoe@example.com",
                        "name": None,
                        "role": "authored_by",
                        "uuid": "e0fd947fca0d7949939ea4e911e9e3817f762181",
                    },
                },
            ),
            Entry(
                message_id="2-0",
                event={
                    "id": "event_2",
                    "type": GIT_EVENT_COMMIT_COMMITTED_BY,
                    "source": "https://github.com/chaoss/example.git",
                    "linked_event": "commit_12345",
                    "data": {
                        "source": "git",
                        "username": "janedoe",
                        "email": "janedoe@example.com",
                        "name": "Jane Doe",
                        "role": "committed_by",
                        "uuid": "460508eb026ffc5d06ef31f73ddc2ead158fae42",
                    },
                },
            ),
        ]

        consumer = SortingHatConsumer(
            connection=self.conn,
            stream_name="test_stream",
            consumer_group="test_group",
            consumer_name="test_consumer",
            stream_block_timeout=1000,
            logging_level=logging.DEBUG,
        )

        consumer.process_entries(entries)

        individuals = Individual.objects.all().order_by("mk")

        self.assertEqual(individuals.count(), 2)

        individual = individuals[0]
        identities = individual.identities.all()
        self.assertEqual(identities.count(), 1)
        identity = identities[0]
        self.assertEqual(identity.username, "janedoe")
        self.assertEqual(identity.email, "janedoe@example.com")
        self.assertEqual(identity.name, "Jane Doe")
        self.assertEqual(identity.source, "git")
        self.assertEqual(identity.uuid, "460508eb026ffc5d06ef31f73ddc2ead158fae42")

        individual = individuals[1]
        identities = individual.identities.all()
        self.assertEqual(identities.count(), 1)
        identity = identities[0]
        self.assertEqual(identity.username, "johndoe")
        self.assertEqual(identity.email, "johndoe@example.com")
        self.assertEqual(identity.name, None)
        self.assertEqual(identity.source, "git")
        self.assertEqual(identity.uuid, "e0fd947fca0d7949939ea4e911e9e3817f762181")
