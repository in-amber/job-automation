# Escalation Policy

Supporting reference for `apply_to_job_from_packet/SKILL.md`. Defines when Cowork must stop and escalate vs. attempt a fix first.

## Immediate escalation

Stop the current application immediately, capture artifacts, create an `InterventionReport`, move the packet to the appropriate waiting queue, and continue to the next packet.

Immediate triggers:

- signup or account creation required
- captcha
- OTP, email, or SMS verification
- ambiguous legal or work-authorization question not clearly covered by packet or master answers
- essay or freeform answer not available in the packet or master answers
- unknown or suspicious domain
- missing required document
- required cover letter with no approved cover letter available

## Try-then-escalate

Attempt a correction within retry limits. Escalate only if the issue is still unresolved after limits are reached.

Try-then-escalate cases:

- field label mismatch (form uses a phrase not in the master answers map)
- date formatting mismatch
- resume parser damage (uploaded resume was mis-parsed into wrong fields)
- upload widget issues (file picker misbehaves, wrong accepted types, etc.)
- broken Workday field mapping (education, work history, etc.)

## Retry limits

- max 2 retries per field
- max 3 minutes on any one unresolved issue
- after limits are exceeded, generate an intervention report and move on

## Intervention report format

Use typed enums. Do not describe the required action in prose.

Required fields:

- `packet_id`
- `issue_type` - one of the enum values defined in the `InterventionReport` schema (e.g. `signup_required`, `captcha`, `otp_required`, `cover_letter_required`, `missing_answer`, `field_mapping_failure`, `suspicious_site`)
- `issue_summary` - short human-readable description
- `current_url`
- `required_human_action` - typed enum (e.g. `create_account`, `solve_captcha`, `complete_verification`, `approve_cover_letter`, `answer_missing_question`, `review_application`, `inspect_site`)
- `screenshot_path`
- `created_at`

Save reports to `data/run_logs/interventions/`.

## Queue routing on escalation

| Trigger | Target queue |
|---|---|
| signup required | `waiting_for_signup` |
| captcha, OTP, verification | `waiting_for_human_review` |
| missing answer / freeform | `waiting_for_human_review` |
| cover letter required (no approved draft) | `waiting_for_cover_letter_approval` |
| suspicious or unknown domain | `waiting_for_human_review` |
| retry limits exceeded on form mapping | `failed` or `waiting_for_human_review` per context |

## Never do

- Do not attempt to create an account.
- Do not enter any credentials beyond an already-authenticated browser session.
- Do not attempt to bypass captcha or verification.
- Do not invent freeform answers.
- Do not describe the needed action in prose when a typed enum exists.
