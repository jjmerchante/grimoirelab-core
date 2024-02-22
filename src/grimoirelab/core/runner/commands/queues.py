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
#     Jose Javier Merchante <jjmerchante@bitergia.com>
#

import os

import click
import django_rq
from django.core.wsgi import get_wsgi_application


@click.group()
@click.option('--config', 'cfg', envvar='GRIMOIRELAB_CONFIG',
              help="Config module in Python path syntax,"
                   "e.g. grimoirelab.core.config.settings.")
def queues(cfg: str):
    """Manage the GrimoireLab Redis queues"""

    env = os.environ

    if cfg:
        env['DJANGO_SETTINGS_MODULE'] = cfg
    else:
        raise click.ClickException(
            "Configuration file not given. "
            "Set it with '--config' option "
            "or 'GRIMOIRELAB_CONFIG' env variable."
        )

    _ = get_wsgi_application()


@queues.command(name='list')
def list_jobs():
    queue = django_rq.get_queue()

    jobs = {
        'Started': [jid for jid in queue.started_job_registry.get_job_ids()],
        'Scheduled': [jid for jid in queue.scheduled_job_registry.get_job_ids()],
        'Failed': [jid for jid in queue.failed_job_registry.get_job_ids()],
        'Deferred': [jid for jid in queue.deferred_job_registry.get_job_ids()],
        'Canceled': [jid for jid in queue.canceled_job_registry.get_job_ids()],
        'Finished': [jid for jid in queue.finished_job_registry.get_job_ids()],
    }
    for key, value in jobs.items():
        click.echo(key)
        click.echo(value)
        click.echo()


@queues.command(name='purge')
def remove_jobs():
    queue = django_rq.get_queue()

    registries = {
        'Started': queue.failed_job_registry,
        'Scheduled': queue.finished_job_registry,
        'Failed': queue.scheduled_job_registry,
        'Deferred': queue.started_job_registry,
        'Canceled': queue.canceled_job_registry,
        'Finished': queue.deferred_job_registry
    }
    for key, registry in registries.items():
        for jid in registry.get_job_ids():
            registry.remove(jid)
        click.echo(f"{key} registry removed.")
