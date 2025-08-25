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

import re

from typing import Generator

from chronicler.events.core.git import GIT_EVENT_COMMIT
from grimoirelab.core.consumers.identities.extractor import IdentitiesExtractor


AUTHOR_P2P_REGEX = re.compile(
    r"(?P<first_authors>.* .*) ([aA][nN][dD]|&|\+) (?P<last_author>.* .*) (?P<email>.*)"
)
AUTHOR_P2P_NEW_REGEX = re.compile(r"Co-authored-by:(?P<first_authors>.* .*<.*>)\n?")
AUTHOR_REGEX = re.compile(r"^\s*(?P<field>.*): (?P<author>.* <.*>)$", re.MULTILINE)
COMMON_COMMIT_TRAILERS = [
    "acked-by",
    "approved-by",
    "co-authored-by",
    "co-developed-by",
    "helped-by",
    "mentored-by",
    "merged-by",
    "reported-by",
    "reviewed-by",
    "signed-off-by",
    "suggested-by",
    "tested-by",
]


class GitCommitIdentities(IdentitiesExtractor):
    """Extractor for Git commit events."""

    event_type = GIT_EVENT_COMMIT
    source = "git"

    def process(self, event: dict):
        """Extract identities from a Git commit event."""

        identities = self.get_identities(event)

        for identity in identities:
            self.store_identity(**identity)

    def get_identities(self, event: dict) -> Generator[dict]:
        """Extract identities from a Git commit event."""

        author = event["data"].get("Author", None)
        if author:
            yield from self._get_users(author)

        committer = event["data"].get("Commit", None)
        if committer:
            yield from self._get_users(committer)

        signers = event["data"].get("Signed-off-by", None)
        if signers:
            for signer in signers:
                user = self._get_sh_identity(signer)
                yield user

        message = event["data"].get("message", "")
        co_authors = AUTHOR_REGEX.findall(message)
        if co_authors:
            for field, author in co_authors:
                if field.lower() in COMMON_COMMIT_TRAILERS:
                    yield from self._get_users(author)

    def _get_users(self, user_str: str) -> Generator[dict]:
        """Extract multiple users from a Git user string."""

        m = AUTHOR_P2P_REGEX.match(user_str)
        n = AUTHOR_P2P_NEW_REGEX.match(user_str)
        if m or n:
            authors = self._get_authors(user_str)
            for author in authors:
                user = self._get_sh_identity(author)
                yield user
        else:
            user = self._get_sh_identity(user_str)
            yield user

    @staticmethod
    def _get_sh_identity(git_user: str) -> dict:
        """Extract identity information from a Git user string."""

        identity = {}

        fields = git_user.split("<")
        name = fields[0]
        name = name.strip()
        email = None
        if len(fields) > 1:
            email = git_user.split("<")[1][:-1]
        identity["username"] = None
        identity["email"] = email
        identity["name"] = name

        return identity

    @staticmethod
    def _get_authors(authors_str: str) -> list[str]:
        """Extract the authors from a multiauthor"""

        authors = []

        # Old style co-authored-by
        m = AUTHOR_P2P_REGEX.match(authors_str)
        if m:
            authors = m.group("first_authors").split(",")
            authors = [author.strip() for author in authors]
            authors += [m.group("last_author")]

        # New style co-authored-by
        n = AUTHOR_P2P_NEW_REGEX.findall(authors_str)
        if n:
            authors = [author.strip() for author in n]

        return list(set(authors))
