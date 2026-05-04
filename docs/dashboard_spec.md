# Dashboard Spec (Prototype)

A lightweight NiceGUI dashboard for editing search/applicant config and visualizing
pipeline activity. Prototype scope — not a production-quality app.

## Goals

- Edit search preferences (locations, titles, reject rules, approved role domains).
- Edit applicant profile (master answers, cover letter master, resume).
- Visualize pipeline activity: applications over time, breakdown by location,
  current queue depths, failed/escalated runs.
- Run alongside the existing cron worker without coupling its uptime.

Non-goals (v1):
- Mutating queue state from the GUI (`transition_packet.py` / `approve_cover_letter.py`
  remain CLI-only).
- Authentication. Localhost-only binding is sufficient on a single-user machine.
- Real-time updates / websockets. Page-load reads are fine at current data volume.
- Markdown rendering / preview. Raw textareas only.

## Deployment

A new `dashboard` service in `docker-compose.yml`, separate from `job-automation`:

```yaml
dashboard:
  build:
    context: .
    dockerfile: docker/dashboard.Dockerfile
  image: job-automation-dashboard:latest
  container_name: job-automation-dashboard
  restart: unless-stopped
  ports:
    - "127.0.0.1:8080:8080"   # localhost-only
  volumes:
    - ./config:/app/config            # rw — dashboard is the only writer
    - ./data:/app/data:ro             # read-only — visualization only in v1
    - ./schemas:/app/schemas:ro       # for write-time validation
    - ./prompts:/app/prompts:ro
  environment:
    - TZ=${LOCAL_TIMEZONE:-America/Los_Angeles}
```

