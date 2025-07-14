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

from django.urls import path

from . import api


ecosystems_urlpatterns = [
    path("", api.EcosystemList.as_view(), name="ecosystem-list"),
    path("<str:name>/", api.EcosystemDetail.as_view(), name="ecosystem-detail"),
    path("<str:ecosystem_name>/projects/", api.ProjectList.as_view(), name="projects-list"),
    path(
        "<str:ecosystem_name>/projects/<str:name>",
        api.ProjectDetail.as_view(),
        name="projects-detail",
    ),
    path(
        "<str:ecosystem_name>/projects/<str:project_name>/children/",
        api.ProjectChildrenList.as_view(),
        name="children-list",
    ),
    path(
        "<str:ecosystem_name>/projects/<str:project_name>/repos/",
        api.RepoList.as_view(),
        name="repo-list",
    ),
    path(
        "<str:ecosystem_name>/projects/<str:project_name>/repos/<str:uuid>/",
        api.RepoDetail.as_view(),
        name="repo-detail",
    ),
    path(
        "<str:ecosystem_name>/projects/<str:project_name>/repos/<str:uuid>/categories/<str:category>/",
        api.CategoryDetail.as_view(),
        name="category-detail",
    ),
]
