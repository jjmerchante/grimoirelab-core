FROM debian:bullseye-slim

LABEL maintainer="Santiago Dueñas <sduenas@bitergia.com>"
LABEL org.opencontainers.image.title="GrimoireLab-core"
LABEL org.opencontainers.image.description="GrimoireLab service"
LABEL org.opencontainers.image.licenses="GPL-3.0+"
LABEL org.opencontainers.image.url="https://chaoss.github.io/grimoirelab/"
LABEL org.opencontainers.image.vendor="GrimoireLab project"
LABEL org.opencontainers.image.authors="sduenas@bitergia.com"
#LABEL org.opencontainers.image.documentation="https://sortinghat.readthedocs.io/"

ENV TERM=xterm-256color

# Create a user an a group
RUN groupadd -r grimoirelab && useradd -r -m -g grimoirelab grimoirelab

# Change apt sources to avoid connection problems
RUN sed -i "s/http:\/\/deb.debian.org/http:\/\/ftp.fr.debian.org/g" /etc/apt/sources.list

# Install base packages
RUN apt-get update && \
    apt-get install -qy \
        --no-install-recommends \
        bash locales sudo \
        tree ccze psmisc \
        unzip \
        ssh ca-certificates \
        dirmngr gnupg \
        curl \
        gcc \
        git git-core \
        python3 python3-dev \
        python3-pip python3-venv \
        libmariadbclient-dev-compat && \
    apt-get purge && \
    apt-get clean && \
    find /var/lib/apt/lists -type f -delete

# Configure locales
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    echo 'LANG="en_US.UTF-8"' > /etc/default/locale && \
    dpkg-reconfigure --frontend=noninteractive locales && \
    update-locale LANG=en_US.UTF-8

ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8
ENV LANG C.UTF-8

# Install GrimoireLab and dependencies
#
# We use a virtual environment because it makes easier
# to find the exact location of the packages installed
# and where the static files are available.
ENV \
    # Disable some unused uWSGI features, saving dependencies
    # Thanks to https://stackoverflow.com/a/25260588/90297
    UWSGI_PROFILE_OVERRIDE=ssl=false;xml=false;routing=false

COPY ./dist/*.whl /tmp/dist/
RUN python3 -m venv /opt/venv/ && \
    . /opt/venv/bin/activate && \
    pip install pip --upgrade && \
    pip install /tmp/dist/*.whl && \
    pip check && \
    rm -rf /tmp/dist

RUN chown -R grimoirelab:grimoirelab /opt/venv

# Add entrypoint
COPY ./docker/entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

USER grimoirelab

ENTRYPOINT ["entrypoint.sh"]
CMD ["grimoirelab"]
