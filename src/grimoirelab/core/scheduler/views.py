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

import pickle

import django_rq
from django.http import JsonResponse
from rq.job import Job

from .scheduler import schedule_task
from .common import Q_DEFAULT_JOBS


def create_job(request):
    backend = 'git'
    category = 'commit'
    backend_args = {
        "gitpath": "/tmp/git/arthur.git/",
        "uri": "https://github.com/chaoss/grimoirelab-kingarthur.git",
        "from_date": "2015-03-01"
    }

    task = schedule_task(backend=backend,
                         category=category,
                         backend_args=backend_args)

    return JsonResponse({'task': task.task_id})


def list_jobs(request):
    queue = django_rq.get_queue(Q_DEFAULT_JOBS)
    connection = queue.connection

    def job_info(jid):
        job = Job.fetch(id=jid, connection=connection)
        return job.exc_info

    def job_sched_info(jid):
        job = Job.fetch(id=jid, connection=connection)
        return job.kwargs

    def job_result(jid):
        job = Job.fetch(id=jid, connection=connection)
        data = job.to_dict()
        data['data'] = pickle.loads(job.data)
        data['result'] = job.result.to_dict()
        data['meta'] = job.meta
        return data

    out = {
        'started': {jid: job_info(jid) for jid in queue.started_job_registry.get_job_ids()},
        'scheduled': {jid: job_sched_info(jid) for jid in queue.scheduled_job_registry.get_job_ids()},
        'failed': {jid: job_info(jid) for jid in queue.failed_job_registry.get_job_ids()},
        'deferred': {jid: job_info(jid) for jid in queue.deferred_job_registry.get_job_ids()},
        'canceled': {jid: job_info(jid) for jid in queue.canceled_job_registry.get_job_ids()},
        'finished': {jid: job_result(jid) for jid in queue.finished_job_registry.get_job_ids()},
    }

    return JsonResponse(out)


def clear_jobs(request):
    queue = django_rq.get_queue(Q_DEFAULT_JOBS)

    registries = [
        queue.failed_job_registry,
        queue.finished_job_registry,
        queue.scheduled_job_registry,
        queue.started_job_registry,
        queue.canceled_job_registry,
        queue.deferred_job_registry
    ]
    for registry in registries:
        for jid in registry.get_job_ids():
            registry.remove(jid)

    return JsonResponse({'removed': True})
