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

from functools import lru_cache
from typing import Iterable

from django.conf import settings
from django.contrib.auth import get_user_model

from sortinghat.core.api import add_identity
from sortinghat.core.context import SortingHatContext
from sortinghat.core.errors import AlreadyExistsError, InvalidValueError

from .consumer import Consumer, Entry
from .consumer_pool import ConsumerPool

from chronicler.events.core.git import (
    GIT_EVENT_COMMIT_AUTHORED_BY,
    GIT_EVENT_COMMIT_COMMITTED_BY,
    GIT_EVENT_COMMIT_ACKED_BY,
    GIT_EVENT_COMMIT_CO_AUTHORED_BY,
    GIT_EVENT_COMMIT_HELPED_BY,
    GIT_EVENT_COMMIT_MENTORED_BY,
    GIT_EVENT_COMMIT_REPORTED_BY,
    GIT_EVENT_COMMIT_REVIEWED_BY,
    GIT_EVENT_COMMIT_SIGNED_OFF_BY,
    GIT_EVENT_COMMIT_SUGGESTED_BY,
    GIT_EVENT_COMMIT_TESTED_BY,
)


IDENTITY_EVENTS = (
    GIT_EVENT_COMMIT_AUTHORED_BY,
    GIT_EVENT_COMMIT_COMMITTED_BY,
    GIT_EVENT_COMMIT_ACKED_BY,
    GIT_EVENT_COMMIT_CO_AUTHORED_BY,
    GIT_EVENT_COMMIT_HELPED_BY,
    GIT_EVENT_COMMIT_MENTORED_BY,
    GIT_EVENT_COMMIT_REPORTED_BY,
    GIT_EVENT_COMMIT_REVIEWED_BY,
    GIT_EVENT_COMMIT_SIGNED_OFF_BY,
    GIT_EVENT_COMMIT_SUGGESTED_BY,
    GIT_EVENT_COMMIT_TESTED_BY,
)


class SortingHatConsumer(Consumer):
    """Store identity events in SortingHat."""

    def __init__(self, *args, **kwargs):
        """Initialize the consumer."""

        super().__init__(*args, **kwargs)

        system_user = get_user_model().objects.get(username=settings.SYSTEM_BOT_USER)
        self.sh_ctx = SortingHatContext(user=system_user, job_id=None, tenant="default")

    def process_entries(self, entries: Iterable[Entry], recovery: bool = False):
        """Extract identities from events and store them in SortingHat."""

        to_ack = []
        i = 0

        for entry in entries:
            i += 1
            if len(to_ack) > 100:
                self.ack_entries(to_ack)
                to_ack = []

            if entry.event["type"] not in IDENTITY_EVENTS:
                to_ack.append(entry.message_id)
                continue

            identity = entry.event.get("data", {})
            source = identity.get("source")
            username = identity.get("username")
            email = identity.get("email")
            name = identity.get("name")

            try:
                self.store_identity(source=source, username=username, email=email, name=name)
                to_ack.append(entry.message_id)
            except Exception as e:
                self.logger.error(f"Error processing event {entry.event['id']}: {e}")

        if len(to_ack) > 0:
            self.ack_entries(to_ack)

    @lru_cache(maxsize=1024)
    def store_identity(
        self, source: str = None, username: str = None, email: str = None, name: str = None
    ):
        """Import identity from an event."""

        try:
            add_identity(self.sh_ctx, source=source, name=name, email=email, username=username)
        except InvalidValueError:
            self.logger.warning(
                f"Skipping identity with invalid data: source={source}, "
                f"username={username}, email={email}, name={name}"
            )
        except AlreadyExistsError:
            pass


class SortingHatConsumerPool(ConsumerPool):
    """Pool of SortingHat identities consumers."""

    CONSUMER_CLASS = SortingHatConsumer
