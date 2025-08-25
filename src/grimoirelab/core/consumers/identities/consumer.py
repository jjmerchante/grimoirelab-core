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

from typing import Iterable

from django.contrib.auth import get_user_model
from sortinghat.core.context import SortingHatContext

from .extractor import find_identities_extractors
from ..consumer import Consumer, Entry
from ..consumer_pool import ConsumerPool


class SortingHatConsumer(Consumer):
    """Extract identities from events and store them in SortingHat."""

    def process_entries(self, entries: Iterable[Entry], recovery: bool = False):
        """Extract identities from events and store them in SortingHat."""

        extractors = find_identities_extractors("grimoirelab.core.consumers.identities.extractors")

        self.logger.debug(f"Found extractors for events: {list(extractors.keys())}")

        system_user = get_user_model().objects.get(username="system-user")
        sh_ctx = SortingHatContext(user=system_user, job_id=None, tenant="default")

        for entry in entries:
            try:
                extractor = extractors[entry.event["type"]](sh_ctx)
            except KeyError:
                self.logger.debug(f"Unknown extractor for event type '{entry.event['type']}'")
                self.ack_entries([entry.message_id])
                continue

            try:
                extractor.process(entry.event)
                self.ack_entries([entry.message_id])
            except Exception as e:
                self.logger.error(f"Error processing event {entry.event['id']}: {e}")
                continue


class SortingHatConsumerPool(ConsumerPool):
    """Pool of SortingHat identities consumers."""

    CONSUMER_CLASS = SortingHatConsumer
