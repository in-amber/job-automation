#!/bin/bash
set -e

echo "[entrypoint] starting job-automation container"
echo "[entrypoint] timezone: ${TZ:-UTC}"
echo "[entrypoint] active crontab:"
sed 's/^/    /' /etc/cron.d/job-automation

# cron in /etc/cron.d/ files must be world-readable; recopy in case the
# bind-mounted source had different perms on the host.
chmod 0644 /etc/cron.d/job-automation

echo "[entrypoint] launching cron in foreground"
exec cron -f -L 15
