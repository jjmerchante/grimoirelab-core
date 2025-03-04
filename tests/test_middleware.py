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

from django.contrib.auth import get_user_model
from django.test import (
    TestCase,
    RequestFactory,
    Client,
    override_settings
)
from django.http import HttpResponse
from django.urls import path
from rest_framework.decorators import api_view

from grimoirelab.core.middleware import requests_logger


@api_view(['GET'])
def test_view(request):
    return HttpResponse("OK")


urlpatterns = [
    path('test-url', test_view, name='test_view'),
]


@override_settings(ROOT_URLCONF="tests.test_middleware")
class AccessLogMiddlewareTest(TestCase):
    def setUp(self):
        self.client = Client()

        self.factory = RequestFactory()

    def test_access_log_middleware(self):
        """Test if it properly logs the access log"""

        user = get_user_model().objects.create_user(username='testuser', password='testpassword')
        self.client.login(username='testuser', password='testpassword')
        self.client

        with self.assertLogs(logger=requests_logger) as cm:
            r = self.client.get("/test-url", headers={"User-Agent": "test-agent-1"})

            self.assertIn("127.0.0.1", cm.output[0])
            self.assertIn("GET", cm.output[0])
            self.assertIn("/test-url", cm.output[0])
            self.assertIn("200", cm.output[0])
            self.assertIn(f"user_id={user.id}", cm.output[0])
            self.assertIn("user_agent='test-agent-1'", cm.output[0])

    def test_unauthenticated_user(self):
        """Test whether it logs unauthenticated user"""

        with self.assertLogs(logger=requests_logger) as cm:
            r = self.client.get("/test-url", headers={"User-Agent": "test-agent-2"})

            self.assertIn("127.0.0.1", cm.output[0])
            self.assertIn("GET", cm.output[0])
            self.assertIn("/test-url", cm.output[0])
            self.assertIn("403", cm.output[0])
            self.assertIn("user_id=None", cm.output[0])
            self.assertIn("user_agent='test-agent-2'", cm.output[0])

    def test_not_found(self):
        """Test not found error"""

        with self.assertLogs(logger=requests_logger) as cm:
            r = self.client.post("/not-found-url", headers={"User-Agent": "test-agent-2"})

            self.assertIn("127.0.0.1", cm.output[0])
            self.assertIn("POST", cm.output[0])
            self.assertIn("/not-found-url", cm.output[0])
            self.assertIn("404", cm.output[0])
            self.assertIn("user_id=None", cm.output[0])
            self.assertIn("user_agent='test-agent-2'", cm.output[0])
