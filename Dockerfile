FROM python:3.11-slim

# System dependencies for WeasyPrint & general utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libjpeg62-turbo \
    libopenjp2-7 \
    libffi-dev \
    fontconfig \
    fonts-dejavu-core \
    libcap2-bin \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -g 1000 zencrm && \
    useradd -u 1000 -g zencrm -s /bin/sh -d /home/zencrm -m zencrm

WORKDIR /app

ARG ZENCRM_VERSION=0.9.0.2
LABEL org.opencontainers.image.version="${ZENCRM_VERSION}"
ENV ZENCRM_VERSION=${ZENCRM_VERSION}

# Install Python requirements (pinned)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Allow python to bind to low ports (< 1024, e.g. port 80) without root
RUN setcap 'cap_net_bind_service=+ep' $(readlink -f $(which python3))

# Copy all application code
COPY . /app

# Ensure runtime directories exist and are owned by zencrm
RUN mkdir -p /app/instance /app/uploads/branding /app/uploads/avatars && \
    chown -R zencrm:zencrm /app /home/zencrm && \
    chmod +x /app/entrypoint.sh

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=80

EXPOSE 80

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
