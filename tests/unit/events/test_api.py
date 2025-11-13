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

import json

from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from ..base import GrimoireLabTestCase


class EventStreamApiTest(GrimoireLabTestCase):
    """Unit tests for the EventStream API"""

    client_class = APIClient

    def setUp(self):
        """Set up test environment"""

        super().setUp()

        # Patch get_connection in the events.api and use FakeRedis
        self.get_conn_patcher = patch(
            "grimoirelab.core.events.api.get_connection", return_value=self.conn
        )
        self.mock_get_connection = self.get_conn_patcher.start()

        user = get_user_model().objects.create(username="test", is_superuser=True)
        self.client.force_authenticate(user=user)
        self.stream_name = settings.GRIMOIRELAB_EVENTS_STREAM_NAME

        pipeline = self.conn.pipeline()
        for i in range(10):
            event = {
                "specversion": "1.0",
                "id": f"event-{i}",
                "source": "test-source",
                "type": "test.event.type",
                "time": 1700000000.0 + i,
                "data": {
                    "commit": i,
                },
            }
            pipeline.xadd(self.stream_name, {"data": json.dumps(event)}, id=f"170000000000{i}-0")
        pipeline.execute()

    def tearDown(self):
        self.get_conn_patcher.stop()
        super().tearDown()

    def test_get_latest_events_without_parameters(self):
        """Test getting latest events without any query parameters"""

        url = reverse("event-stream")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertEqual(len(response.data), 10)

        for i in range(10):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{i}-0")
            self.assertEqual(event["event"]["id"], f"event-{i}")
            self.assertEqual(event["event"]["data"]["commit"], i)

    def test_get_events_with_from_id(self):
        """Test getting events with from_id parameter"""

        url = reverse("event-stream")

        response = self.client.get(url, {"from_id": "1700000000005-0"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

        for i in range(5):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{5 + i}-0")
            self.assertEqual(event["event"]["id"], f"event-{5 + i}")
            self.assertEqual(event["event"]["data"]["commit"], 5 + i)

    def test_get_events_with_to_id(self):
        """Test getting events with to_id parameter"""

        url = reverse("event-stream")
        response = self.client.get(url, {"to_id": "1700000000004-0"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

        for i in range(5):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{i}-0")
            self.assertEqual(event["event"]["id"], f"event-{i}")
            self.assertEqual(event["event"]["data"]["commit"], i)

    def test_get_events_with_from_id_and_to_id(self):
        """Test getting events with both from_id and to_id parameters"""

        url = reverse("event-stream")
        response = self.client.get(url, {"from_id": "1700000000004-0", "to_id": "1700000000007-0"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 4)

        for i in range(4):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{4 + i}-0")
            self.assertEqual(event["event"]["id"], f"event-{4 + i}")
            self.assertEqual(event["event"]["data"]["commit"], 4 + i)

    def test_get_events_with_custom_size(self):
        """Test getting events with custom size parameter"""

        url = reverse("event-stream")
        response = self.client.get(url, {"size": "2"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        for i in range(2):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{8 + i}-0")
            self.assertEqual(event["event"]["id"], f"event-{8 + i}")
            self.assertEqual(event["event"]["data"]["commit"], 8 + i)

    def test_get_events_with_timestamps_as_ids(self):
        """Test getting events using timestamps instead of Redis stream IDs"""

        url = reverse("event-stream")
        response = self.client.get(url, {"from_id": "1700000000002", "to_id": "1700000000003"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        for i in range(2):
            event = response.data[i]
            self.assertEqual(event["entry_id"], f"170000000000{2 + i}-0")
            self.assertEqual(event["event"]["id"], f"event-{2 + i}")
            self.assertEqual(event["event"]["data"]["commit"], 2 + i)

    def test_get_events_empty_stream(self):
        """Test getting events from empty stream"""

        # Clear the stream
        self.conn.xtrim(self.stream_name, maxlen=0)

        url = reverse("event-stream")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_get_events_invalid_size_parameter(self):
        """Test getting events with invalid size parameter"""

        url = reverse("event-stream")
        response = self.client.get(url, {"size": "invalid"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], "'size' parameter must be an integer between 1 and 100.")

    def test_get_events_size_parameter_out_of_bounds(self):
        """Test getting events with size parameter out of bounds"""

        url = reverse("event-stream")

        response = self.client.get(url, {"size": "0"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], "'size' parameter must be an integer between 1 and 100.")

        response = self.client.get(url, {"size": "101"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data[0], "'size' parameter must be an integer between 1 and 100.")

    def test_event_data_parsing(self):
        """Test correct parsing of event data from Redis stream"""

        complex_event = {
            "specversion": "1.0",
            "id": "test-id-123",
            "source": "test-source",
            "type": "test.event.type",
            "time": 1234567890.0,
            "data": {
                "nested": {"object": "value", "array": [1, 2, 3]},
                "unicode": "test with unicode: ñáéíóú",
                "boolean": True,
                "null_value": None,
            },
        }
        self.conn.xtrim(self.stream_name, maxlen=0)
        self.conn.xadd(self.stream_name, {"data": json.dumps(complex_event)}, id="1234567890000-0")

        url = reverse("event-stream")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        event = response.data[0]
        self.assertEqual(event["entry_id"], "1234567890000-0")
        self.assertEqual(event["event"], complex_event)
