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

from django.conf import settings
from rest_framework import response, views
from django_rq import get_connection
from rest_framework.exceptions import ValidationError
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes


MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


class EventSerializer(serializers.Serializer):
    entry_id = serializers.CharField()
    event = serializers.JSONField()


class EventStream(views.APIView):
    """
    API endpoint that allows to get the latest events in the stream.
    By default, it returns the latest events in the stream.

    Old events are removed from the stream based on the retention policy configured.
    """

    serializer_class = EventSerializer

    @extend_schema(
        responses=EventSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name="from_id",
                type=OpenApiTypes.STR,
                description=(
                    "Start ID (inclusive) to read events from. "
                    "Can be a Redis Stream ID (e.g. '1609459200000-0') or a "
                    "timestamp in milliseconds. Use for paginating forward."
                ),
                required=False,
            ),
            OpenApiParameter(
                name="to_id",
                type=OpenApiTypes.STR,
                description=(
                    "End ID (inclusive) to read events up to. "
                    "Can be a Redis Stream ID or a timestamp in milliseconds."
                ),
                required=False,
            ),
            OpenApiParameter(
                name="size",
                default=25,
                type=OpenApiTypes.INT,
                description=f"Maximum number of events to return (default {DEFAULT_PAGE_SIZE}, max {MAX_PAGE_SIZE}).",
                required=False,
            ),
        ],
    )
    def get(self, request, format=None):
        events_stream = settings.GRIMOIRELAB_EVENTS_STREAM_NAME
        from_id = request.query_params.get("from_id", None)
        to_id = request.query_params.get("to_id", None)
        try:
            size = int(request.query_params.get("size", DEFAULT_PAGE_SIZE))
            if size < 1 or size > MAX_PAGE_SIZE:
                raise ValueError
        except ValueError:
            raise ValidationError("'size' parameter must be an integer between 1 and 100.")

        connection = get_connection()
        if from_id is None and to_id is None:
            # Get the latest events
            entries = connection.xrevrange(events_stream, max="+", min="-", count=size)
            entries = reversed(entries)
        else:
            entries = connection.xrange(
                events_stream, min=from_id or "-", max=to_id or "+", count=size
            )

        events = []
        for entry in entries:
            entry_id = entry[0].decode("utf-8")
            entry_data = json.loads(entry[1][b"data"])
            event = {"entry_id": entry_id, "event": entry_data}
            events.append(event)

        return response.Response(events)
