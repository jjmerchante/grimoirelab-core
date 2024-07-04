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
from typing import Any, TYPE_CHECKING

from .backend import Backend


if TYPE_CHECKING:
    from grimoirelab.core.scheduler.models import FetchTask


class GitLab(Backend):
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

        tokens = job_args['backend_args'].get('api_token')
        # if not tokens:
        #     tokens = list(Token.objects.filter(backend='gitlab').values_list('token', flat=True))
        if not isinstance(tokens, list):
            tokens = [tokens]

        job_args['backend_args']['api_token'] = tokens
        job_args['backend_args']['sleep_for_rate'] = True

        return job_args

    @staticmethod
    def update_backend_args(summary, backend_args):
        """
        Update the arguments for the next execution based on the
        result summary.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        """
        # Include all the tokens available
        # if 'api_token' not in job_args['backend_args']:
        #     tokens = list(Token.objects.filter(backend='gitlab').values_list('token', flat=True))
        #     job_args['backend_args']['api_token'] = tokens

        backend_args['sleep_for_rate'] = True
        backend_args['from_date'] = summary.last_updated_on

        return backend_args

    @staticmethod
    def recovery_params(summary, backend_args):
        """
        Create or update the backend arguments for the recovery job.

        :param summary: summary of the PercevalJob
        :param backend_args: backend arguments for the job
        """
        # Include all the tokens available
        # if 'api_token' not in job_args['backend_args']:
        #     tokens = list(Token.objects.filter(backend='gitlab').values_list('token', flat=True))
        #     job_args['backend_args']['api_token'] = tokens

        if summary and summary.last_updated_on:
            backend_args["from_date"] = summary.last_updated_on

        return backend_args
