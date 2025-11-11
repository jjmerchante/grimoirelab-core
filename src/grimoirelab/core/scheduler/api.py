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

from django.db.models import (
    F,
    OuterRef,
    Subquery,
)

from rest_framework import (
    filters,
    generics,
    response,
    status,
    views,
)
from rest_framework.exceptions import ValidationError

from .errors import NotFoundError
from .models import SchedulerStatus, get_registered_task_model
from .scheduler import schedule_task, reschedule_task, cancel_task
from .serializers import (
    EventizerTaskSerializer,
    SortingHatTaskSerializer,
    SchedulerPaginator,
    JobSummarySerializer,
    JobSerializer,
    JobLogsSerializer,
)
from .tasks.models import EventizerTask, SortingHatTask


TASKS_SERIALIZERS = {
    EventizerTask.TASK_TYPE: EventizerTaskSerializer,
    SortingHatTask.TASK_TYPE: SortingHatTaskSerializer,
}


class ListTaskTypes(views.APIView):
    """API view to list all registered task types."""

    def get(self, request, *args, **kwargs):
        task_types = list(TASKS_SERIALIZERS.keys())
        return response.Response(task_types, status=200)


class ListCreateTasks(generics.ListCreateAPIView):
    """API view to list all tasks paginated or create a new task."""

    pagination_class = SchedulerPaginator
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        "scheduled_at",
        "last_run",
    ]
    ordering = [F("last_run").desc(nulls_first=True)]

    def get_serializer_class(self):
        task_type = self.kwargs["task_type"]
        try:
            return TASKS_SERIALIZERS[task_type]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

    def get_queryset(self):
        task_type = self.kwargs["task_type"]
        try:
            queryset = get_registered_task_model(task_type)[0].objects.all()
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

        status = self.request.query_params.get("status")
        last_run_status = self.request.query_params.get("last_run_status")
        if status is not None:
            if int(status) == SchedulerStatus.FAILED:
                queryset = queryset.filter(jobs__status=status).distinct()
            else:
                queryset = queryset.filter(status=status)
        if last_run_status is not None:
            annotation = Subquery(
                get_registered_task_model(task_type)[1]
                .objects.filter(task_id=OuterRef("id"), finished_at__isnull=False)
                .order_by("-job_num")
                .values("status")[:1]
            )
            queryset = queryset.annotate(last_run_status=annotation).filter(
                last_run_status=last_run_status
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            task = schedule_task(**serializer.create_scheduler_task_args())
        except Exception as e:
            return response.Response(
                {"detail": f"Error scheduling task: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        data = [f"Task '{task.uuid}' created."]
        return response.Response(data, status=status.HTTP_201_CREATED)


class RetrieveDestroyTask(generics.RetrieveDestroyAPIView):
    """API view to retrieve or delete a specific task."""

    lookup_field = "uuid"

    def get_serializer_class(self):
        task_type = self.kwargs["task_type"]
        try:
            return TASKS_SERIALIZERS[task_type]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

    def get_queryset(self):
        task_type = self.kwargs["task_type"]
        try:
            task_model = get_registered_task_model(task_type)[0]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")
        return task_model.objects.all()


class RescheduleTask(views.APIView):
    """API view to reschedule a specific task."""

    def post(self, request, *args, **kwargs):
        task_id = self.kwargs["uuid"]
        try:
            reschedule_task(task_id)
        except NotFoundError:
            return response.Response(
                {"detail": f"Task with id '{task_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = [f"Task '{task_id}' rescheduled."]
        return response.Response(data, status=200)


class CancelTask(views.APIView):
    """API view to cancel a specific task."""

    def post(self, request, *args, **kwargs):
        task_id = self.kwargs["uuid"]

        cancel_task(task_id)

        data = [f"Task '{task_id}' cancelled."]
        return response.Response(data, status=200)


class ListJobs(generics.ListAPIView):
    """API view to list all jobs paginated for a specific task."""

    serializer_class = JobSummarySerializer
    pagination_class = SchedulerPaginator
    filter_backends = [filters.OrderingFilter]
    ordering_fields = [
        "scheduled_at",
        "last_run",
    ]

    def get_queryset(self):
        task_type = self.kwargs["task_type"]
        task_id = self.kwargs["task_id"]
        try:
            job_model = get_registered_task_model(task_type)[1]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

        queryset = job_model.objects.filter(task__uuid=task_id).order_by("-job_num")

        status = self.request.query_params.get("status")
        if status is not None:
            queryset = queryset.filter(status=status)
        return queryset


class JobDetail(generics.RetrieveAPIView):
    """API view to retrieve detailed information about a specific job task."""

    lookup_field = "uuid"
    serializer_class = JobSerializer
    pagination_class = SchedulerPaginator

    def get_queryset(self):
        task_type = self.kwargs["task_type"]
        task_id = self.kwargs["task_id"]
        try:
            job_model = get_registered_task_model(task_type)[1]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

        return job_model.objects.filter(task__uuid=task_id)


class JobLogs(generics.RetrieveAPIView):
    """API view to retrieve log entries for a specific job task."""

    lookup_field = "uuid"
    serializer_class = JobLogsSerializer

    def get_queryset(self):
        task_type = self.kwargs["task_type"]
        task_id = self.kwargs["task_id"]
        try:
            job_model = get_registered_task_model(task_type)[1]
        except KeyError:
            raise ValidationError(f"Unknown task type: '{task_type}'")

        return job_model.objects.filter(task__uuid=task_id)
