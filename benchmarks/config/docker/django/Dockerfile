FROM python:3.12-slim-bookworm as debian

FROM debian as debian-build-stage

WORKDIR /opt/app/

ENV DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y python3-pip git

COPY ./benchmarks/requirements.txt ./requirements.txt

RUN pip wheel --wheel-dir /usr/src/app/wheels -r requirements.txt

##---------------------------------------------------------------
FROM debian as debian-run-stage

ENV APP_HOME=/app/src
WORKDIR $APP_HOME

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBIAN_FRONTEND=noninteractive

COPY --from=debian-build-stage /usr/src/app/wheels /wheels/

RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
    && rm -rf /wheels/

COPY ./src /xinclude
COPY ./pyproject.toml /xinclude
COPY ./README.rst /xinclude
RUN pip install /xinclude  # django-xinclude from pyproject.toml

# Retain shell history in the container
RUN SNIPPET="export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.bash_history" \
    && echo "$SNIPPET" >> "/root/.bashrc"

RUN mkdir -p /var/opt/app/static/
RUN mkdir -p /var/opt/app/media/

COPY ./benchmarks/config/docker/django/entrypoint.sh /entrypoint.sh
