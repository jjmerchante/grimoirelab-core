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
from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.conf import settings
from django.db import IntegrityError, transaction

from .models import Repository
from ..scheduler.scheduler import schedule_task
from ..permissions import check_permissions


@api_view(['POST'])
@check_permissions(['datasources.add_repository'])
def add_repository(request):
    """Create a Repository and start a Task to fetch items

    The body should contain a JSON similar to:
    {
        'uri': "<repository_uri>",
        'datasource_type': 'git',
        'datasource_category': 'commit',
        'scheduler': {
            'job_interval': 86400,
            'job_max_retries': 3,
        }
    }
    """
    data = request.data

    # Get POST data
    job_interval = settings.GRIMOIRELAB_JOB_INTERVAL
    job_max_retries = settings.GRIMOIRELAB_JOB_MAX_RETRIES
    if 'scheduler' in data:
        job_interval = data['scheduler'].get('job_interval', job_interval)
        job_max_retries = data['scheduler'].get('job_max_retries', job_max_retries)

    uri = data.get('uri')
    datasource_type = data.get('datasource_type')
    datasource_category = data.get('datasource_category')
    if not uri or not datasource_type or not datasource_category:
        return Response({"error": "Missing parameters"}, status=400)

    # Create the task and the repository
    try:
        with transaction.atomic():
            repository = Repository.objects.create(uri=uri,
                                                   datasource_type=datasource_type,
                                                   datasource_category=datasource_category)
    except IntegrityError:
        return Response({"error": "Repository already exists"}, status=405)

    task_args = {
        'uri': data['uri']
    }
    task = schedule_task(
        'eventizer', task_args,
        datasource_type=datasource_type,
        datasource_category=datasource_category,
        job_interval=job_interval,
        job_max_retries=job_max_retries
    )
    repository.task = task
    repository.save()

    response = {
        'status': 'ok',
        'task_id': repository.task.uuid,
        'message': f"Repository {uri} added correctly"
    }
    return Response(response)
