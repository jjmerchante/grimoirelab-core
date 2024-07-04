# Grimoirelab Core Docker Image

This docker image runs a container preinstalled with a certain release of
GrimoireLab core, including all libraries and programs. By default, it runs
the grimoirelab command.

For more information about GrimoireLab, please visit
our [website](https://chaoss.github.io/grimoirelab/).


## How to use this image

### Quickstart 

You can use this image to run grimoirelab core scheduler and some basic
commands. You might need a MySQL and Redis server containers running:

```
docker network create grimoire-net

docker run --rm -d --net grimoire-net --name mysqldb -e 'MYSQL_ROOT_PASSWORD=root' mariadb:latest

docker run --rm -d --net grimoire-net --name redisdb  redis:latest redis-server --appendonly yes
```

#### Configure the database
```
docker run --rm --net grimoire-net \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab config setup
```

#### Run a scheduler worker
```
docker run --rm -d --net grimoire-net --name grimoirelab-worker \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run scheduler-worker
```

#### Run a pool of scheduler workers
```
docker run --rm -d --net grimoire-net --name grimoirelab-workerpool \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run workerpool --num-workers 20
```

#### Run the web server
```
docker run --rm -d --net grimoire-net --name grimoirelab-server \
    --env-file docker/grimoirelab.env -p 8000:8000 \
    grimoirelab/grimoirelab-core \
    grimoirelab run server --dev
```

#### Create a Git fetch task

```
docker run --rm --net grimoire-net \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab fetch-task git https://github.com/chaoss/grimoirelab-perceval.git
```

#### Consume items from the queue
```
docker run --rm --net grimoire-net --name grimoirelab-consumer-1 \
    --env-file docker/grimoirelab.env \
    grimoirelab/grimoirelab-core \
    grimoirelab run test-perceval-consumer
```


## Building the image

The image requires that the `grimoirelab-core` Python package is built and
ready in dist directory. You can build a new package running the next command:

```
poetry build
```

Once the package is ready, to build the image, run `docker build` command from
the repository root directory:

```
docker build -f docker/Dockerfile -t grimoirelab/grimoirelab-core .
```


## License

GrimoireLab is licensed under GNU General Public License (GPL), version 3
or later.

However, this image is based on the [Debian docker image](https://hub.docker.com/_/debian),
Check their [license information](https://www.debian.org/social_contract#guidelines)
for the type of software is contained in this image.
