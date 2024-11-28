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

import cloudevents.conversion
import rq.job

import perceval.backend
import perceval.backends
import chronicler.eventizer

from grimoirelab_toolkit.datetime import str_to_datetime

from ...scheduler.errors import NotFoundError

if typing.TYPE_CHECKING:
    from typing import Any
    from datetime import datetime


logger = logging.getLogger(__name__)


def chronicler_job(
    datasource_type: str,
    datasource_category: str,
    events_queue: str,
    job_args: dict[str, Any] = None
) -> ChroniclerProgress:
    """Fetch and eventize data.

    It will fetch data from a software development repository and
    convert it into events. Fetched data and events will be
    published to a Redis queue. The progress of the job can be accessed
    through the property `progress`. The result of the job can be obtained
    accessing to the property `result` of the object.

    Data will be fetched using `perceval` and eventized using
    `chronicler`.

    :param datasource_type: type of the datasource
        (e.g., 'git', 'github')
    :param datasource_category: category of the datasource
        (e.g., 'pull_request', 'issue')
    :param job_args: extra arguments to pass to the job
        (e.g., 'url', 'owner', 'repository')
    """
    rq_job = rq.get_current_job()

    try:
        backends = perceval.backend.find_backends(perceval.backends)[0]
        backend_class = backends[datasource_type]
    except KeyError:
        raise NotFoundError(element=datasource_type)

    backend_args = job_args.copy() if job_args else {}

    # Get the generator to fetch the data items
    perceval_gen = perceval.backend.BackendItemsGenerator(
        backend_class,
        backend_args,
        datasource_category
    )
    progress = ChroniclerProgress(
        rq_job.get_id(),
        datasource_type,
        datasource_category,
        None
    )
    rq_job.progress = progress

    # The chronicler generator will eventize the data items
    # that are fetched by the perceval generator.
    try:
        events = chronicler.eventizer.eventize(datasource_type,
                                               perceval_gen.items)
        for event in events:
            data = cloudevents.conversion.to_json(event)
            rq_job.connection.rpush(events_queue, data)
    finally:
        progress.summary = perceval_gen.summary

    return progress


class ChroniclerProgress:
    """Class to store the progress of a Chronicler job.

    It stores the summary of the job and other useful data
    such as the task and job identifiers, the backend and the
    category of the items generated.

    :param job_id: job identifier
    :param backend: backend used to fetch the items
    :param category: category of the fetched items
    """
    def __init__(self, job_id: str, backend: str, category: str,
                 summary: perceval.backend.Summary | None = None) -> None:
        self.job_id = job_id
        self.backend = backend
        self.category = category
        self.summary = summary

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ChroniclerProgress:
        """Create a new instance from a dictionary."""

        def convert_to_datetime(dt: str) -> datetime | None:
            return str_to_datetime(dt) if dt else None

        data_summary = data['summary']

        if data_summary:
            summary = perceval.backend.Summary()
            summary.fetched = data_summary['fetched']
            summary.skipped = data_summary['skipped']
            summary.min_updated_on = convert_to_datetime(data_summary['min_updated_on'])
            summary.max_updated_on = convert_to_datetime(data_summary['max_updated_on'])
            summary.last_updated_on = convert_to_datetime(data_summary['last_updated_on'])
            summary.last_uuid = data_summary['last_uuid']
            summary.min_offset = data_summary['min_offset']
            summary.max_offset = data_summary['max_offset']
            summary.last_offset = data_summary['last_offset']
            summary.extras = data_summary['extras']
        else:
            summary = None

        return cls(
            data['job_id'],
            data['backend'],
            data['category'],
            summary=summary
        )

    def to_dict(self) -> dict[str, str | int]:
        """Convert object to a dict."""

        summary = {}

        if self.summary:
            summary['fetched'] = self.summary.fetched
            summary['skipped'] = self.summary.skipped
            summary['last_uuid'] = self.summary.last_uuid
            summary['min_offset'] = self.summary.min_offset
            summary['max_offset'] = self.summary.max_offset
            summary['last_offset'] = self.summary.last_offset
            summary['extras'] = self.summary.extras

            if self.summary.min_updated_on:
                summary['min_updated_on'] = self.summary.min_updated_on.timestamp()
            else:
                summary['min_updated_on'] = None

            if self.summary.max_updated_on:
                summary['max_updated_on'] = self.summary.max_updated_on.timestamp()
            else:
                summary['max_updated_on'] = None

            if self.summary.last_updated_on:
                summary['last_updated_on'] = self.summary.last_updated_on.timestamp()
            else:
                summary['last_updated_on'] = None

        result = {
            'job_id': self.job_id,
            'backend': self.backend,
            'category': self.category,
            'summary': summary
        }

        return result


