# Job Application Automation Spec

## 1. Objective

Build a local-first job application automation system that maximizes application volume while preserving enough control, logging, and auditability to trust the process.

The system should:

- ingest job postings from a configurable source
- reject only clearly disqualified or clearly unwanted jobs
- generate application packets for everything else
- draft cover letters when needed
- queue those packets for browser execution
- use Claude Cowork to fill and optionally submit applications
- update a Google Sheet after every completed application
- store a full local audit trail of decisions, submissions, and escalations

## 2. Product philosophy

This system is **volume-first**.

Screening is not meant to be selective. It is a hard-reject filter.

Default behavior:

- if clearly disqualified, reject
- if clearly not interested, reject
- otherwise, apply

There is no human review step for qualification screening.

There is a human approval step for cover letters and an optional human approval step before final submission.

## 3. Fixed decisions already made

These are locked requirements.

- Environment: local Mac
- Docker is allowed
- n8n should be self-hosted locally
- Google Sheet is the definitive external activity log
- Google Sheet must be updated after every completed application
- local files are the primary source of truth for artifacts and state
- manual signup only
- if signup is required, escalate and move on to next job
- trusted automated application targets in v1:
  - LinkedIn Easy Apply
  - Greenhouse
  - Workday
- LinkedIn Easy Apply is trusted enough for auto-submit
- Workday should attempt to correct fields before escalating
- if screening predicts a cover letter is needed, generate draft and move packet to waiting-for-approval
- if Cowork discovers a cover letter is needed mid-application, stop that job, send it to the cover-letter workflow, and continue the queue

## 4. High-level architecture

### Orchestrator

Self-hosted n8n running locally in Docker.

Responsibilities:

- scheduled ingestion
- job normalization
- deduplication
- screening calls to OpenAI
- queue/state transitions
- cover-letter generation calls to OpenAI
- Google Sheets updates
- local file writes
- run bookkeeping

### Screening and writing engine

OpenAI API.

Responsibilities:

- hard-reject screening
- cover-letter drafting
- optional extraction helpers

Use strict structured outputs for screening and other machine-consumed decisions.

### Browser worker

Claude Cowork.

Responsibilities:

- read application packet
- navigate ATS/application site
- fill fields
- upload documents
- pause on escalation conditions
- optionally submit
- save screenshots/PDFs/notes

### Optional local coding/control plane

Claude Code.

Responsibilities:

- scaffold repo
- generate configs and schemas
- write scripts
- stand up Docker and n8n files
- implement queue workers and utilities
- add tests and docs

## 5. Non-goals for v1

Do not implement these in the initial scaffold:

- autonomous account creation
- autonomous credential management
- captcha solving
- OTP/email/SMS verification handling
- broad permissions on arbitrary domains
- resume tailoring or multi-resume support
- sophisticated ranking/scoring beyond reject vs apply
- scraping architecture that depends tightly on one provider
- deep ATS-specific custom parsers beyond a reasonable shared abstraction

## 6. Root project structure

Use this exact top-level structure.

```text
job-automation/
  README.md
  .env.example
  .gitignore
  docker-compose.yml

  docs/
    architecture.md
    workflow-spec.md
    state-machine.md
    prompts.md
    security.md
    setup.md

  config/
    runtime.json
    trusted_domains.json
    search/
      titles.txt
      search_filters.json
      reject_rules.json
    applicant/
      applicant_master_answers.md
      cover_letters_master.md
      resume.pdf

  data/
    raw_jobs/
    normalized_jobs/
    screened_jobs/
    application_packets/
    queues/
      ready_to_apply/
      waiting_for_cover_letter_approval/
      waiting_for_signup/
      waiting_for_human_review/
      completed/
      rejected/
      failed/
    run_logs/
    checkpoints/

  artifacts/
    screenshots/
    pdfs/
    cover_letters/
    exports/

  sheets/
    schema.md

  prompts/
    screening/
      system.md
      user_template.md
      schema.json
    cover_letter/
      system.md
      user_template.md
    cowork/
      master_operator.md
      skills/
        apply_to_job_from_packet/
          SKILL.md
          escalation_policy.md
          submission_audit_checklist.md
          artifact_logging.md
          ats_playbooks.md
        # Future optional splits (TODO, do not implement yet):
        #   workday_application/SKILL.md
        #   greenhouse_application/SKILL.md
        #   linkedin_easy_apply/SKILL.md
        #   application_recovery/SKILL.md
        # Only split out if the main skill becomes too long,
        # ATS behavior clearly diverges, or resuming from
        # interrupted applications becomes a common workflow.

  schemas/
    normalized_job.schema.json
    screening_decision.schema.json
    application_packet.schema.json
    cover_letter_request.schema.json
    run_log.schema.json
    intervention_report.schema.json

  scripts/
    bootstrap/
      init_dirs.py
      validate_env.py
    ingest/
      fetch_jobs.py
      normalize_jobs.py
      dedupe_jobs.py
    screening/
      screen_jobs.py
    cover_letters/
      draft_cover_letters.py
    packets/
      build_application_packets.py
    queues/
      enqueue_packet.py
      dequeue_packet.py
      transition_packet.py
    sheets/
      update_google_sheet.py
    run_logs/
      write_run_log.py
      archive_artifacts.py
    utils/
      fileio.py
      hashing.py
      json_validate.py
      timestamps.py

  n8n/
    workflows/
      01_ingest_jobs.json
      02_screen_jobs.json
      03_generate_cover_letters.json
      04_queue_packets.json
      05_log_completed_application.json
    credentials/
      README.md

  tests/
    fixtures/
    unit/
    integration/
```

