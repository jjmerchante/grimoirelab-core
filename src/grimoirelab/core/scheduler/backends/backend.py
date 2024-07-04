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

import copy
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from perceval.backend import Summary
    from grimoirelab.core.scheduler.models import FetchTask


class Backend:
    """Base Class for Scheduler Backends

    This base class implements specific functions for scheduler backends.
    It provides fundamental methods applicable to most backends and should
    be extended for those that require specific functionality.
    """

    @staticmethod
    def create_backend_args(task: FetchTask) -> dict[str, Any]:
        """
        Create the arguments for the given task. This is typically
        for the first execution and does not depend on any previous
        execution.

        :param task: object that contains all the information for the task
        :return: a dictionary containing the job arguments
        """
        job_args = {
            'backend': task.backend,
            'category': task.category,
            'backend_args': copy.deepcopy(task.backend_args)
        }
        return job_args

    @staticmethod
    def update_backend_args(summary: Summary, backend_args: dict):
        """
        Update the arguments for the next execution based on the
        result summary.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        """
        if summary and summary.fetched > 0:
            backend_args["from_date"] = summary.max_updated_on.isoformat()

            if summary.max_offset:
                backend_args["offset"] = summary.max_offset

        return backend_args

    @staticmethod
    def recovery_params(summary: Summary, backend_args: dict):
        """
        Create or update the backend arguments for the recovery job.
        By default, it does the same as update backend args.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        :return:
        """

        return Backend.update_backend_args(summary, backend_args)
