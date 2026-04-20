# Skill: apply_to_job_from_packet

## Purpose

End-to-end playbook for applying to a single job using an approved application packet. This is the main Cowork browser-worker procedure: read a packet, fill the application, handle branches and escalations, optionally submit, save artifacts, and return a structured result.

Supporting references in this directory:

- `escalation_policy.md` - when to escalate immediately vs. try-then-escalate, retry limits
- `submission_audit_checklist.md` - pre-submit verification steps
- `artifact_logging.md` - what to save, what never to store
- `ats_playbooks.md` - compact per-ATS handling notes

## Inputs

- Path to an application packet JSON file (conforms to `ApplicationPacket` schema)
- Access to `config/applicant/applicant_master_answers.md`
- Access to `config/runtime.json`

## Procedure

### 1. Read and validate the packet

- Load the packet JSON and confirm it conforms to the `ApplicationPacket` schema.
- Confirm required paths exist: `resume_path`, `applicant_answers_path`, `job_snapshot_path`, `screening_decision_path`.
- If `cover_letter_status == "approved"`, confirm `cover_letter_path` exists.
- If any required file is missing, do not attempt the application. Record a failure result and move on.

### 2. Confirm context before navigating

Before opening the browser, note:

- `apply_url` - where to navigate
- `ats_type` - one of `linkedin_easy_apply`, `greenhouse`, `workday`, `other`
- `trust_tier` - A / B / C
- `submit_policy` - controls whether submission is allowed
- `escalation_policy` - retry limits, escalation thresholds
- `cover_letter_status` - whether a cover letter is attached, needed, or not required

### 3. Fill application fields

Fill form fields using only:

- the application packet
- `applicant_master_answers.md`
- the approved cover letter, if attached

Do not invent answers. Do not infer facts that are not grounded in the packet or master answers. Unsupported freeform/essay questions trigger escalation (see `escalation_policy.md`).

For field-matching logic and retry limits, follow `escalation_policy.md`.

### 4. Apply ATS-specific handling

Consult `ats_playbooks.md` for compact guidance on:

- LinkedIn Easy Apply
- Greenhouse
- Workday

For `other` / unknown ATS: never auto-submit; treat as Tier C.

### 5. Attempt allowed field corrections

For fixable mismatches (date formats, resume parser damage, upload widget quirks, Workday field-mapping drift), attempt corrections within the retry limits defined in `escalation_policy.md`. Workday in particular expects a correction pass before escalation.

### 6. Escalate when required

Escalate immediately on any of:

- signup/account creation required
- captcha
- OTP or email/SMS verification
- missing required answer (legal/work-authorization, essay, freeform) not covered by packet or master answers
- suspicious or unknown domain
- missing required document
- required cover letter with no approved cover letter available

See `escalation_policy.md` for the full list and try-then-escalate cases.

On escalation:

1. Capture a screenshot of the blocking state.
2. Record the current URL.
3. Create an `InterventionReport` using typed enums for `issue_type` and `required_human_action` (no prose-only suggestions).
4. Move the packet to the appropriate waiting queue.
5. Continue to the next packet.

### 7. Cover letter discovered mid-application

If you discover a required cover letter mid-application and none is approved:

1. Stop work on the current application immediately.
2. Save current progress (screenshots, notes).
3. Mark the packet `cover_letter_status = required_discovered_mid_apply`.
4. Create the cover-letter draft request / intervention.
5. Move the packet to `waiting_for_cover_letter_approval`.
6. Remove the packet from the active browser queue.
7. Continue to the next packet.

This path must never block the rest of the queue.

### 8. Pre-submit audit

Before clicking submit, run the full checklist in `submission_audit_checklist.md`. If any item fails, do not submit - escalate or create a review request per the packet's `submit_policy`.

### 9. Submit only if policy allows

Honor `submit_policy`:

- `auto` - submit
- `manual` - stop at submit, capture screenshot, create review request
- `require_approval` - create review request, move packet to `waiting_for_human_review`, do not submit

Defaults by ATS are defined in `ats_playbooks.md` and `config/runtime.json`.

### 10. Save artifacts

Follow `artifact_logging.md`. Capture screenshots before submit, at any review/confirmation page, after submit, and on errors. Save a PDF of the confirmation when practical. Never store passwords, OTP codes, tokens, or session credentials.

### 11. Return a structured run result

Emit a `RunLog`-compatible result:

- `run_id`
- `packet_id`
- `worker = "cowork"`
- `started_at`, `finished_at`
- `result` - `completed` | `escalated_signup` | `escalated_cover_letter` | `escalated_other` | `failed`
- `confirmation_number` (if available)
- `escalation_reason` (if escalated)
- `notes`
- `screenshot_paths`
- `pdf_path`

This result triggers the downstream logging workflow (`05_log_completed_application`) and the Google Sheets update.

## What this Skill is not

This Skill is one broad playbook. Reading the packet, escalation, signup handling, submission audit, artifact logging, field correction, and queue transitions are **sections of this procedure**, not separate Skills. Do not invoke or reference them as standalone Skills.

## Future optional splits (TODO - do not implement yet)

Future versions may split out ATS-specific or recovery-specific Skills only if this main Skill grows too long, ATS behavior clearly diverges, Claude starts mixing up platform-specific instructions, or resuming from interrupted applications becomes a common workflow:

- `workday_application/SKILL.md`
- `greenhouse_application/SKILL.md`
- `linkedin_easy_apply/SKILL.md`
- `application_recovery/SKILL.md`

Do not create these until the complexity justifies it.
