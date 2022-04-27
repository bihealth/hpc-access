FROM python:3.10-buster

MAINTAINER Oliver Stolpe <oliver.stolpe@bih-charite.de>
LABEL org.opencontainers.image.source https://github.com/bihealth/hpc-access

ARG app_git_url=https://github.com/bihealth/hpc-access.git
ARG app_git_tag
ARG app_git_depth=1

ENV DEBIAN_FRONTEND noninteractive
ENV CUSTOM_STATIC_DIR /usr/src/app/local-static
ENV DJANGO_ADMIN_URL for-build-only
ENV DJANGO_SECRET_KEY for-build-only
ENV DJANGO_SETTINGS_MODULE config.settings.production
ENV DATABASE_URL postgres://hpcaccess:hpcaccess@fake/varfish

## Add the wait script to the image
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.7.3/wait /usr/local/bin/wait
RUN chmod +x /usr/local/bin/wait

# Copy source code into Docker image.
RUN mkdir -p /usr/src
RUN git clone --depth $app_git_depth --branch $app_git_tag $app_git_url /usr/src/app

# Install system dependencies.
RUN apt-get update && \
    apt-get install -y \
        apt-utils \
        gcc \
        ldap-utils \
        libldap2-dev \
        libsasl2-dev \
        make \
        postgresql-client \
        wget \
        xmlsec1

# Install Python dependencies.
RUN cd /usr/src/app && \
    pip install --no-cache-dir -r requirements/production.txt && \
    pip install --no-cache-dir -r requirements/local.txt && \
    pip install --no-cache-dir -r requirements/ldap.txt

# Build sphinx manual.
#RUN cd /usr/src/app/docs && \
#    make clean html

# Install modern nodejs
RUN curl -sL https://deb.nodesource.com/setup_12.x | bash - && \
    apt install nodejs

# Install npm dependencies.
#RUN cd /usr/src/app/hpc-access/vueapp && \
#    npm ci && \
#    npm run build

# Download files from CDN.
RUN mkdir -p /usr/src/app/local-static/local/css && \
    mkdir -p /usr/src/app/local-static/local/fonts && \
    mkdir -p /usr/src/app/local-static/local/js && \
    cd /usr/src/app/local-static/local/css && \
    wget https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/css/bootstrap.min.css && \
    cd /usr/src/app/local-static/local/js && \
    wget \
      https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js \
      https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.1.3/js/bootstrap.min.js \
      https://browser.sentry-cdn.com/6.17.9/bundle.tracing.min.js \
      https://code.jquery.com/jquery-3.6.0.min.js

# Get icons
#RUN cd /usr/src/app && \
#    DJANGO_ADMIN_URL=for-build-only \
#    DJANGO_SECRET_KEY=for-build-only \
#    DJANGO_SETTINGS_MODULE=config.settings.production \
#    DATABASE_URL=postgres://hpcaccess:hpcaccess@fake/sodar \
#    python manage.py geticons -c

# Prepare static files
#    mkdir -p /usr/src/app/hpc-access/vueapp/dist && \
RUN cd /usr/src/app && python manage.py collectstatic --no-input

# Define the entry point.
COPY docker-entrypoint.sh /usr/local/bin
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
    ln -s /usr/local/bin/docker-entrypoint.sh / # backwards compat
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["wsgi"]
EXPOSE 8080/tcp
