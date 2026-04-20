# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local-first job application automation system for macOS. Uses n8n for orchestration, OpenAI API for screening/writing, and Claude Cowork for browser automation.

**Philosophy**: Volume-first. Screening is a hard-reject filter, not a ranking system. Default to APPLY unless a configured hard rule clearly triggers.

## Architecture

- **Orchestrator**: Self-hosted n8n in Docker
- **Screening/Writing**: OpenAI API with structured outputs
- **Browser Worker**: Claude Cowork (reads packets, fills forms, escalates on issues)
- **State**: Local filesystem is primary; Google Sheets is audit log only

## Commands

```bash
# Bootstrap
python scripts/bootstrap/init_dirs.py
python scripts/bootstrap/validate_env.py

# Docker/n8n
docker-compose up -d

# Ingestion pipeline
python scripts/ingest/fetch_jobs.py --source linkedin
python scripts/ingest/normalize_jobs.py
python scripts/ingest/dedupe_jobs.py

# Screening
python scripts/screening/screen_jobs.py

# Packets and queue
python scripts/packets/build_application_packets.py
python scripts/queues/enqueue_packet.py <packet_id>
python scripts/queues/transition_packet.py <packet_id> <new_state>

# Cover letters
python scripts/cover_letters/draft_cover_letters.py

# Google Sheets sync
python scripts/sheets/update_google_sheet.py

# Tests
pytest tests/ -v
pytest tests/unit/test_screening.py -v  # Single test file
```

## Critical Behavioral Rules

1. **Screening defaults to APPLY** - reject only when hard rules clearly trigger
2. **Cover-letter queue is non-blocking** - waiting packets don't block other applications
3. **No autonomous signup** - escalate and continue to next job
4. **Google Sheets updated after every application attempt**
5. **LinkedIn Easy Apply may auto-submit; Greenhouse/Workday require config flag**

## Queue States

`screened_apply` → `ready_to_apply` → `in_progress` → `completed`

Escalation paths: `waiting_for_cover_letter_approval`, `waiting_for_signup`, `waiting_for_human_review`, `failed`, `rejected`

## Key Files

- `config/runtime.json` - Submit policies, retry limits, mode settings
- `config/search/reject_rules.json` - Hard reject criteria
- `config/applicant/applicant_master_answers.md` - Form field answers
- `schemas/*.schema.json` - JSON Schema validators for all data types
- `prompts/` - System prompts for OpenAI and Cowork

## Testing

Tests enforce volume-first behavior:
- `test_screening.py` - Verifies apply-by-default, reject only on hard rules
- `test_queue_transitions.py` - Verifies cover-letter non-blocking behavior
