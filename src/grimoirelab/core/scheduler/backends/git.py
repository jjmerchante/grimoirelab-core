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

from .backend import Backend


class Git(Backend):
    """Git custom methods for the Scheduler"""

    @staticmethod
    def update_backend_args(summary, backend_args):
        """
        Update the arguments for this backend

        :param summary: summary of the PercevalJob
        :param backend_args: backend args for the job
        """

        backend_args["latest_items"] = True

        if "recovery_commit" in backend_args:
            del backend_args["recovery_commit"]

        return backend_args

    @staticmethod
    def recovery_params(summary, backend_args):
        """
        Update the backend arguments for the recovery job.

        :param summary: summary of the PercevalJob
        :param backend_args: backend args for the job
        :return:
        """
        if summary and summary.last_offset:
            backend_args["recovery_commit"] = summary.last_offset
            backend_args["latest_items"] = False
        else:
            backend_args["latest_items"] = True

        return backend_args
