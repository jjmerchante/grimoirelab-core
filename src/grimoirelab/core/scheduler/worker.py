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

from __future__ import annotations

import logging
import typing

import django.db.transaction
import rq.worker

from .db import find_job
from .models import SchedulerStatus

if typing.TYPE_CHECKING:
    from .jobs import GrimoireLabJob


logger = logging.getLogger(__name__)


class GrimoireLabWorker(rq.worker.Worker):
    """Worker to run GrimoireLab jobs.

    This class includes some extra functionality to run GrimoireLab
    jobs, like for example, update Job status on models.
    """
    def prepare_job_execution(self, job: GrimoireLabJob, remove_from_intermediate_queue: bool = False):
        """Performs bookkeeping like updating states prior to job execution."""

        super().prepare_job_execution(job, remove_from_intermediate_queue)

        job_db = find_job(job.id)

        with django.db.transaction.atomic():
            job_db.status = SchedulerStatus.RUNNING
            job_db.save()
            job_db.task.status = SchedulerStatus.RUNNING
            job_db.task.save()
