FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        tini \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
COPY requirements-dashboard.txt /tmp/requirements-dashboard.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dashboard.txt && \
    rm /tmp/requirements.txt /tmp/requirements-dashboard.txt

WORKDIR /app
COPY dashboard /app/dashboard

EXPOSE 8080

ENTRYPOINT ["tini", "--", "python", "-m", "dashboard"]
