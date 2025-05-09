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

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import PasswordChangeForm
from rest_framework import permissions
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.response import Response


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def api_login(request):
    username = request.data.get('username')
    password = request.data.get('password')

    if username is None or password is None:
        return Response({'detail': 'Please provide username and password.'}, status=400)

    user = authenticate(request, username=username, password=password)

    if user is None:
        response = {
            'errors': 'Invalid credentials.'
        }
        return Response(response, status=403)
    else:
        login(request, user)
        response = {
            'user': username,
            'isAdmin': user.is_superuser,
        }
        return Response(response)


@api_view(['POST'])
def change_password(request):
    form = PasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        response = {
            'updated': user.username
        }
        return Response(response)
    else:
        response = {
            'errors': form.errors.get_json_data()
        }

        return Response(response, status=400)
