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

from unittest.mock import MagicMock, patch

from grimoirelab.core.consumers.identities.extractors.core.git import GitCommitIdentities
from chronicler.events.core.git import GIT_EVENT_COMMIT

from ...base import GrimoireLabTestCase


class TestGitCommitIdentities(GrimoireLabTestCase):
    """Test Git commit identities extractor"""

    def setUp(self):
        """Set up test fixtures"""

        super().setUp()
        self.mock_context = MagicMock()
        self.extractor = GitCommitIdentities(self.mock_context)

    def test_event_type(self):
        """Test the extractor event type"""

        self.assertEqual(GitCommitIdentities.event_type, GIT_EVENT_COMMIT)

    def test_source(self):
        """Test the extractor source"""

        self.assertEqual(GitCommitIdentities.source, "git")

    def test_get_sh_identity_with_email(self):
        """Test _get_sh_identity method with name and email"""

        git_user = "User name 1 <user1@example.com>"
        identity = GitCommitIdentities._get_sh_identity(git_user)

        expected = {"username": None, "email": "user1@example.com", "name": "User name 1"}
        self.assertEqual(identity, expected)

    def test_get_authors_old_style_coauthored(self):
        """Test _get_authors method with old style co-authored-by format"""

        authors_str = "User name1, User name2 and User name3 <user3@example.com>"
        authors = GitCommitIdentities._get_authors(authors_str)

        expected = ["User name1", "User name2", "User name3"]
        self.assertEqual(sorted(authors), sorted(expected))

    def test_get_authors_new_style_coauthored(self):
        """Test _get_authors method with new style co-authored-by format"""

        authors_str = "Co-authored-by:User name 1 <user1@example.com>\nCo-authored-by:User name 2 <user2@example.com>\n"
        authors = GitCommitIdentities._get_authors(authors_str)

        expected = ["User name 1 <user1@example.com>", "User name 2 <user2@example.com>"]
        self.assertEqual(sorted(authors), sorted(expected))

    def test_get_users_single_author(self):
        """Test _get_users method with single author"""

        user_str = "User name 1 <user1@example.com>"
        users = list(self.extractor._get_users(user_str))

        expected = [{"username": None, "email": "user1@example.com", "name": "User name 1"}]
        self.assertEqual(users, expected)

    def test_get_users_multiple_authors(self):
        """Test _get_users method with multiple authors (old style)"""

        user_str = "User name 1, User name 2 and User name 3 <user3@example.com>"
        users = list(self.extractor._get_users(user_str))

        self.assertEqual(len(users), 3)
        names = [user["name"] for user in users]
        self.assertIn("User name 1", names)
        self.assertIn("User name 2", names)
        self.assertIn("User name 3", names)

    def test_get_identities(self):
        """Test get_identities method with a commit event"""

        event = {
            "data": {
                "Author": "User name 1 <user1@example.com>",
                "Commit": "User name 1 <user1@example.com>",
            }
        }

        identities = list(self.extractor.get_identities(event))

        # Should get 2 identities (author and committer, even if same person)
        self.assertEqual(len(identities), 2)

        for identity in identities:
            self.assertEqual(identity["email"], "user1@example.com")
            self.assertEqual(identity["name"], "User name 1")
            self.assertIsNone(identity["username"])

    def test_get_identities_with_signers(self):
        """Test get_identities method with signed-off-by"""

        event = {
            "data": {
                "Author": "User name 1 <user1@example.com>",
                "Commit": "User name 1 <user1@example.com>",
                "Signed-off-by": [
                    "User name 1 <user1@example.com>",
                    "User name 2 <user2@example.com>",
                ],
            }
        }

        identities = list(self.extractor.get_identities(event))

        # Should get 4 identities (author, committer, 2 signers)
        self.assertEqual(len(identities), 4)

        emails = [identity["email"] for identity in identities]
        names = [identity["name"] for identity in identities]

        self.assertEqual(emails.count("user1@example.com"), 3)
        self.assertEqual(emails.count("user2@example.com"), 1)
        self.assertIn("User name 1", names)
        self.assertIn("User name 2", names)

    def test_get_identities_merge(self):
        """Test get_identities method with merge commit"""

        event = {
            "data": {
                "Author": "User name 1 <user1@example.com>",
                "Commit": "GitHub <noreply@github.com>",
            }
        }

        identities = list(self.extractor.get_identities(event))

        # Should get 2 identities (author and committer)
        self.assertEqual(len(identities), 2)

        emails = [identity["email"] for identity in identities]
        names = [identity["name"] for identity in identities]

        self.assertIn("user1@example.com", emails)
        self.assertIn("noreply@github.com", emails)
        self.assertIn("User name 1", names)
        self.assertIn("GitHub", names)

    def test_get_identities_coauthored(self):
        """Test get_identities method with co-authored commit"""

        event = {
            "data": {
                "Author": "User name 1 <user1@example.com>",
                "Commit": "GitHub <noreply@github.com>",
                "message": "Some commit message\n\nCo-authored-by: User name 2 <user2@example.com>\nSigned-off-by: User name 3 <user3@example.com>",
            }
        }
        identities = list(self.extractor.get_identities(event))
        # Should get 4 identities (author, committer, co-author, signer)
        self.assertEqual(len(identities), 4)
        emails = [identity["email"] for identity in identities]
        names = [identity["name"] for identity in identities]
        self.assertIn("user1@example.com", emails)
        self.assertIn("User name 1", names)
        self.assertIn("noreply@github.com", emails)
        self.assertIn("GitHub", names)
        self.assertIn("user2@example.com", emails)
        self.assertIn("User name 2", names)
        self.assertIn("user3@example.com", emails)
        self.assertIn("User name 3", names)

    @patch.object(GitCommitIdentities, "store_identity")
    def test_process_calls_store_identity(self, mock_store):
        """Test that process method calls store_identity for each identity"""
        event = {
            "data": {
                "Author": "User name 1 <user1@example.com>",
                "Commit": "User name 2 <user2@example.com>",
            }
        }

        self.extractor.process(event)

        # Should call store_identity twice (once for author, once for committer)
        self.assertEqual(mock_store.call_count, 2)

        calls = mock_store.call_args_list
        call_kwargs = [call.kwargs for call in calls]

        expected_identities = [
            {"username": None, "email": "user1@example.com", "name": "User name 1"},
            {"username": None, "email": "user2@example.com", "name": "User name 2"},
        ]

        for expected in expected_identities:
            self.assertIn(expected, call_kwargs)
