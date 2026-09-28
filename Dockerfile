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
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . /app

# Ensure runtime directories exist
RUN mkdir -p /app/instance /app/uploads/branding /app/uploads/avatars

# Make entrypoint script executable
RUN chmod +x /app/entrypoint.sh

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1
ENV PORT=80

EXPOSE 80

ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
