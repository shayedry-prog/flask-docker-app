# ---------- Base image ----------
FROM python:3.12-slim

# Don't write .pyc files, and flush logs straight to `docker logs`
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ---------- Dependencies ----------
# Copied first so Docker can cache this layer when only app code changes
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- App code ----------
COPY app/ ./app/
COPY wsgi.py .

# Run as a non-root user
RUN useradd --create-home --uid 1000 appuser
USER appuser

# Set at build time by CI so / reports which version is running
ARG APP_VERSION=dev
ENV APP_VERSION=${APP_VERSION}

EXPOSE 8000

# Container reports healthy only when the app can reach the database
HEALTHCHECK --interval=10s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"

# --preload creates tables once, before workers fork
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--preload", "--access-logfile", "-", "wsgi:app"]
