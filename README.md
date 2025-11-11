# GrimoireLab Core

GrimoireLab scheduler to fetch data from software repositories.

The scheduler is a distributed job queue that schedules and executes Perceval.
The platform has one or more workers that will run each Perceval job.

The repositories whose data will be fetched are added to the platform using a
REST API. Then, the server transforms these repositories into Perceval jobs and
schedules them between its job queues.

Workers are waiting for new jobs checking these queues. Workers only execute
a job at a time. When a new job arrives, an idle worker will take and run it.
Once a job is finished, if the result is successful, the server will re-schedule
it to retrieve new data.

By default, items fetched by each job will be published using a Redis queue.

## Requirements

- Python >= 3.11
- Redis database
- MySQL database

You will also need some other libraries for running the tool, you can find the
whole list of dependencies in [pyproject.toml](pyproject.toml) file.


## Installation

There are several ways to install GrimoireLab core on your system: packages or
source code using Poetry or pip.

### mysql_config

Before you install GrimoireLab core you might need to install `mysql_config`
command. If you are using a Debian based distribution, this command can be
found either in `libmysqlclient-dev` or `libmariadbclient-dev` packages
(depending on if you are using MySQL or MariaDB database server). You can
install these packages in your system with the next commands:

* **MySQL**

```
$ apt install libmysqlclient-dev
```

* **MariaDB**

```
$ apt install libmariadbclient-dev-compat
```

### PyPI

GrimoireLab core can be installed using pip, a tool for installing Python
packages. To do it, run the next command:
```
$ pip install grimoirelab-core
```

### Source code

To install from the source code you will need to clone the repository first:
```
$ git clone https://github.com/grimoirelab/grimoirelab-core
$ cd grimoirelab-core
```

Then use pip or Poetry to install the package along with its dependencies.

#### Pip
To install the package from local directory run the following command:
```
$ pip install .
```
In case you are a developer, you should install grimoirelab-core in editable mode:
```
$ pip install -e .
```

#### Poetry
We use [poetry](https://python-poetry.org/) for dependency management and
packaging. You can install it following its [documentation](https://python-poetry.org/docs/#installation).
Once you have installed it, you can install grimoirelab-core and the dependencies
in a project isolated environment using:
```
$ poetry install
```
To spaw a new shell within the virtual environment use:
```
$ poetry shell
```

To build the static files automatically you can install the pre-hook plugin
included in the project. Each time you run `poetry install` or `poetry build`
the static files will be built automatically:
```
$ poetry self add "$PWD/build/poetry-prehook"
```

If you prefer to build the static files manually, you can run:
```
$ poetry run python build/build-ui.py
```

## Usage

```
$ grimoirelab
Usage: grimoirelab [OPTIONS] COMMAND [ARGS]...

  Toolset for software development analytics.

  GrimoireLab is a set of tools and a platform to retrieve, analyze, and
  provide insights about data coming from software development repositories.
  With this command, you'll be able to configure and run its different
  services.

  It requires to pass a configuration file module using the Python path syntax
  (e.g. grimoirelab.core.config.settings). Take into account the configuration
  should be accessible by your PYTHON_PATH. You can also use the environment
  variable GRIMOIRELAB_CONFIG to define the config location.

Options:
  --config TEXT  Configuration module in Python path syntax  [default:
                 grimoirelab.core.config.settings]
  --help         Show this message and exit.

Commands:
  admin  GrimoireLab administration tool.
  run    Run a GrimoireLab service.
```

## Configuration

The first step is to run a Redis server, a MySQL database and an OpenSearch
container that will be used for communicating components and storing results.
Please refer to their documentation to know how to install and run them.

### Configuration variables

By default, GrimoireLab runs using a configuration file defined at
`grimoirelab.core.config.settings`. You can update that file or use
environment variables to override the default values.

#### Configure the database

This command will create the database tables and the initial admin user.

```
grimoirelab admin setup
```

#### Run eventizer workers

Run the eventizer workers that will fetch data from the repositories
and insert it into a Redis Stream.

```
grimoirelab run eventizers
```

#### Run archivist workers

Run the archivist workers that will read data from the Redis Stream and
store it into OpenSearch.

```
grimoirelab run archivists
```

### Run identities storage workers

Run the identities storage workers that will read data from the Redis Stream
and store it into SortingHat database.

```
grimoirelab run ushers
```

### Run SortingHat workers

Run the SortingHat workers that will run jobs related to identities management.
Like affiliate, unify, genderize, recommendations and identities importers.

```
grimoirelab run sortinghat-workers
```

#### Run the backend API

Run the backend API server that will provide a REST API to manage the
repositories, jobs and identities.

It also provides a web interface to manage the platform.

```
grimoirelab run server --dev
```

## Running tests

GrimoireLab core comes with a comprehensive list of unit and integration tests.

- Unitary tests requires a SQL database running (MySQL or MariaDB).

- Integration tests uses testcontainers to spawn temporary containers (MariaDB,
Valkey, and OpenSearch).

```
(.venv)$ pytest
```

Set the environment variable `GRIMOIRELAB_TESTING_VERBOSE` to activate the
verbose mode.
