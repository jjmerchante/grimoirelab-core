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

## Usage

```
$ grimoirelab
Usage: grimoirelab [OPTIONS] COMMAND [ARGS]...

  CHAOSS toolset for software development analytics

Options:
  --help  Show this message and exit.

Commands:
  config      GrimoireLab administration tool.
  fetch-task  Scheduler commands.
  queues      Manage the GrimoireLab Redis queues
  run         Run a service.
```

## Configuration

The first step is to run a Redis server and a MySQL database that will be used
for communicating components and storing results. Please refer to their
documentation to know how to install and run them both.

#### Configure the database
```
grimoirelab config setup
```

#### Run a scheduler worker
```
grimoirelab run scheduler-worker
```

#### Create a Git fetch task
```
grimoirelab fetch-task git https://github.com/chaoss/grimoirelab.git
```

#### Consume items from the queue
```
grimoirelab run test-perceval-consumer
```

### Configuration variables

By default, GrimoireLab runs using a configuration file defined at
`grimoirelab.core.config.settings`. You can update that file or use
environment variables.

## Running tests

GrimoireLab core comes with a comprehensive list of unit tests

```
(.venv)$ ./manage.py test --settings=config.settings.testing
```
