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

from django.urls import path, re_path

from . import api
from . import views


datasources_urlpatterns = [
    re_path(r'^add_repository', views.add_repository, name='add_repository'),
    path('repositories/', api.RepositoryList.as_view()),
]

ecosystems_urlpatterns = [
    path('', api.EcosystemList.as_view(), name='ecosystem-list'),
    path('<str:name>/', api.EcosystemDetail.as_view(), name='ecosystem-detail'),
]
