FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        cron \
        pandoc \
        procps \
        tini \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -d /home/node -s /bin/bash -u 1000 node

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

COPY docker/crontab /etc/cron.d/job-automation
RUN chmod 0644 /etc/cron.d/job-automation

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /home/node

ENTRYPOINT ["tini", "--", "/usr/local/bin/entrypoint.sh"]