Rationale for splitting from the cron container: the worker keeps `config:ro`
unchanged, GUI crashes don't affect overnight runs, and dependencies stay isolated
(NiceGUI brings FastAPI/uvicorn — the worker doesn't need them).

`docker/dashboard.Dockerfile` is a thin Python 3.12-slim image that installs
`requirements-dashboard.txt` (just `nicegui` plus what's already in
`requirements.txt`) and runs `python -m dashboard`.

The dashboard process serves NiceGUI on `0.0.0.0:8080` inside the container; the
compose port mapping exposes it only on the host loopback.

## Source layout

```
dashboard/
  __init__.py
  __main__.py            # `python -m dashboard` entrypoint
  app.py                 # NiceGUI page registrations + tab layout
  config_io.py           # read/validate/backup/write of config files
  data_io.py             # read-only loaders for data/* (cached per-request)
  pages/
    overview.py
    search_prefs.py
    applicant.py
    runs.py
```

No persistence layer beyond the filesystem. Each page reads what it needs at
request time. If perf becomes an issue (it won't at this scale), add a 60s
in-memory cache keyed by file mtime.

## Pages

### 1. Overview

Top row: four count tiles.
- Applied (lifetime) — count of `data/queues/completed/*.json`.
- In flight — count of packets in `ready_to_apply` + `in_progress`.
- Escalated — count across `waiting_for_*` queues.
- Failed — count of run logs where `result == "failed"` (last 30 days).

Charts (ECharts via `ui.echart`):
- **Applications over time**: bar chart, last 30 days, bucketed by day.
  Source: `data/queues/completed/*.json` `updated_at` (fallback `created_at`).
- **Breakdown by location**: bar chart, top 10 locations among completed packets.
  Group by city extracted from packet `location` (split on first comma).
- **Screening decisions**: bar chart, apply vs reject totals plus stacked
  reject-reason breakdown (from `matched_reject_rules` in `data/screened_jobs/*`).

Per-factor breakdown charts (by role domain, industry, experience required) are
backed by `data_io.screened_factor_breakdown(field, decision)`. The screener
records each enabled factor's categorization on every screening decision (see
`docs/prompts.md` → Factor Output Fields). Synthetic location-prefilter rejects
omit those fields and bucket as `'(missing)'`.

Queue-depth strip at the bottom: one number per directory under `data/queues/`.

### 2. Search prefs

Form-edits two JSON files with typed inputs and on-save validation:

- `config/search/search_filters.json`
  - `locations`: editable list (add/remove rows of strings).
  - `remote_allowed` / `onsite_allowed` / `hybrid_allowed`: checkboxes.
  - `keywords_include` / `keywords_exclude`: editable lists.
  - `linkedin_api.*`: nested fields rendered inline (endpoint, location_filter,
    seniority_filter, max_jobs, include_description).

- `config/search/reject_rules.json`
  - `enabled_factors`: multi-select against the known set
    (`experience`, `role_domain`, `industry`, `clearance`, `location`).
  - `max_required_years_experience`: number input.
  - `reject_senior_titles`: checkbox.
  - `senior_title_keywords`: editable list.
  - `reject_if_*` flags: checkboxes.
  - `reject_if_explicitly_unwanted_domain`: editable list.

Plain textareas for:
- `config/search/approved_role_domains.md`
- `config/search/approved_industries.md`
- `config/search/titles.txt`

### 3. Applicant

- `config/applicant/applicant_master_answers.md` — textarea.
- `config/applicant/cover_letters_master.md` — textarea.
- `config/applicant/resume.pdf` — file upload that replaces the PDF (after
  backing up the previous version).

### 4. Runs

Sortable, filterable table of `data/run_logs/run_*.json` (skip the legacy
non-`run_`-prefixed files).

Columns: `started_at`, `finished_at`, `packet_id`, `result`, `issue_type`, `notes`.
Filters: result (multi-select), date range, free-text search over `notes`.
Default sort: `started_at` descending.

Each row links to the packet — locate it by scanning queue directories for
`<packet_id>.json` and show the matching packet path. If the packet is in
`data/queues/failed/`, surface the failed-queue path explicitly.

Top-of-page summary: counts by `result` and by `issue_type` over the selected
date range.

## Write safety (config edits)

Every write to `config/*` follows this sequence:

1. Read current file from disk.
2. Apply the edit in memory.
3. Validate against a JSON Schema in `schemas/`. Reject the save and surface
   the error in the UI if validation fails. v1 of the dashboard adds schemas
   for `runtime.json`, `search_filters.json`, and `reject_rules.json` (they
   currently lack one) so this validation path is uniform across all editable
   config files. See build step 4 below.
4. Copy current file to `config/.backups/<relative_path>.<ISO8601>.bak`.
5. Atomic replace: write to `<path>.tmp`, `os.replace()` to final.

Backups directory is created on first write; `.gitignore` should exclude it.

For `resume.pdf`: same backup-then-replace pattern; reject uploads larger than
5 MB and non-`application/pdf` content types.

## Data-load patterns

- `data/queues/<state>/`: `glob("*.json")`, count or load as needed. Total volume
  is small enough that loading all completed packets per page-render is fine.
- `data/screened_jobs/`: same pattern; load on Overview only.
- `data/run_logs/run_*.json`: load on Runs page; the older non-prefixed files
  predate the current schema and are ignored.
- `data/normalized_jobs/`: not loaded in v1 (Overview uses packet data, which
  already carries `company`, `title`, `location`).

All loaders return plain dicts, no dataclasses. Bad/legacy files are skipped
with a logged warning rather than failing the page.

## Dependencies

Add to a new `requirements-dashboard.txt`:
```
nicegui>=2.0
```

Everything else needed (`jsonschema`, `python-dotenv`) is already in
`requirements.txt` and reused.

## Out of scope (explicit follow-ups)

- Triggering pipeline runs from the UI.
- Approving cover letters from the UI (memory note: friendlier approval flow
  is already a known follow-up).
- Editing `config/runtime.json` (low value vs. risk for a prototype; CLI-edit
  for now). A schema for it is still added in v1 for future-proofing.
- Wiring the per-factor breakdown helpers (`data_io.screened_factor_breakdown`)
  into actual Overview charts. The screener already records the factor
  categorizations on each decision; the chart wiring is the remaining step.

## Build order

1. New `dashboard/` package + Dockerfile + compose service; "hello world" page
   reachable at `http://127.0.0.1:8080`.
2. Read-only Overview (counts + applications-over-time only).
3. Runs page.
4. Author JSON Schemas for `runtime.json`, `search_filters.json`, and
   `reject_rules.json`; wire them into the existing `schemas/` directory.
5. Search-prefs editor with backup + schema-validated save.
6. Applicant editor (textareas + resume upload).
7. Remaining Overview charts (location, screening decisions).