class ChroniclerArgumentGenerator:
    """Class to generate parameters depending on the backend used.

    This class provides methods to generate parameters for different
    chronicler backends, depending on the situation: new parameters,
    parameters that need to be updated after chronicler run, or parameters
    for the recovery mode then the run failed.
    """
    @staticmethod
    def initial_args(task_args: dict[str, Any]) -> dict[str, Any]:
        """Generate the common parameters for an initial run."""

        return {}

    @staticmethod
    def resuming_args(
        task_args: dict[str, Any],
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """Generate the common parameters for a resuming run."""

        params = {}

        if progress.summary and progress.summary.fetched > 0:
            params['from_date'] = progress.summary.max_updated_on

            if progress.summary.max_offset:
                params['offset'] = progress.summary.max_offset

        return params

    @staticmethod
    def recovery_args(
        task_args: dict[str, Any],
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """Generate the common parameters for a recovery run."""

        return ChroniclerArgumentGenerator.resuming_args(
            task_args, progress
        )


def get_chronicler_argument_generator(name: str) -> ChroniclerArgumentGenerator:
    """Get the argument generator for a backend."""

    generators = {
        'git': GitArgumentGenerator,
        'github': GitHubArgumentGenerator
    }
    return generators.get(name.lower(), ChroniclerArgumentGenerator)


class GitArgumentGenerator(ChroniclerArgumentGenerator):
    """Chronicler argument generator for Git."""

    @staticmethod
    def initial_args(task_args: dict[str, Any]) -> dict[str, Any]:
        """Git initial arguments."""

        import os.path
        from django.conf import settings

        # For the first run, make some arguments mandatory
        base_path = os.path.expanduser(settings.GIT_STORAGE_PATH)
        uri = task_args['uri']
        processed_uri = uri.lstrip('/')
        git_path = os.path.join(base_path, processed_uri) + '-git'

        job_args = {}
        job_args['latest_items'] = False
        job_args['gitpath'] = git_path
        job_args['uri'] = uri

        return job_args

    @staticmethod
    def resuming_args(
        task_args: dict[str, Any] | None,
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """Git resuming arguments."""

        job_args = task_args.copy() if task_args else {}
        job_args['latest_items'] = True

        if 'recovery_commit' in job_args:
            del job_args['recovery_commit']

        return job_args

    @staticmethod
    def recovery_args(
        task_args: dict[str, Any] | None,
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """Git recovery arguments."""

        job_args = task_args.copy() if task_args else {}

        if progress.summary and progress.summary.last_offset:
            job_args['recovery_commit'] = progress.summary.last_offset
            job_args['latest_items'] = False
        elif progress.summary:
            job_args['latest_items'] = True
        else:
            # Something went wrong on the side of the worker.
            # The only thing we can do is to start over,
            # without retrieving the latest items.
            job_args['latest_items'] = False

        return job_args


class GitHubArgumentGenerator(ChroniclerArgumentGenerator):
    """Chronicler argument generator for GitHub."""

    @staticmethod
    def initial_args(task_args: dict[str, Any]) -> dict[str, Any]:
        """GitHub initial arguments."""

        # For the first execution make some arguments mandatory
        job_args = {}
        job_args['owner'] = task_args['owner']
        job_args['repository'] = task_args['repository']

        tokens = task_args.get('api_token', [])

        if not isinstance(tokens, list):
            tokens = [tokens]

        job_args['api_token'] = tokens
        job_args['sleep_for_rate'] = True

    @staticmethod
    def resuming_args(
        task_args: dict[str, Any] | None,
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """GitHub resuming arguments."""

        job_args = task_args.copy() if task_args else {}
        job_args['sleep_for_rate'] = True
        job_args['from_date'] = progress.summary.last_updated_on

        return job_args

    @staticmethod
    def recovery_args(
        task_args: dict[str, Any],
        progress: ChroniclerProgress,
    ) -> dict[str, Any]:
        """GitHub recovery arguments."""

        job_args = task_args.copy() if task_args else {}

        if progress.summary and progress.summary.last_updated_on:
            job_args['from_date'] = progress.summary.last_updated_on

        return job_args


class GitLabArgumentGenerator(GitHubArgumentGenerator):
    """Chronicler argument generator for GitLab."""

    pass
