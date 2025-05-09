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

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.conf import settings

from .scheduler import (
    cancel_task as scheduler_cancel_task,
    schedule_task,
    reschedule_task as scheduler_reschedule_task
)
from ..permissions import check_permissions


@api_view(['POST'])
@check_permissions(['tasks.add_eventizertask'])
def add_task(request):
    """Create a Task to fetch items

    The body should contain a JSON similar to:
    {
        'type': 'eventizer',
        'task_args': {
            'datasource_type': 'git',
            'datasource_category': 'commit',
            'backend_args': {
                'uri': 'https://github.com/chaoss/grimoirelab.git'
            }
        },
        'scheduler': {
            'job_interval': 86400,
            'job_max_retries': 3
        }
    }
    """
    data = request.data

    task_type = data['type']

    job_interval = settings.GRIMOIRELAB_JOB_INTERVAL
    job_max_retries = settings.GRIMOIRELAB_JOB_MAX_RETRIES

    if 'scheduler' in data:
        job_interval = data['scheduler'].get('job_interval', job_interval)
        job_max_retries = data['scheduler'].get('job_max_retries', job_max_retries)

    task_args = data['task_args']['backend_args']

    task = schedule_task(
        task_type, task_args,
        datasource_type=data['task_args']['datasource_type'],
        datasource_category=data['task_args']['datasource_category'],
        job_interval=job_interval,
        job_max_retries=job_max_retries
    )

    response = {
        'status': 'ok',
        'message': f"Task {task.id} added correctly"
    }
    return Response(response, status=200)


@api_view(['POST'])
@check_permissions(['tasks.change_eventizertask'])
def reschedule_task(request):
    """Reschedule a Task

    The body should contain the task id to reschedule:
    {
        'taskId': 'task_id'
    }
    """
    data = request.data
    task_id = data['taskId']

    scheduler_reschedule_task(task_id)

    response = {
        'status': 'ok',
        'message': f"Task {task_id} rescheduled correctly"
    }
    return Response(response, status=200)


@api_view(['POST'])
@check_permissions(['tasks.delete_eventizertask'])
def cancel_task(request):
    """Cancel a Task

    The body should contain the task id to cancel:
    {
        'taskId': 'task_id'
    }
    """
    data = request.data
    task_id = data['taskId']

    scheduler_cancel_task(task_id)

    response = {
        'status': 'ok',
        'message': f"Task {task_id} canceled correctly"
    }
    return Response(response, status=200)
