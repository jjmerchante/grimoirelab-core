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

import importlib
import logging
import pkgutil

from sortinghat.core.api import add_identity
from sortinghat.core.errors import AlreadyExistsError


class IdentitiesExtractor:
    """Base class for identity extractors."""

    event_type: str = None
    source: str = None

    def __init__(self, sh_ctx):
        """Initialize the extractor.

        :param sh_ctx: SortingHat context to use for calling the API.
        """

        self.sh_ctx = sh_ctx
        self.logger = logging.getLogger(self.__class__.__name__)

    def process(self, event: dict):
        """Extract identities from an event and store them.

        :param event: The event to extract identities from.

        :returns: A generator of identity dictionaries.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    def store_identity(self, username: str = None, email: str = None, name: str = None):
        """Store an identity in SortingHat.

        :param username: The username of the identity.
        :param email: The email of the identity.
        :param name: The name of the identity.
        """
        try:
            # TODO: add lru cache or similar to avoid adding the same identity multiple times
            add_identity(self.sh_ctx, self.source, username, email, name)
        except AlreadyExistsError:
            pass
        except Exception as e:
            self.logger.error(f"Error storing identity: {e}")


def find_identities_extractors(top_package_name: str) -> dict[str, type[IdentitiesExtractor]]:
    """Find available identities extractors.

    Look for the `IdentitiesExtractor` classes under `top_package`
    and its sub-packages. When `top_package` defines a namespace,
    classes under that same namespace will be found too.

    :param top_package_name: the top package name where to look for `IdentitiesExtractor` classes.

    :returns: a dict with `IdentitiesExtractor`
    """
    top_package = importlib.import_module(top_package_name)

    candidates = pkgutil.walk_packages(top_package.__path__, prefix=top_package.__name__ + ".")

    modules = [name for _, name, is_pkg in candidates if not is_pkg]

    return _import_extractors(modules)


def _import_extractors(modules):
    for module in modules:
        importlib.import_module(module)

    klasses = _find_classes(IdentitiesExtractor, modules)

    extractors = {kls.event_type: kls for kls in klasses}

    return extractors


def _find_classes(parent, modules):
    parents = parent.__subclasses__()

    while parents:
        kls = parents.pop()

        m = kls.__module__

        if m not in modules:
            continue

        parents.extend(kls.__subclasses__())

        yield kls