## 7. Local-first storage model

The local filesystem is the primary operational state.

Google Sheets is the definitive external audit log for application activity, but not the operational queue.

Rule:

- queue state lives locally
- artifacts live locally
- raw and derived job data live locally
- Google Sheets mirrors key events after each application

## 8. Configuration files

### `config/runtime.json`

```json
{
  "mode": "volume_first",
  "default_decision_on_uncertainty": "apply",
  "human_approval_before_submit": true,
  "auto_submit_linkedin_easy_apply": true,
  "auto_submit_greenhouse": false,
  "auto_submit_workday": false,
  "attempt_field_corrections_before_escalation": true,
  "max_field_retries": 2,
  "max_issue_minutes": 3,
  "pause_on_cover_letter_detection": true,
  "manual_signup_only": true,
  "update_google_sheet_after_each_application": true,
  "local_timezone": "America/Los_Angeles"
}
```

### `config/trusted_domains.json`

```json
{
  "tier_a": [
    "linkedin.com",
    "greenhouse.io",
    "myworkdayjobs.com"
  ],
  "tier_b": [],
  "tier_c_default": true
}
```

### `config/search/titles.txt`

One title or search phrase per line.

### `config/search/search_filters.json`

Contains location and search constraints.

Example:

```json
{
  "locations": ["San Francisco Bay Area", "Remote", "New York"],
  "remote_allowed": true,
  "onsite_allowed": true,
  "hybrid_allowed": true,
  "keywords_include": [],
  "keywords_exclude": []
}
```

### `config/search/reject_rules.json`

The hard reject policy.

Example:

```json
{
  "max_required_years_experience": 1,
  "reject_senior_titles": true,
  "senior_title_keywords": ["senior", "staff", "principal", "lead", "manager", "director"],
  "reject_if_requires_clearance": true,
  "reject_if_requires_unmet_work_authorization": true,
  "reject_if_location_mismatch": true,
  "reject_if_explicitly_unwanted_domain": []
}
```

## 9. Core schemas

Claude Code should create JSON Schemas and validators for these.

### `NormalizedJob`

Fields:

- `job_id`
- `source`
- `source_posting_id`
- `fetched_at`
- `company`
- `title`
- `location`
- `employment_type`
- `apply_url`
- `source_url`
- `description_raw`
- `description_clean`
- `salary_text`
- `seniority_hint`
- `remote_hint`
- `requires_cover_letter_hint`
- `metadata`

### `ScreeningDecision`

Fields:

- `job_id`
- `decision` enum: `apply | reject`
- `hard_reject_rule_triggered`
- `matched_reject_rules`
- `reason_summary`
- `confidence`
- `cover_letter_likely_required`
- `generated_at`

Important rule:

- if no hard reject rule is clearly triggered, `decision` must be `apply`

### `ApplicationPacket`

Fields:

- `packet_id`
- `job_id`
- `company`
- `title`
- `location`
- `source`
- `source_url`
- `apply_url`
- `ats_type`
- `trust_tier`
- `resume_path`
- `cover_letter_status` enum:
  - `not_needed`
  - `predicted_needed_draft_pending`
  - `draft_ready_waiting_approval`
  - `approved`
  - `required_discovered_mid_apply`
- `cover_letter_path`
- `applicant_answers_path`
- `job_snapshot_path`
- `screening_decision_path`
- `submit_policy`
- `escalation_policy`
- `status`
- `created_at`
- `updated_at`

### `RunLog`

Fields:

- `run_id`
- `packet_id`
- `worker`
- `started_at`
- `finished_at`
- `result`
- `confirmation_number`
- `escalation_reason`
- `notes`
- `screenshot_paths`
- `pdf_path`

### `InterventionReport`

Fields:

- `packet_id`
- `issue_type`
- `issue_summary`
- `current_url`
- `suggested_next_action`
- `created_at`

