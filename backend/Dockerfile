# syntax=docker/dockerfile:1.7
# ────────────────────────────────────────────────────────────────────────────
# Spotter backend image — Django 5 + Gunicorn.
# Small, production-ready, runs as non-root.
# ────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# System deps: build tools for psycopg/timezonefinder wheels; curl for healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps in a separate layer for caching.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy application code.
COPY . .

# Collect static (safe to run at build time; DATABASE_URL not required).
RUN DJANGO_SECRET_KEY=build-time-only \
    DATABASE_URL=sqlite:///tmp/build.sqlite3 \
    python manage.py collectstatic --noinput

# Non-root user for runtime.
RUN useradd --system --home /app --shell /usr/sbin/nologin spotter \
    && chown -R spotter:spotter /app
USER spotter

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:${PORT:-8000}/api/health/" || exit 1

# Entrypoint runs migrations then starts Gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn spotter.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-2} --timeout 60 --access-logfile -"]
