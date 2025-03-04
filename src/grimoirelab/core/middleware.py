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

import logging
import time
import typing

requests_logger = logging.getLogger("grimoirelab.requests")


if typing.TYPE_CHECKING:
    from django.http import HttpRequest, HttpResponse
    from typing import Callable


def _create_api_access_log(
    request: HttpRequest,
    response: HttpResponse,
    start_time: float
) -> str:
    """Create a log entry to be used for api metrics gathering"""

    try:
        user = getattr(request, 'user', None)
        user_id = str(getattr(user, 'id', None))
        frontend_request = bool(request.COOKIES) and 'Authentication' not in request.headers
        caller_ip = str(request.META.get("REMOTE_ADDR"))
        user_agent = str(request.META.get("HTTP_USER_AGENT"))
        response_time_ms = (time.time() - start_time) / 1000

        message = (
            f"{caller_ip} - - {str(request.method)} {request.get_full_path()} {response.status_code} => "
            f"{len(response.content)} bytes in {response_time_ms:.2f} ms. "
            f"user_id={user_id} "
            f"is_frontend_request={frontend_request} "
            f"user_agent='{user_agent}' "
        )
    except Exception as e:
        message = f"Error capturing API access logs: {e}"

    return message


def requests_log_middleware(
        get_response: Callable[[HttpRequest], HttpResponse]
) -> Callable[[HttpRequest], HttpResponse]:

    def middleware(request: HttpRequest):
        request_start_request = time.time()

        response = get_response(request)

        message = _create_api_access_log(request, response, request_start_request)
        requests_logger.info(message)

        return response

    return middleware
