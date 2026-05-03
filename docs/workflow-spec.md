# Workflow Specification

The system runs as a single Docker container with cron inside. Scheduled jobs are defined in the project's crontab; manual stages are invoked via `docker exec`.

## Scheduled jobs (cron)

### Ingest jobs

**Schedule**: configurable, default every 6 hours (kept disabled or commented out during early testing — RapidAPI credits are metered and a misconfigured filter can burn the daily budget).

**Steps**:
1. Fetch raw jobs from configured provider (`scripts/ingest/fetch_jobs.py --source all`)
2. Normalize to standard schema (`scripts/ingest/normalize_jobs.py`)
3. Deduplicate against existing jobs (`scripts/ingest/dedupe_jobs.py`)

**Output**: New normalized jobs in `data/normalized_jobs/`.

### Sheets sync

**Schedule**: every 5 minutes.

**Steps**:
1. Run `scripts/sheets/update_google_sheet.py --sync-all`.

This iterates `data/queues/completed/`, `data/run_logs/`, and `data/run_logs/interventions/` and appends any not-yet-pushed rows to the audit Sheet's `applied`, `runs`, and `interventions` tabs. Idempotent via `data/.sheets_synced.json`.

## Manual stages

These don't run on a schedule because they require human review of intermediate state. Invoke via `docker exec job-automation python /home/node/scripts/...`.

### Screen jobs

**Trigger**: After ingestion or any time you want to screen newly-fetched jobs.

**Steps**:
1. Load unscreened normalized jobs.
2. Call OpenAI with screening prompt + reject rules + approved role domains (`config/search/approved_role_domains.md`; see `docs/prompts.md`).
3. Parse strict JSON response.
4. Write screening decision.
5. Route: rejected → `data/queues/rejected/`, apply → next step.

**Output**: Screening decisions in `data/screened_jobs/`.

### Build packets

**Trigger**: After screening.

**Steps**:
1. `build_application_packets.py` — turn screened-apply jobs into application packets and write them directly into `data/queues/ready_to_apply/`. Cover-letter need is not predicted; packets start with `cover_letter_path=null` and are routed to `waiting_for_cover_letter_approval` only if the apply step encounters a cover-letter requirement.

### Generate cover letter drafts

**Trigger**: Cron — picks up any packet sitting in `waiting_for_cover_letter_approval` (the apply step moves them there mid-flight when a cover-letter field is discovered).

**Steps**:
1. Find every packet in `waiting_for_cover_letter_approval`.
2. Load job description and cover letter corpus.
3. Call OpenAI draft prompt.
4. Save draft markdown + DOCX to `artifacts/cover_letters/`.
5. Set `cover_letter_path` on the packet and transition it to `ready_to_apply`.

**Output**: DOCX cover letters and packets returned to `ready_to_apply` automatically. No manual approval step in the normal flow.

### Manual cover letter override (escape hatch)

**Trigger**: Rare — only when a human needs to push a packet out of `waiting_for_cover_letter_approval` without a regenerated draft (e.g., a hand-edited DOCX is already in place).

**Steps**:
1. `scripts/cover_letters/approve_cover_letter.py <packet_id>` — verifies the packet is in `waiting_for_cover_letter_approval` and `cover_letter_path` exists, then moves the packet to `ready_to_apply`.

### Apply (Cowork)

**Trigger**: Cowork picks up packets from `ready_to_apply`.

**Steps**:
1. Cowork reads packet and applicant master answers.
2. Fills the form, attaches resume + approved cover letter.
3. Submits per `submit_policy` or escalates per `escalation_policy`.
4. Writes a `RunLog` JSON to `data/run_logs/`.

The run log file is what gets the application into Sheets — the periodic Sheets-sync cron job picks up new run logs and appends rows.
