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

from django.db.models import (
    CharField,
    CASCADE,
    OneToOneField
)

from ..scheduler.tasks.models import EventizerTask
from ..models import BaseModel, MAX_SIZE_CHAR_FIELD


class Repository(BaseModel):
    """Base class for repositories

    A repository is composed of a backend, a category, and a URI.
    Each repository is fetched by a task. The task will be executed
    recurrently.
    """
    uri = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    datasource_type = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    datasource_category = CharField(max_length=MAX_SIZE_CHAR_FIELD)
    task = OneToOneField(EventizerTask, on_delete=CASCADE, related_name="repository", null=True, default=None)

    class Meta:
        unique_together = ['uri', 'datasource_type', 'datasource_category']
