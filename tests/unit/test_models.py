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

from django.db import connection
from django.db.models import CharField

from grimoirelab_toolkit.datetime import datetime_utcnow

from grimoirelab.core.models import MAX_SIZE_CHAR_FIELD, BaseModel

from .base import GrimoireLabTestCase


class BaseModelTest(BaseModel):
    """Class for testing purposes"""

    name = CharField(max_length=MAX_SIZE_CHAR_FIELD)


class TestBaseModel(GrimoireLabTestCase):
    """Unit tests for BaseModel class"""

    def setUp(self):
        def cleanup_test_model():
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(BaseModelTest)

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(BaseModelTest)

        self.addCleanup(cleanup_test_model)
        super().setUp()

    def test_created_at(self):
        """Creation date is set when the object is created"""

        before_dt = datetime_utcnow()
        base = BaseModelTest(name="base test")
        after_dt = datetime_utcnow()

        self.assertGreaterEqual(base.created_at, before_dt)
        self.assertLessEqual(base.created_at, after_dt)

        base.save()

        self.assertGreaterEqual(base.created_at, before_dt)
        self.assertLessEqual(base.created_at, after_dt)

    def test_created_at_not_updated(self):
        """ "Creation date is not updated when the object is modified"""

        before_dt = datetime_utcnow()
        base = BaseModelTest(name="base test")
        base.save()
        after_dt = datetime_utcnow()

        base.save()

        self.assertGreaterEqual(base.created_at, before_dt)
        self.assertLessEqual(base.created_at, after_dt)

    def test_last_modified(self):
        """Last modification date is set when the object is updated"""

        before_dt = datetime_utcnow()
        org = BaseModelTest(name="base test")
        after_dt = datetime_utcnow()

        self.assertGreaterEqual(org.last_modified, before_dt)
        self.assertLessEqual(org.last_modified, after_dt)

        before_modified_dt = datetime_utcnow()
        org.save()
        after_modified_dt = datetime_utcnow()

        self.assertGreaterEqual(org.last_modified, before_modified_dt)
        self.assertLessEqual(org.last_modified, after_modified_dt)
