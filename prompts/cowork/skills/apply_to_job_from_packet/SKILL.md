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
- Access to `job-automation/config/applicant/applicant_master_answers.md`
- Access to `job-automation/config/runtime.json`

## Procedure

### 1. Read and validate the packet

- Load the packet JSON and confirm it conforms to the `ApplicationPacket` schema.
- Confirm required paths exist: `resume_path`, `applicant_answers_path`, `job_snapshot_path`, `screening_decision_path`.
- If `cover_letter_path` is set, confirm the file exists.
- If any required file is missing, do not attempt the application. Record a failure result and move on.

### 2. Confirm context before navigating

Before opening the browser, note:

- `apply_url` - where to navigate
- `ats_type` - one of `linkedin_easy_apply`, `greenhouse`, `workday`, `other`
- `trust_tier` - A / B / C
- `submit_policy` - controls whether submission is allowed
- `escalation_policy` - retry limits, escalation thresholds
- `cover_letter_path` - non-null if an approved cover letter is attached

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

For `other` / unknown ATS: behavior is governed entirely by the packet's `submit_policy`. Do not apply hardcoded ATS-specific overrides at runtime.

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
- cover letter field present in the form (including fields labeled "optional") with no approved cover letter available — treat any cover letter input the form accepts as mandatory

See `escalation_policy.md` for the full list and try-then-escalate cases.

On escalation:

1. Record the current URL.
2. Create an `InterventionReport` using typed enums for `issue_type` and `required_human_action` (no prose-only suggestions).
3. Move the packet to the appropriate waiting queue.
4. Continue to the next packet.

### 7. Cover letter discovered mid-application

A cover letter is "discovered" whenever the form offers any field that accepts one — a textarea, a file upload, or a link — regardless of whether the form labels it required or optional. If the form will accept a cover letter, treat it as mandatory.

If you discover a cover letter field mid-application and none is attached (`cover_letter_path` is null):

1. Stop work on the current application immediately.
2. Save current progress notes.
3. Create the cover-letter draft request / intervention.
4. Move the packet to `waiting_for_cover_letter_approval`.
5. Remove the packet from the active browser queue.
6. Continue to the next packet.

The drafter cron will pick the packet up, generate a letter, set `cover_letter_path`, and transition it back to `ready_to_apply` for a fresh attempt.

This path must never block the rest of the queue.

### 8. Pre-submit audit

Before clicking submit, run the full checklist in `submission_audit_checklist.md`. If any item fails, do not submit - escalate or create a review request per the packet's `submit_policy`.

### 9. Submit only if policy allows

Honor `submit_policy` (two booleans on the packet):

- `auto_submit_allowed: true` AND `human_approval_required: false` → submit.
- `human_approval_required: true` → create a review request, move packet to `waiting_for_human_review`, do not submit.
- `auto_submit_allowed: false` (and `human_approval_required: false`) → create a review request, move packet to `waiting_for_human_review`, do not submit.

These booleans are computed at packet build time from `job-automation/config/runtime.json` based on the packet's `ats_type`. Do not override based on the ATS at runtime.

### 10. Save artifacts

Follow `artifact_logging.md`. Never store passwords, OTP codes, tokens, or session credentials.

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

This result triggers the downstream logging workflow (`05_log_completed_application`) and the Google Sheets update.

### 12. Close the browser tab

After the run log is written and the packet has been transitioned to its terminal queue, close the browser tab opened for this application before moving on. The next packet should open a fresh tab.

This applies to every outcome — successful submission, escalation, mid-apply cover-letter discovery, or failure — so tabs do not accumulate across a long queue drain.

## What this Skill is not

This Skill is one broad playbook. Reading the packet, escalation, signup handling, submission audit, artifact logging, field correction, and queue transitions are **sections of this procedure**, not separate Skills. Do not invoke or reference them as standalone Skills.

## Future optional splits (TODO - do not implement yet)

Future versions may split out ATS-specific or recovery-specific Skills only if this main Skill grows too long, ATS behavior clearly diverges, Claude starts mixing up platform-specific instructions, or resuming from interrupted applications becomes a common workflow:

- `workday_application/SKILL.md`
- `greenhouse_application/SKILL.md`
- `linkedin_easy_apply/SKILL.md`
- `application_recovery/SKILL.md`

Do not create these until the complexity justifies it.
