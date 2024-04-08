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
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

from .backend import Backend
from .git import Git
from .github import GitHub
from .gitlab import GitLab


def get_scheduler_backend(backend: str):
    backend = backend.lower()
    # TODO: Move this to a global?
    connectors = {
        "git": Git,
        "github": GitHub,
        "gitlab": GitLab
    }

    try:
        return connectors[backend]
    except KeyError:
        return Backend
