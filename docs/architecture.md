# Architecture

## Overview

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   Job Sources   │────▶│  Docker container    │────▶│  Google Sheets  │
│  (LinkedIn,etc) │     │  (cron + scripts)    │     │   (Audit Log)   │
└─────────────────┘     └──────────┬───────────┘     └─────────────────┘
                                   │
                      ┌────────────┼────────────┐
                      ▼            ▼            ▼
                ┌──────────┐ ┌──────────┐ ┌──────────┐
                │  OpenAI  │ │  Local   │ │  Cowork  │
                │Screening │ │Filesystem│ │ Browser  │
                │& Writing │ │  State   │ │  Worker  │
                └──────────┘ └──────────┘ └──────────┘
```

The container is the only deployment unit. The same image runs identically on macOS and Windows hosts because Docker abstracts the host OS.

## Components

### Orchestrator: cron in Docker

A single Docker container runs cron alongside the project's Python scripts. The crontab fires:

- The ingestion pipeline (fetch → normalize → dedupe) on a configurable interval (default every 6 hours, off by default during early testing because RapidAPI credits are metered).
- Hourly screening + packet build, chained with `&&` so packet-building only runs if screening exits 0.
- Cover letter drafting every 15 minutes, picking up any packet sitting in `waiting_for_cover_letter_approval`.
- A periodic Sheets sync (`update_google_sheet.py --sync-all`, every 5 minutes) that picks up any new run logs and completed packets and appends rows to the audit Sheet. The sync script is idempotent via the `data/.sheets_synced.json` manifest.

Manual stages (queue transitions, the manual cover-letter override, ad-hoc reruns) are invoked via `docker exec` or directly from the host shell.

### OpenAI API

Used for:
- **Screening**: Hard-reject filter with structured JSON output
- **Cover Letters**: Draft generation from corpus material

All AI decisions use strict structured outputs for machine parsing.

### Claude Cowork (Browser Worker)

Executes applications:
- Reads application packets
- Fills forms from applicant answers
- Uploads documents
- Handles escalations

Driven by the master operator prompt plus one Skill: `prompts/cowork/skills/apply_to_job_from_packet/`, which bundles the full procedure (packet read, fill, escalation, submission audit, artifact logging, ATS handling). See `docs/prompts.md` for details.

### Local Filesystem

Primary state storage:
- `data/` - All job data and queue state
- `artifacts/` - Cover letters
- `config/` - Runtime settings

### Google Sheets

External audit log only. Updated after every application attempt. Not used for queue state.

## Data Flow

1. **Ingest**: Fetch jobs → Normalize → Dedupe
2. **Screen**: Load normalized → OpenAI screening → Route (apply/reject)
3. **Packet**: Build application packet → Classify ATS → Set policies
4. **Queue**: Enqueue → Ready state (or cover-letter wait)
5. **Execute**: Cowork reads packet → Fills forms → Submit/escalate
6. **Log**: Write run log → Update Sheets → Archive artifacts

## Trust Tiers

| Tier | Domains | Notes |
|------|---------|-------|
| A | linkedin.com, greenhouse.io, myworkdayjobs.com | Highest confidence |
| B | User-configured | Verify before relying on auto-submit |
| C | All others | Default; treat as least-trusted |

Auto-submit eligibility is currently driven by `ats_type` and the `auto_submit_*` flags in `config/runtime.json`, not by trust tier directly. See `build_submit_policy` in `scripts/packets/build_application_packets.py`.
