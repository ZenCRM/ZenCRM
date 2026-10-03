FROM python:3.11-slim

# Pending Debian security fixes, then system dependencies for WeasyPrint & general utilities
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libjpeg62-turbo \
    libopenjp2-7 \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user and group
RUN groupadd -g 1000 zencrm && \
    useradd -u 1000 -g zencrm -s /bin/sh -d /home/zencrm -m zencrm

WORKDIR /app

# Install Python requirements (pinned), then drop the installers: nothing installs packages at runtime,
# and pip, setuptools and wheel only add vulnerabilities to the image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y pip setuptools wheel

# Declared after the dependency layer so a version bump does not reinstall requirements
ARG ZENCRM_VERSION=0.9.0.4
LABEL org.opencontainers.image.version="${ZENCRM_VERSION}"
ENV ZENCRM_VERSION=${ZENCRM_VERSION}

# Copy all application code
COPY . /app

# Ensure runtime directories exist and are owned by zencrm
RUN mkdir -p /app/instance /app/uploads/branding /app/uploads/avatars /app/generated/offers /app/generated/documents && \
    chown -R zencrm:zencrm /app/instance /app/uploads /app/generated /home/zencrm && \
    chmod +x /app/entrypoint.sh

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
