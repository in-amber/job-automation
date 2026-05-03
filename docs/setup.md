# Setup Guide

## Prerequisites

- macOS or Windows host
- Docker Desktop
- Python 3.10+ (for any host-side script invocations; the container has its own)
- Google Cloud account (for Sheets API)
- OpenAI API key
- RapidAPI account (LinkedIn Job Search API)

## Installation

### 1. Clone and Configure

```bash
cd job-automation
cp .env.example .env
```

Edit `.env` with your values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `RAPIDAPI_KEY`: Your RapidAPI key for LinkedIn job search
- `GOOGLE_SHEET_ID`: ID of your tracking spreadsheet
- `GOOGLE_SHEETS_CREDENTIALS_PATH`: Path to your Google service-account credentials JSON (relative paths are resolved against the project root)

### 2. Set Up Google Sheets

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account
4. Download credentials JSON to `config/google_credentials.json`
5. Create a Google Sheet with tabs: `applications`, `rejections`, `interventions`, `runs`
6. Share the sheet with your service account email

### 3. Configure Applicant Data

```bash
cp config/applicant/applicant_master_answers.md.example config/applicant/applicant_master_answers.md
cp config/applicant/cover_letters_master.md.example config/applicant/cover_letters_master.md
```

Edit these files with your information:
- Add your resume to `config/applicant/resume.pdf`
- Fill in `applicant_master_answers.md` with your standard answers
- Add your cover letter material to `cover_letters_master.md`

### 4. Configure Search and Rules

Edit these files:
- `config/search/titles.txt`: Job titles to search
- `config/search/search_filters.json`: Location preferences
- `config/search/reject_rules.json`: Hard reject criteria

### 5. Validate Environment

```bash
python scripts/bootstrap/validate_env.py
```

### 6. Start the Container

```bash
docker-compose up -d
```

This builds the image (first run only, ~2 min) and starts the container. cron is now running inside it and will fire the configured scheduled jobs.

Tail container logs to see cron-job output:

```bash
docker-compose logs -f
```

Stop the container:

```bash
docker-compose down
```

### 7. Verify the Container

Confirm cron is reading the crontab and the scripts can find their dependencies:

```bash
docker exec job-automation crontab -l         # should print the project's crontab
docker exec job-automation python /home/node/scripts/bootstrap/validate_env.py
```

## Directory Permissions

Ensure these directories are writable:
- `data/`
- `artifacts/`

## Verification

Run the test suite:
```bash
pytest tests/ -v
```

## Common Issues

### Docker not starting
Ensure Docker Desktop is running.

### Cron jobs aren't firing
Check `docker-compose logs -f` for cron-job output. Confirm `docker exec job-automation crontab -l` lists the expected schedule. Cron in containers has a known footgun where env vars set in `docker-compose.yml` are not visible to cron jobs — the project's entrypoint writes `.env` contents into a location cron can read; if a cron job fails with missing-env errors, verify that mechanism in `docker/entrypoint.sh`.

### Google Sheets errors
Verify the sheet is shared with your service account email. `GOOGLE_SHEETS_CREDENTIALS_PATH` may be relative; the script resolves relative paths against the project root.
