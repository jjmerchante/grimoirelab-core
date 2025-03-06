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

import getpass
import logging
import os
import sys
import typing

import click
import django.core
import django_rq

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError

if typing.TYPE_CHECKING:
    from click import Context


logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def admin(ctx: Context):
    """GrimoireLab administration tool.

    This swiss army knife tool allows to run administrative tasks to
    configure, initialize, update, or check the service.
    """
    pass


@admin.command()
def setup():
    """Run initialization tasks to configure GrimoireLab.

    This command will create the database, tables and apply the
    defined migrations and fixtures.
    """
    _setup()


def _setup():
    """Setup GrimoireLab"""

    _create_database()
    _setup_database()
    _install_static_files()

    logger.info("\nGrimoirelab configuration completed")


def _create_database(database: str = 'default', db_name: str | None = None):
    """Create an empty database"""

    import MySQLdb
    from django.conf import settings

    db_params = settings.DATABASES[database]
    db_name = db_name if db_name else db_params['NAME']

    logger.info("## GrimoireLab database creation\n")

    try:
        cursor = MySQLdb.connect(
            user=db_params['USER'],
            password=db_params['PASSWORD'],
            host=db_params['HOST'],
            port=int(db_params['PORT'])
        ).cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {db_name} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_520_ci;"
        )
    except MySQLdb.DatabaseError as exc:
        msg = f"Error creating database '{db_name}' for '{database}': {exc}."
        raise click.ClickException(msg)

    logger.info(f"GrimoireLab database '{db_name}' for '{database}' created.\n")


def _setup_database(database: str = 'default'):
    """Apply migrations and fixtures to the database"""

    click.secho(f"## GrimoireLab database setup for {database}\n",
                fg='bright_cyan')

    django.core.management.call_command('migrate', database=database)


def _install_static_files():
    """Collect static files and install them."""

    click.secho('## GrimoireLab static files installation\n',
                fg='bright_cyan')

    django.core.management.call_command('collectstatic',
                                        ignore=['admin', 'rest_framework'],
                                        clear=True,
                                        interactive=False)


@admin.command()
@click.option('--username', help="Specifies the login for the user.")
@click.option('--is-admin', is_flag=True, default=False,
              help="Specifies if the user is superuser.")
@click.option('--no-interactive', is_flag=True, default=False,
              help="Run the command in no interactive mode.")
def create_user(username, is_admin, no_interactive):
    """Create a new user given a username and password"""

    try:
        if no_interactive:
            # Use password from environment variable, if provided.
            password = os.environ.get('GRIMOIRELAB_USER_PASSWORD')
            if not password or not password.strip():
                raise click.ClickException("Password cannot be empty.")
            # Use username from environment variable, if not provided in options.
            if username is None:
                username = os.environ.get('GRIMOIRELAB_USER_USERNAME')
            error = _validate_username(username)
            if error:
                click.ClickException(error)
        else:
            # Get username
            if username is None:
                username = input("Username: ")
            error = _validate_username(username)
            if error:
                click.ClickException(error)
            # Prompt for a password
            password = getpass.getpass()
            password2 = getpass.getpass('Password (again): ')
            if password != password2:
                raise click.ClickException("Error: Your passwords didn't match.")
            if password.strip() == '':
                raise click.ClickException("Error: Blank passwords aren't allowed.")

        extra_fields = {}
        if is_admin:
            extra_fields['is_staff'] = True
            extra_fields['is_superuser'] = True

        get_user_model().objects.create_user(username=username,
                                             password=password,
                                             **extra_fields)

        logger.info("User created successfully.")
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled.")
        sys.exit(1)
    except IntegrityError:
        logger.warning(f"User '{username}' already exists.")
        sys.exit(1)


def _validate_username(username):
    """Check if the username is valid and return the error"""

    if not username:
        return "Username cannot be empty."
    username_field = get_user_model()._meta.get_field(get_user_model().USERNAME_FIELD)
    try:
        username_field.clean(username, None)
    except ValidationError as e:
        return '; '.join(e.messages)


@admin.group()
@click.pass_context
def queues(ctx: Context):
    """Manage the GrimoireLab job queues."""

    pass


@queues.command(name='list')
def list_jobs():
    """List the jobs in the queues.

    Print the jobs classified by their status.
    """
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
        logger.info(key)
        logger.info(value)
        logger.info("")


@queues.command(name='purge')
def remove_jobs():
    """Remove the jobs from the queues."""

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
        logger.info(f"{key} registry removed.")
