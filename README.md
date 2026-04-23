# Job Application Automation

Local-first job application automation system for macOS that maximizes application volume while preserving control, logging, and auditability.

## Philosophy

This system is **volume-first**. Screening is a hard-reject filter, not a ranking system.

- If clearly disqualified → reject
- If clearly not interested → reject
- Otherwise → **apply**

## Architecture

| Component | Technology | Responsibility |
|-----------|------------|----------------|
| Orchestrator | n8n (Docker) | Scheduling, workflow, state transitions |
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

3. **Start n8n**
   ```bash
   docker-compose up -d
   ```

4. **Configure your search**
   - Edit `config/search/titles.txt` with job titles
   - Edit `config/search/reject_rules.json` with hard reject criteria
   - Add your resume to `config/applicant/resume.pdf`
   - Fill in `config/applicant/applicant_master_answers.md`

5. **Run the pipeline**
   ```bash
   python scripts/ingest/fetch_jobs.py --source linkedin
   python scripts/ingest/normalize_jobs.py
   python scripts/screening/screen_jobs.py
   python scripts/packets/build_application_packets.py
   ```

## Directory Structure

```
config/          Runtime settings, search filters, applicant data
data/            Jobs, packets, queues, logs (primary state)
artifacts/       Cover letters
prompts/         OpenAI and Cowork system prompts
schemas/         JSON Schema validators
scripts/         Python CLI tools
n8n/             Workflow definitions
tests/           Unit and integration tests
```

## Trusted Application Targets (v1)

- LinkedIn Easy Apply (auto-submit allowed)
- Greenhouse
- Workday

## Non-Goals (v1)

- Autonomous account creation
- Captcha solving
- OTP/email/SMS verification
- Multi-resume support
- Sophisticated scoring beyond reject/apply

## License

Private - not for distribution.