## 10. Queue and state machine

Every packet must be in exactly one queue/state at a time.

Allowed states:

- `screened_apply`
- `rejected`
- `waiting_for_cover_letter_approval`
- `ready_to_apply`
- `in_progress`
- `waiting_for_signup`
- `waiting_for_human_review`
- `completed`
- `failed`

### Transition rules

#### Job screening

- raw job -> normalized job
- normalized job -> `rejected` if hard reject rule triggers
- normalized job -> `screened_apply` otherwise

#### Cover-letter prediction

- if screening predicts cover letter needed:
  - build packet
  - draft cover letter
  - move packet to `waiting_for_cover_letter_approval`

#### Cover-letter discovered mid-application

- if Cowork discovers cover letter requirement during application:
  - save current progress
  - mark packet `required_discovered_mid_apply`
  - create cover-letter draft request
  - move packet to `waiting_for_cover_letter_approval`
  - remove current job from active browser queue
  - continue next queued packet

#### Approved cover letter

- once approved:
  - attach cover letter path
  - move packet to `ready_to_apply`

#### Signup needed

- if signup required:
  - create intervention report
  - move packet to `waiting_for_signup`
  - continue next queued packet

#### Browser execution

- `ready_to_apply` -> `in_progress`
- `in_progress` -> `completed`
- `in_progress` -> `waiting_for_human_review`
- `in_progress` -> `waiting_for_signup`
- `in_progress` -> `failed`

## 11. Screening behavior

This is the most important logic rule in the whole system.

The screening agent is a **rejector**, not a selector.

### Screening contract

Inputs:

- normalized job
- title list
- search filters
- reject rules

Outputs:

- strict `ScreeningDecision` JSON

### Screening policy

- reject only when a configured hard rule is clearly triggered
- ignore soft concerns
- ignore “preferred” qualifications
- ignore mild seniority hints unless a hard rule clearly applies
- if unsure whether a reject rule applies, do not reject
- if job seems imperfect but not clearly disqualified, apply
- never escalate screening to a human

### Examples

Reject:

- “requires 3+ years of experience” when max allowed is 1
- “senior product security engineer” when senior titles are blocked
- requires clearance you do not have
- explicit location mismatch per your file

Apply:

- “1 to 3 years preferred”
- “ideally has X”
- “nice to have Y”
- unclear level
- ambiguous qualifications
- partial mismatch but no hard rule triggered

## 12. Cover-letter workflow

### Trigger conditions

A cover-letter draft should be created when either:

- screening predicts cover letter likely needed, or
- browser worker discovers a required cover-letter field and none is approved

### Behavior

- draft cover letter using job packet + cover-letter corpus
- save draft locally under `artifacts/cover_letters/`
- update packet status to `draft_ready_waiting_approval`
- move packet to `waiting_for_cover_letter_approval`

### Queue behavior

A packet waiting on cover-letter approval must not block the rest of the queue.

Rule:

- remove it from the active application queue
- continue processing the next packet

## 13. Browser automation policy for Cowork

Claude Cowork should be treated as a constrained worker.

### Allowed actions

- open application page
- navigate trusted ATS flows
- fill fields from packet and applicant master answers
- upload approved files
- correct form field mismatches
- save screenshots
- save PDF if practical
- submit if policy allows

### Forbidden actions

- create accounts automatically
- generate or manage passwords
- use sensitive credentials beyond already-authenticated sessions
- solve captchas
- handle OTP/email/SMS verification
- invent answers not grounded in the packet or approved applicant file
- continue indefinitely on broken forms

### Escalation triggers

Immediate escalation on:

- signup required
- captcha
- OTP verification
- ambiguous legal/work authorization question not clearly covered
- essay/freeform answer not available in packet
- unknown suspicious domain
- missing required document

Try-then-escalate on:

- field label mismatch
- date formatting mismatch
- resume parser damage
- upload widget issues
- broken Workday field mapping

### Retry policy

- max 2 retries per field
- max 3 minutes on one unresolved issue
- after that, generate `InterventionReport` and move on

### Submission policy

- LinkedIn Easy Apply: auto-submit allowed by config
- Greenhouse: controlled by config
- Workday: controlled by config
- unknown sites: never auto-submit in v1

## 14. ATS abstraction

Claude Code should create a small ATS classifier with these labels:

- `linkedin_easy_apply`
- `greenhouse`
- `workday`
- `other`

Classifier inputs:

- URL
- domain
- page markers if available

The system should store `ats_type` in every packet and log.

## 15. Google Sheets schema

Create four tabs.

### `applied`

Columns:

