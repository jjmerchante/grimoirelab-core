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

CODE_BASE_ERROR = 1
CODE_ALREADY_EXISTS_ERROR = 2
CODE_NOT_FOUND_ERROR = 9
CODE_VALUE_ERROR = 10
CODE_TASK_REGISTRY_ERROR = 100


class BaseError(Exception):
    """Base class for GrimoireLab exceptions.

    Derived classes can overwrite the error message declaring ``message``
    property.
    """
    code = CODE_BASE_ERROR
    message = "GrimoireLab core unknown error"

    def __init__(self, **kwargs):
        super().__init__()
        self.msg = self.message % kwargs

    def __str__(self):
        return self.msg

    def __int__(self):
        return self.code


class AlreadyExistsError(BaseError):
    """Exception raised when an element already exists"""

    code = CODE_ALREADY_EXISTS_ERROR
    message = "%(element)s already exists"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.element = kwargs['element']


class NotFoundError(BaseError):
    """Exception raised when an element is not found"""

    code = CODE_NOT_FOUND_ERROR
    message = "%(element)s not found"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.element = kwargs['element']


class TaskRegistryError(BaseError):
    """Generic error for TaskRegistry"""

    code = CODE_TASK_REGISTRY_ERROR
    message = "%(cause)s"


class InvalidValueError(BaseError):
    """Exception raised when a value is invalid"""

    code = CODE_VALUE_ERROR
    message = "%(msg)s"
