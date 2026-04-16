# Google Sheets Schema

This document defines the structure for the Google Sheets audit log.

## Sheet Setup

Create a Google Sheet with four tabs. Share it with your service account email (found in your credentials JSON).

---

## Tab: applications

Track all application attempts.

| Column | Type | Description |
|--------|------|-------------|
| application_id | string | Packet ID |
| date_found | datetime | When job was discovered |
| date_applied | datetime | When application was submitted |
| company | string | Company name |
| title | string | Job title |
| location | string | Job location |
| source | string | Where job was found (linkedin, greenhouse, etc.) |
| source_url | url | Original job posting URL |
| apply_url | url | Application URL |
| ats_type | string | ATS classification |
| status | string | Current status |
| submission_mode | string | auto, manual, or require_approval |
| cover_letter_used | string | Yes/No |
| artifact_folder | string | Packet ID for finding artifacts |
| confirmation_number | string | Application confirmation if received |
| notes | string | Additional notes |

---

## Tab: rejections

Track hard-rejected jobs.

| Column | Type | Description |
|--------|------|-------------|
| job_id | string | Job ID |
| date_screened | datetime | When screening occurred |
| company | string | Company name |
| title | string | Job title |
| source_url | url | Job posting URL |
| reject_rule | string | Rule(s) that triggered rejection |
| reason_summary | string | Explanation of rejection |
| job_snapshot_path | string | Path to local job file |

---

## Tab: interventions

Track escalations requiring human attention.

| Column | Type | Description |
|--------|------|-------------|
| packet_id | string | Packet ID |
| company | string | Company name |
| title | string | Job title |
| issue_type | string | Type of issue |
| issue_summary | string | Description of issue |
| status | string | open, resolved, abandoned |
| created_at | datetime | When issue was created |
| resolved_at | datetime | When issue was resolved |

---

## Tab: runs

Track browser worker execution logs.

| Column | Type | Description |
|--------|------|-------------|
| run_id | string | Run ID |
| packet_id | string | Packet ID |
| started_at | datetime | When run started |
| finished_at | datetime | When run finished |
| worker | string | Worker identifier |
| result | string | Outcome of run |
| escalation_reason | string | Why escalated (if applicable) |
| confirmation_number | string | Confirmation if received |
| log_path | string | Path to local log file |

---

## Issue Types

For the `interventions` tab:

- `signup_required` - Account creation needed
- `captcha` - Captcha encountered
- `otp_verification` - OTP/verification needed
- `work_authorization_unclear` - Ambiguous legal question
- `essay_required` - Essay question without answer
- `unknown_domain` - Untrusted domain
- `missing_document` - Required document not available
- `field_mismatch` - Form field issues
- `upload_failed` - File upload problems
- `other` - Other issues

## Run Results

For the `runs` tab:

- `completed` - Successfully submitted
- `completed_pending_review` - Ready but awaiting manual submit
- `escalated_signup` - Stopped for signup
- `escalated_cover_letter` - Stopped for cover letter
- `escalated_other` - Stopped for other reason
- `failed` - Application failed
