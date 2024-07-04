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

from __future__ import annotations

import os
from typing import Any, TYPE_CHECKING

from django.conf import settings

from .backend import Backend

if TYPE_CHECKING:
    from grimoirelab.core.scheduler.models import FetchTask


class Git(Backend):
    """Backend specific methods for the Scheduler"""

    @staticmethod
    def create_backend_args(task: FetchTask) -> dict[str, Any]:
        """
        Create the arguments for the given task. This is typically
        for the first execution and does not depend on any previous
        execution.

        :param task: object that contains all the information for the task
        :return: a dictionary containing the job arguments
        """
        job_args = Backend.create_backend_args(task)

        # For the first execution make some arguments mandatory
        base_path = os.path.expanduser(settings.GIT_PATH)
        uri = task.backend_args['uri']
        processed_uri = uri.lstrip('/')
        git_path = os.path.join(base_path, processed_uri) + '-git'

        job_args['backend_args']['latest_items'] = False
        job_args['backend_args']['gitpath'] = git_path

        return job_args

    @staticmethod
    def update_backend_args(summary, backend_args):
        """
        Update the arguments for the next execution based on the
        result summary.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        """
        backend_args["latest_items"] = True

        if "recovery_commit" in backend_args:
            del backend_args["recovery_commit"]

        return backend_args

    @staticmethod
    def recovery_params(summary, backend_args):
        """
        Create or update the backend arguments for the recovery job.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        """
        if summary and summary.last_offset:
            backend_args["recovery_commit"] = summary.last_offset
            backend_args["latest_items"] = False
        else:
            backend_args["latest_items"] = True

        return backend_args
