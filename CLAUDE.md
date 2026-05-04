# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local-first job application automation system. Runs in a Docker container so the same setup works on macOS or Windows hosts. Uses cron in the container for scheduled orchestration, OpenAI API for screening/writing, and Claude Cowork for browser automation.

**Philosophy**: Volume-first. Screening is a hard-reject filter, not a ranking system. Default to APPLY unless a configured hard rule clearly triggers.

## Architecture

- **Orchestrator**: cron running inside the project's Docker container; scheduled jobs invoke the Python scripts directly
- **Screening/Writing**: OpenAI API with structured outputs
- **Browser Worker**: Claude Cowork (reads packets, fills forms, escalates on issues)
- **State**: Local filesystem is primary; Google Sheets is audit log only

## Commands

```bash
# Bootstrap
python scripts/bootstrap/init_dirs.py
python scripts/bootstrap/validate_env.py

# Container lifecycle
docker-compose up -d        # start the container; cron picks up the schedule
docker-compose logs -f      # tail cron-job output
docker-compose down         # stop

# Manual triggers (run inside the container)
docker exec job-automation python /home/node/scripts/screening/screen_jobs.py
docker exec job-automation python /home/node/scripts/cover_letters/draft_cover_letters.py

# Ingestion pipeline
python scripts/ingest/fetch_jobs.py --source linkedin
python scripts/ingest/normalize_jobs.py
python scripts/ingest/dedupe_jobs.py

# Screening
python scripts/screening/screen_jobs.py

# Packets and queue
python scripts/packets/build_application_packets.py   # writes packets directly into data/queues/ready_to_apply/
python scripts/queues/transition_packet.py <packet_id> <new_state>

# Cover letters
python scripts/cover_letters/draft_cover_letters.py

# Google Sheets sync
python scripts/sheets/update_google_sheet.py

# Tests
pytest tests/ -v
pytest tests/unit/test_location_prefilter.py -v  # Single test file
```

## Critical Behavioral Rules

1. **Screening defaults to APPLY** - reject only when hard rules clearly trigger
2. **Cover-letter queue is non-blocking** - waiting packets don't block other applications
3. **No autonomous signup** - escalate and continue to next job
4. **Google Sheets updated after every application attempt**
5. **All ATS types auto-submit by default; per-ATS flags in `config/runtime.json` (`auto_submit_*`) toggle behavior**

## Queue States

`screened_apply` → `ready_to_apply` → `in_progress` → `completed`

Escalation paths: `waiting_for_cover_letter_approval`, `waiting_for_signup`, `waiting_for_human_review`, `failed`, `rejected`

## Key Files

- `config/runtime.json` - Submit policies, retry limits, mode settings
- `config/search/reject_rules.json` - Hard reject criteria
- `config/search/approved_role_domains.md` - Inclusive list of role categories the screener will apply to (gated by `reject_if_role_not_in_approved_domains`); see `docs/prompts.md` for behavior
- `config/search/approved_industries.md` - Inclusive list of company industries the screener will apply to (gated by `reject_if_industry_not_in_approved`, opt-in via `enabled_factors`); see `docs/prompts.md` for behavior
- `config/applicant/applicant_master_answers.md` - Form field answers
- `schemas/*.schema.json` - JSON Schema validators for all data types
- `prompts/` - System prompts for OpenAI and Cowork

## Testing

Tests enforce volume-first behavior:
- `test_screening.py` - Verifies apply-by-default, reject only on hard rules
- `test_queue_transitions.py` - Verifies cover-letter non-blocking behavior
