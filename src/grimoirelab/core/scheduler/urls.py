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


tasks_urlpatterns = [
    path("", api.ListTaskTypes.as_view(), name="task-types"),
    path("<str:task_type>/", api.ListCreateTasks.as_view(), name="tasks"),
    path("<str:task_type>/<str:uuid>/", api.RetrieveDestroyTask.as_view(), name="task-detail"),
    path(
        "<str:task_type>/<str:uuid>/reschedule/",
        api.RescheduleTask.as_view(),
        name="task-reschedule",
    ),
    path("<str:task_type>/<str:uuid>/cancel/", api.CancelTask.as_view(), name="task-cancel"),
    path("<str:task_type>/<str:task_id>/jobs/", api.ListJobs.as_view(), name="jobs"),
    path(
        "<str:task_type>/<str:task_id>/jobs/<str:uuid>/", api.JobDetail.as_view(), name="job-detail"
    ),
    path(
        "<str:task_type>/<str:task_id>/jobs/<str:uuid>/logs/",
        api.JobLogs.as_view(),
        name="job-logs",
    ),
]