- `application_id`
- `date_found`
- `date_applied`
- `company`
- `title`
- `location`
- `source`
- `source_url`
- `apply_url`
- `ats_type`
- `status`
- `submission_mode`
- `cover_letter_used`
- `artifact_folder`
- `confirmation_number`
- `notes`

### `skipped`

Columns:

- `job_id`
- `date_screened`
- `company`
- `title`
- `source_url`
- `reject_rule`
- `reason_summary`
- `job_snapshot_path`

### `interventions`

Columns:

- `packet_id`
- `company`
- `title`
- `issue_type`
- `issue_summary`
- `status`
- `created_at`
- `resolved_at`

### `runs`

Columns:

- `run_id`
- `packet_id`
- `started_at`
- `finished_at`
- `worker`
- `result`
- `escalation_reason`
- `confirmation_number`
- `log_path`

### Sheet update rule

After every completed application attempt, immediately update:

- `applied`
- `runs`
- `interventions` if relevant

## 16. n8n workflows to scaffold

### Workflow 1: ingest jobs

Steps:

- schedule trigger
- fetch raw jobs from configured provider
- normalize
- dedupe
- write raw and normalized files locally

### Workflow 2: screen jobs

Steps:

- load unscreened normalized jobs
- call OpenAI screening prompt with strict schema
- write `ScreeningDecision`
- route to rejected or packet-building path

### Workflow 3: generate cover letters

Steps:

- find packets needing cover letters
- call OpenAI draft prompt
- save draft locally
- update packet and queue state

### Workflow 4: queue packets

Steps:

- move eligible packets to `ready_to_apply`
- ensure waiting states do not block queue

### Workflow 5: log completed application

Steps:

- consume run result
- write run log locally
- update Google Sheets immediately
- archive screenshots/PDFs

## 17. Scripts to implement

Claude Code should implement these scripts with clear CLI entry points.

### Ingestion

- `fetch_jobs.py`
- `normalize_jobs.py`
- `dedupe_jobs.py`

### Screening

- `screen_jobs.py`

### Packets

- `build_application_packets.py`

### Cover letters

- `draft_cover_letters.py`

### Queue management

- `enqueue_packet.py`
- `dequeue_packet.py`
- `transition_packet.py`

### Sheets sync

- `update_google_sheet.py`

### Logging

- `write_run_log.py`
- `archive_artifacts.py`

### Bootstrap

- `init_dirs.py`
- `validate_env.py`

## 18. Prompt files to create

### Screening prompt

Must instruct model to:

- default to apply
- reject only on explicit hard rule triggers
- output strict schema only
- explain which reject rule triggered

### Cover-letter prompt

Must instruct model to:

- use existing cover-letter corpus as style/material source
- tailor modestly
- never invent experience
- produce concise, plausible draft
- mark approval required

### Cowork master operator prompt

Must instruct Cowork to:

- read packet first
- fill only from packet and applicant answers
- respect submit policy
- stop on escalation triggers
- save artifacts
- generate structured issue reports when blocked

## 19. Security boundaries

### Filesystem

Cowork should only be pointed at the project root and approved document files.

### Browser

Use a separate browser profile for job applications.

### Accounts

No autonomous signup. Ever in v1.

### Secrets

Use `.env` and Docker secrets patterns where practical.
Do not hardcode API keys in repo files.

### Logging

Never store passwords.
Never store OTP codes.
Do store enough context to resume interrupted applications.

## 20. Implementation order for Claude Code

This should be the execution sequence.

### Phase 1

Scaffold only:

- repo structure
- docs
- schemas
- config files
- env example
- Docker Compose
- utility modules
- test skeletons

### Phase 2

Implement:

- ingestion
- normalization
- dedupe
- screening
- packet generation

### Phase 3

Implement:

- cover-letter drafting
- waiting queue logic
- Google Sheets sync
- run logging

### Phase 4

Implement:

- Cowork-facing prompt files
- intervention report flow
- completion logging hooks
- artifact archiving helpers

Do not attempt full browser automation inside this repo unless explicitly requested later. This repo should prepare the packets, prompts, state machine, and logging needed for Cowork to execute reliably.

## 21. Acceptance criteria

Claude Code’s output is acceptable when all of the following are true:

- project boots locally on Mac with Docker
- directory structure matches spec
- all schemas exist and validate sample payloads
- config files exist with realistic defaults
- n8n Docker setup exists
- n8n workflow JSON files exist as initial scaffold
- Python scripts exist with CLI stubs or working first-pass implementations
- screening pipeline works end-to-end on fixture jobs
- “apply by default” behavior is enforced by tests
- cover-letter waiting queue behavior is enforced by tests
- Google Sheets sync module exists and is wired into completed-application flow
- Cowork prompt files exist and reflect the stated policies
- docs clearly explain how to configure and run the system

