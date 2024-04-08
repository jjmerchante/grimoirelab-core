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
# Authors:
#     Santiago Dueñas <sduenas@bitergia.com>
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import json

import django_rq

from django.conf import settings
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from rq.exceptions import NoSuchJobError
from rq.job import Job

from .errors import NotFoundError
from .jobs import JobResult
from .models import FetchTask
from .scheduler import (schedule_task,
                        remove_task,
                        reschedule_task as scheduler_reschedule_task)


@require_http_methods(["GET"])
def list_tasks(request):
    tasks = FetchTask.objects.all()

    page_number = request.GET.get('page', 1)
    per_page = request.GET.get('per_page', 10)
    paginator = Paginator(tasks, per_page=per_page)
    page_obj = paginator.get_page(page_number)

    serialized_tasks = [
        {
            'id': task.id,
            'backend': task.backend,
            'category': task.category,
            'backend_args': task.backend_args,
            'status': task.get_status_display(),
            'age': task.age,
            'executions': task.executions,
            'num_failures': task.num_failures,
            'jobs': [job.job_id for job in task.jobs.all()],
            'queue': task.queue,
            'scheduled_datetime': task.scheduled_datetime,
            'interval': task.interval,
            'max_retries': task.max_retries,
            'last_execution': task.last_execution,
            'task_id': task.task_id,
        }
        for task in page_obj
    ]

    return JsonResponse({
        'count': paginator.count,
        'num_pages': paginator.num_pages,
        'current_page': page_obj.number,
        'objects': serialized_tasks
    })


@require_http_methods(["GET"])
def show_job(request, job_id):
    connection = django_rq.get_connection()

    try:
        job = Job.fetch(job_id, connection=connection)
    except NoSuchJobError:
        return JsonResponse({'error_message': f'Job {job_id} not found'}, status=404)

    response = {
        "created_at": job.created_at,
        "started_at": job.started_at,
        "ended_at": job.ended_at,
        "worker_name": job.worker_name,
        "queue": job.origin,
        "func_name": job.func_name,
        "args": job.args,
        "kwargs": job.kwargs,
        "enqueued_at": job.enqueued_at,
        "status": job.get_status(),
        "log": None,
        "result": None,
    }
    if 'log' in job.meta:
        response['log'] = job.meta['log']

    if 'result' in job.meta and job.meta['result']:
        response['result'] = job.meta['result'].to_dict()

    return JsonResponse(response)


@require_http_methods(["GET"])
def show_task(request, task_id):
    try:
        task = FetchTask.objects.get(id=task_id)
    except FetchTask.DoesNotExist:
        return JsonResponse({"error": "Task not found."}, status=404)

    connection = django_rq.get_connection()
    num_jobs = request.GET.get('num_jobs', 10)
    jobs = []
    for job in task.jobs.all()[:num_jobs]:
        try:
            job_rq = Job.fetch(job.job_id, connection=connection)
        except NoSuchJobError:
            # TODO: delete job from DB?
            continue

        job_result = None
        if isinstance(job_rq.return_value(), JobResult):
            job_result = job_rq.return_value().to_dict()

        logs = None
        if 'log' in job_rq.meta:
            logs = job_rq.meta['log']

        jobs.append({
            'job_id': job.job_id,
            'job_status': job_rq.get_status(),
            'result': job_result,
            'logs': logs,
        })

    response = {
        'id': task.id,
        'backend': task.backend,
        'category': task.category,
        'backend_args': task.backend_args,
        'status': task.get_status_display(),
        'age': task.age,
        'executions': task.executions,
        'num_failures': task.num_failures,
        'jobs': jobs,
        'queue': task.queue,
        'scheduled_datetime': task.scheduled_datetime,
        'interval': task.interval,
        'max_retries': task.max_retries,
        'last_execution': task.last_execution,
        'task_id': task.task_id,
    }

    return JsonResponse(response)


@require_http_methods(["POST"])
@csrf_exempt
def add_task(request):
    """Create a Task to fetch items

    The body should contain a JSON similar to:
    {
        "taskData": {
            "backend": "git",
            "category": "commit",
            "backendArgs": {
                "uri": "https://github.com/chaoss/grimoirelab.git"
            }
        },
        "schedulerArgs": {
            "interval": 86400,
            "max_retries": 3
        }
    }
    """
    task_args = {}
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    task_data = data['taskData']
    task_args['backend'] = task_data['backend']
    task_args['category'] = task_data['category']
    task_args['backend_args'] = {}
    if task_data['backend'] == 'git':
        task_args['backend_args']['uri'] = task_data['backendArgs']['uri']
        task_args['backend_args']['gitpath'] = settings.GIT_PATH
        if 'fromDate' in task_data['backendArgs']:
            task_args['backend_args']['from_date'] = task_data['backendArgs']['fromDate']

    if 'interval' in data['schedulerArgs']:
        task_args['interval'] = int(data['schedulerArgs']['interval'])
    if 'maxRetries' in data['schedulerArgs']:
        task_args['max_retries'] = int(data['schedulerArgs']['maxRetries'])

    task = schedule_task(**task_args)

    return JsonResponse({'status': 'ok',
                         'message': f"Task {task.id} added correctly"}, safe=False)


@require_http_methods(["POST"])
@csrf_exempt
def delete_task(request):
    task_id = json.loads(request.body)['taskId']

    try:
        remove_task(task_id)
    except NotFoundError:
        err = "Task not found"
        return JsonResponse({'status': 'false', 'message': err}, status=404)
    return JsonResponse({'status': 'ok',
                         'message': "Task removed correctly"}, safe=False)


@require_http_methods(["POST"])
@csrf_exempt
def reschedule_task(request):
    task_id = json.loads(request.body)['taskId']

    try:
        rescheduled = scheduler_reschedule_task(task_id)
    except NotFoundError:
        err = "Task not found"
        return JsonResponse({'status': 'false', 'message': err}, status=404)

    if not rescheduled:
        err = "Error rescheduling the task"
        return JsonResponse({'status': 'false', 'message': err},
                            status=400)
    return JsonResponse({'status': 'ok',
                         'message': "Task rescheduled correctly"})
