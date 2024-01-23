# syntax=docker/dockerfile:1.3

# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

FROM python:3.10-bookworm AS base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONFAULTHANDLER 1

WORKDIR /usr/src/app

MAINTAINER Oliver Stolpe <oliver.stolpe@bih-charite.de>
LABEL org.opencontainers.image.source https://github.com/bihealth/hpc-access

RUN apt-get update && apt-get install -y curl
RUN apt-get clean autoclean && \
    apt-get autoremove --yes && \
    rm -rf /var/lib/{apt,dpkg,cache,log}/

# Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /usr/local/bin/wait
RUN chmod +x /usr/local/bin/wait

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

FROM base AS deps

RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends \
        apt-utils \
        gcc \
        ldap-utils \
        libldap2-dev \
        libsasl2-dev \
        make \
        postgresql-client \
        wget \
        xmlsec1

# Copy Pipfile and lock into the Docker image.
COPY Pipfile Pipfile.lock ./

# Install Python dependencies via pipenv.
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install \
        --python=/usr/local/bin/python \
        --categories=packages,prod-packages,dev-packages,ldap-packages \
        --deploy

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------

FROM base AS runtime

COPY --from=deps /usr/src/app/.venv /usr/src/app/.venv

WORKDIR /usr/src/app

ENV PATH="/usr/src/app/.venv/bin:$PATH"
ENV CUSTOM_STATIC_DIR /usr/src/app/local-static

# Temporarily setup environment variables for ``manage.py` commands below.
# We will clear them again later.
ENV DJANGO_SECRET_KEY=for-build-only \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    DATABASE_URL=postgres://hpc-access:hpc-access@fake/hpc-access

# Copy source code
COPY . .

# Download files from CDN.
RUN mkdir -p local-static/local/css && \
    mkdir -p local-static/local/fonts && \
    mkdir -p local-static/local/js && \
    wget -P local-static/local/css \
      https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css \
      https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css.map \
    && \
    wget -P local-static/local/js \
      https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js \
      https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js.map \
      https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.min.js \
      https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.min.js.map \
      https://browser.sentry-cdn.com/6.17.9/bundle.tracing.min.js \
      https://browser.sentry-cdn.com/6.17.9/bundle.tracing.min.js.map \
      https://code.jquery.com/jquery-3.6.0.min.js

# Prepare static files
RUN python manage.py collectstatic --no-input

# Define entrypoint
COPY utils/docker/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["wsgi"]
EXPOSE 8080/tcp
