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

import json

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .scheduler import (
    schedule_task
)


@require_http_methods(["POST"])
@csrf_exempt
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
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

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
    return JsonResponse(response, safe=False)
