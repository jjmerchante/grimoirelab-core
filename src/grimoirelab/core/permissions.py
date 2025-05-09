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

from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.response import Response


class IsAuthenticated(BasePermission):
    """
    Allows access only to authenticated users.
    When `GRIMOIRELAB_AUTHENTICATION_REQUIRED` setting is False it always has permissions.
    """
    def has_permission(self, request, view):
        if not settings.GRIMOIRELAB_AUTHENTICATION_REQUIRED:
            return True

        return bool(request.user and request.user.is_authenticated)


def check_permissions(permissions):
    """
    Decorator to check if the user has the given permissions.
    This only works for RestFramework views.
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            if not settings.GRIMOIRELAB_AUTHENTICATION_REQUIRED:
                return func(request, *args, **kwargs)
            if not request.user or not request.user.has_perms(permissions):
                return Response({'message': 'You do not have permission to perform this action.'}, status=403)
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
