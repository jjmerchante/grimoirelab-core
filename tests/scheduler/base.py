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

from django.test import TestCase
from fakeredis import FakeStrictRedis
from rq import push_connection, pop_connection


class TestBaseRQ(TestCase):
    """Base class to inherit test cases from for RQ"""

    conn = None

    @classmethod
    def setUpClass(cls):
        cls.conn = FakeStrictRedis()
        push_connection(cls.conn)

    @classmethod
    def tearDownClass(cls):
        conn = pop_connection()

    def setUp(self):
        self.conn.flushdb()

    def tearDown(self):
        self.conn.flushdb()
