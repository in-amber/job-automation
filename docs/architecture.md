# Architecture

## Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Job Sources   │────▶│    n8n          │────▶│  Google Sheets  │
│  (LinkedIn,etc) │     │  (Orchestrator) │     │   (Audit Log)   │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │  OpenAI  │ │  Local   │ │  Cowork  │
              │Screening │ │Filesystem│ │ Browser  │
              │& Writing │ │  State   │ │  Worker  │
              └──────────┘ └──────────┘ └──────────┘
```

## Components

### n8n Orchestrator

Self-hosted in Docker. Handles:
- Scheduled job ingestion
- Pipeline coordination
- State transitions
- API calls to OpenAI
- Google Sheets updates

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
- Saves artifacts (screenshots, PDFs)

Driven by the master operator prompt plus one Skill: `prompts/cowork/skills/apply_to_job_from_packet/`, which bundles the full procedure (packet read, fill, escalation, submission audit, artifact logging, ATS handling). See `docs/prompts.md` for details.

### Local Filesystem

Primary state storage:
- `data/` - All job data and queue state
- `artifacts/` - Screenshots, PDFs, cover letters
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

| Tier | Domains | Auto-Submit |
|------|---------|-------------|
| A | linkedin.com, greenhouse.io, myworkdayjobs.com | Per config |
| B | User-configured | Never |
| C | All others | Never |
