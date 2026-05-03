# Job Application Automation

Local-first job application automation system that maximizes application volume while preserving control, logging, and auditability. Runs in a Docker container so the same setup works on macOS or Windows hosts.

## Philosophy

This system is **volume-first**. Screening is a hard-reject filter, not a ranking system.

- If clearly disqualified → reject
- If clearly not interested → reject
- Otherwise → **apply**

## Architecture

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Orchestrator | cron in Docker container | Scheduled job ingestion, periodic Sheets sync |
| Screening | OpenAI API | Hard-reject filtering, cover letter drafts |
| Browser Worker | Claude Cowork | Form filling, submission, escalation |
| State | Local filesystem | Primary source of truth |
| Audit Log | Google Sheets | External activity log |

## Quick Start

1. **Clone and configure**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Bootstrap**
   ```bash
   python scripts/bootstrap/validate_env.py
   ```

3. **Start the container**
   ```bash
   docker-compose up -d
   ```
   This brings up the project's Docker container with cron running inside it. The crontab triggers ingestion on a schedule and polls for new run logs to push to Sheets. Tail logs with `docker-compose logs -f`.

4. **Configure your search**
   - Edit `config/search/titles.txt` with job titles
   - Edit `config/search/reject_rules.json` with hard reject criteria
   - Add your resume to `config/applicant/resume.pdf`
   - Fill in `config/applicant/applicant_master_answers.md`

5. **Run pipeline steps manually** (any time, in addition to the scheduled cron jobs)
   ```bash
   docker exec job-automation python /home/node/scripts/ingest/fetch_jobs.py --source linkedin
   docker exec job-automation python /home/node/scripts/ingest/normalize_jobs.py
   docker exec job-automation python /home/node/scripts/screening/screen_jobs.py
   docker exec job-automation python /home/node/scripts/packets/build_application_packets.py
   ```

## Directory Structure

```
config/          Runtime settings, search filters, applicant data
data/            Jobs, packets, queues, logs (primary state)
artifacts/       Cover letters
prompts/         OpenAI and Cowork system prompts
schemas/         JSON Schema validators
scripts/         Python CLI tools
docker/          Container entrypoint and crontab
tests/           Unit and integration tests
```

## Trusted Application Targets (v1)

- LinkedIn Easy Apply
- Greenhouse
- Workday
- Other (catchall — any ATS not in the three above)

Auto-submit is enabled per-ATS via `config/runtime.json` (`auto_submit_*` flags); see `scripts/packets/build_application_packets.py:build_submit_policy`.

## Non-Goals (v1)

- Autonomous account creation
- Captcha solving
- OTP/email/SMS verification
- Multi-resume support
- Sophisticated scoring beyond reject/apply

## License

Private - not for distribution.
