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

from __future__ import annotations

from typing import Any

import logging

from .jobs import PercevalJob
from .models import FetchTask
from .common import (
    DEFAULT_JOB_INTERVAL,
    MAX_JOB_RETRIES,
    Q_DEFAULT_JOBS
)

logger = logging.getLogger(__name__)


def schedule_task(
        backend: str,
        category: str,
        backend_args: dict[str, Any],
        queue_id: str = Q_DEFAULT_JOBS,
        interval: int = DEFAULT_JOB_INTERVAL,
        max_retries: int = MAX_JOB_RETRIES,
) -> FetchTask:
    """Create a new task and schedule a job for that task"""

    task = FetchTask.objects.create(
        backend=backend,
        category=category,
        backend_args=backend_args,
        queue=queue_id,
        interval=interval,
        max_retries=max_retries,
    )

    PercevalJob.enqueue_job(task=task)

    return task
