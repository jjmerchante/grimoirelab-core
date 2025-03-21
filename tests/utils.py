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

import json


class RedisStream:
    """Helper class to interact with Redis streams"""

    def __init__(self, redis_connection, stream_name):
        self.redis_connection = redis_connection
        self.stream_name = stream_name

    def create_group(self, group_name):
        self.redis_connection.xgroup_create(self.stream_name, group_name, id="0", mkstream=True)

    def add_entry(self, event, message_id):
        self.redis_connection.xadd(self.stream_name, {b"data": json.dumps(event).encode()}, id=message_id)

    def read_group(self, group_name, consumer_name, total):
        return self.redis_connection.xreadgroup(group_name, consumer_name, {self.stream_name: ">"}, count=total)


def read_file(filename):
    with open(filename, "r") as file:
        return file.read()
