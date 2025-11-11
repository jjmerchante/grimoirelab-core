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

import django_rq

from rest_framework import (
    pagination,
    response,
    serializers,
)

from .models import SchedulerStatus
from .tasks.models import EventizerTask, SortingHatTask


class SchedulerPaginator(pagination.PageNumberPagination):
    page_size = 25
    page_size_query_param = "size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return response.Response(
            {
                "links": {"next": self.get_next_link(), "previous": self.get_previous_link()},
                "count": self.page.paginator.count,
                "page": self.page.number,
                "total_pages": self.page.paginator.num_pages,
                "results": data,
            }
        )


class TaskSerializerMixin(serializers.ModelSerializer):
    """
    Serializer mixin for Task models to be used for get and create views of tasks.

    Subclasses should define the `model` in Meta and can extend the `fields` list
    and create_scheduler_task_args() method as needed.
    """

    uuid = serializers.CharField(read_only=True)
    status = serializers.CharField(source="get_status_display", read_only=True)
    runs = serializers.IntegerField(read_only=True)
    failures = serializers.IntegerField(read_only=True)
    last_run = serializers.DateTimeField(read_only=True)
    scheduled_at = serializers.DateTimeField(read_only=True)
    last_jobs = serializers.SerializerMethodField(read_only=True)
    task_args = serializers.JSONField(required=True)
    job_max_retries = serializers.IntegerField(required=False)
    job_interval = serializers.IntegerField(required=False)
    burst = serializers.BooleanField(required=False)

    class Meta:
        model = None
        fields = [
            "uuid",
            "status",
            "runs",
            "failures",
            "last_run",
            "job_interval",
            "scheduled_at",
            "job_max_retries",
            "task_args",
            "burst",
            "last_jobs",
        ]

    def get_last_jobs(self, obj):
        jobs = obj.jobs.order_by("-job_num")[:10]
        return JobSummarySerializer(jobs, many=True).data

    def create_scheduler_task_args(self) -> dict:
        keys = ["task_args", "job_interval", "job_max_retries", "burst"]

        task_args = {}
        for key in keys:
            if key in self.validated_data:
                task_args[key] = self.validated_data[key]

        return task_args


class JobSummarySerializer(serializers.Serializer):
    uuid = serializers.CharField()
    job_num = serializers.IntegerField()
    status = serializers.CharField(source="get_status_display")
    scheduled_at = serializers.DateTimeField(allow_null=True)
    started_at = serializers.DateTimeField(allow_null=True)
    finished_at = serializers.DateTimeField(allow_null=True)

    class Meta:
        fields = [
            "uuid",
            "job_num",
            "status",
            "scheduled_at",
            "started_at",
            "finished_at",
            "queue",
        ]


class JobSerializer(JobSummarySerializer):
    progress = serializers.SerializerMethodField()

    class Meta:
        fields = JobSummarySerializer.Meta.fields + [
            "progress",
        ]

    def get_progress(self, obj):
        if obj.status == SchedulerStatus.RUNNING:
            rq_job = django_rq.get_queue(obj.queue).fetch_job(obj.uuid)
            if rq_job:
                return rq_job.progress.to_dict()
        return obj.progress


class JobLogsSerializer(serializers.Serializer):
    uuid = serializers.CharField()
    status = serializers.CharField(source="get_status_display")
    logs = serializers.SerializerMethodField()

    class Meta:
        fields = [
            "uuid",
            "status",
            "logs",
        ]

    def get_logs(self, obj):
        if obj.status == SchedulerStatus.RUNNING:
            rq_job = django_rq.get_queue(obj.queue).fetch_job(obj.uuid)
            if rq_job:
                return rq_job.job_log
        return obj.logs


class EventizerTaskSerializer(TaskSerializerMixin):
    class Meta:
        model = EventizerTask
        fields = TaskSerializerMixin.Meta.fields + [
            "datasource_type",
            "datasource_category",
        ]

    def create_scheduler_task_args(self):
        task_args = super().create_scheduler_task_args()
        task_args["task_type"] = EventizerTask.TASK_TYPE
        task_args["datasource_type"] = self.validated_data["datasource_type"]
        task_args["datasource_category"] = self.validated_data["datasource_category"]
        return task_args


class SortingHatTaskSerializer(TaskSerializerMixin):
    class Meta:
        model = SortingHatTask
        fields = TaskSerializerMixin.Meta.fields + [
            "job_type",
        ]

    def create_scheduler_task_args(self):
        task_args = super().create_scheduler_task_args()
        task_args["task_type"] = SortingHatTask.TASK_TYPE
        task_args["job_type"] = self.validated_data["job_type"]
        return task_args
