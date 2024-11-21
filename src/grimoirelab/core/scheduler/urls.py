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


urlpatterns = [
    re_path(r'^add_task', views.add_task),
    path('tasks/', api.EventizerTaskList.as_view()),
    path('tasks/<str:uuid>/', api.EventizerTaskDetail.as_view()),
    path('tasks/<str:task_id>/jobs/', api.EventizerJobList.as_view()),
    path('tasks/<str:task_id>/jobs/<str:uuid>/', api.EventizerJobDetail.as_view()),
    path('tasks/<str:task_id>/jobs/<str:uuid>/logs/', api.EventizerJobLogs.as_view()),
]
