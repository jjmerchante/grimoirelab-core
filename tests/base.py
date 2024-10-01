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

from django.test import TransactionTestCase

from fakeredis import FakeStrictRedis


class GrimoireLabTestCase(TransactionTestCase):
    """Base class to build tests for GrimoireLab Core.

    This class contains all necessary to build tests cases for
    GrimoireLab Core.

    It's a subclass of Django's TransactionTestCase that helps
    to run tests with database transactions. Also, it provides
    a Redis mock connection to run tests with a Redis database.
    """
    conn = None

    @classmethod
    def setUpClass(cls):
        cls.conn = FakeStrictRedis()

    @classmethod
    def tearDownClass(cls):
        pass

    def setUp(self):
        self.conn.flushdb()

    def tearDown(self):
        self.conn.flushdb()
