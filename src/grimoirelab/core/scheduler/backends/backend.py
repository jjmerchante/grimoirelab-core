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


class Backend:
    """Base Class for Scheduler Backends

    This base class implements specific functions for scheduler backends.
    It provides fundamental methods applicable to most backends and should
    be extended for those that require specific functionality.
    """

    @staticmethod
    def update_backend_args(summary, backend_args):
        """
        Update the arguments for this backend

        :param summary: summary of the PercevalJob
        :param backend_args: backend args for the job
        """
        if summary and summary.fetched > 0:
            backend_args["next_from_date"] = summary.max_updated_on.isoformat()

            if summary.max_offset:
                backend_args["next_offset"] = summary.max_offset

        return backend_args

    @staticmethod
    def recovery_params(summary, backend_args):
        """
        Create or update the backend arguments for the recovery job.
        By default, it does the same as create backend args.

        :param summary: summary of the PercevalJob
        :param backend_args: backend args for the job
        :return:
        """

        return Backend.update_backend_args(summary, backend_args)
