# Setup Guide

## Prerequisites

- macOS
- Docker Desktop
- Python 3.10+
- Google Cloud account (for Sheets API)
- OpenAI API key

## Installation

### 1. Clone and Configure

```bash
cd job-automation
cp .env.example .env
```

Edit `.env` with your values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_SHEET_ID`: ID of your tracking spreadsheet
- `N8N_BASIC_AUTH_PASSWORD`: Change from default

### 2. Set Up Google Sheets

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create a service account
4. Download credentials JSON to `config/google_credentials.json`
5. Create a Google Sheet with tabs: `applications`, `rejections`, `interventions`, `runs`
6. Share the sheet with your service account email

### 3. Configure Applicant Data

```bash
cp config/applicant/applicant_master_answers.txt.example config/applicant/applicant_master_answers.txt
cp config/applicant/cover_letters_master.md.example config/applicant/cover_letters_master.md
```

Edit these files with your information:
- Add your resume to `config/applicant/resume.pdf`
- Fill in `applicant_master_answers.txt` with your standard answers
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

### 6. Start n8n

```bash
docker-compose up -d
```

Access n8n at http://localhost:5678

### 7. Import n8n Workflows

1. Open n8n web interface
2. Import each workflow from `n8n/workflows/`
3. Configure credentials in n8n

## Directory Permissions

Ensure these directories are writable:
- `data/`
- `artifacts/`
- `n8n/data/`

## Verification

Run the test suite:
```bash
pytest tests/ -v
```

## Common Issues

### Docker not starting
Ensure Docker Desktop is running.

### n8n can't write data
Check permissions on `n8n/data/` directory.

### Google Sheets errors
Verify the sheet is shared with your service account email.
