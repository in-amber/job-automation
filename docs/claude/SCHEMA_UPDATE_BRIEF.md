# Schema Update Brief for Claude Code

Update the existing repository to tighten the JSON schemas and any dependent code so the pipeline is less likely to hallucinate or fabricate values.

Do **not** rebuild the project from scratch. This is a targeted refactor of the current v1 scaffold.

## Goal

Reduce schema-driven hallucination risk by:

- removing fields that invite guessing
- removing redundant fields
- ensuring each schema only includes information available at that workflow step
- separating AI-output schemas from code-generated storage schemas
- making unknown values explicit
- tightening validation rules so invalid or fabricated states are rejected early

## High-level rules

Apply these principles throughout the repo:

1. **AI-output schemas must be minimal.**
   - Only include fields the model actually needs to return.
   - Use strict enums where possible.
   - Set `additionalProperties: false`.

2. **Code-generated schemas can be richer, but should still avoid duplicated state.**
   - Do not store the same operational state in multiple places unless one is explicitly derived.
   - Prefer deriving queue state from queue location rather than storing it redundantly in packet JSON.

3. **Anything derivable should be computed by code, not guessed by AI.**
   - Example: `ats_type`, `trust_tier`, submit policy, escalation policy.

4. **Anything not actually knowable at that step must be nullable or explicitly `unknown`.**
   - Never force the model to fill a field just because the schema requires it.

5. **Rejections must be grounded.**
   - Any reject decision must include evidence from the posting.

## Required repo-wide changes

### 1. Distinguish schema roles

Update docs and code comments so schemas are clearly categorized as one of:

- **AI-output schema**
- **code-generated storage schema**
- **runtime log schema**

At minimum, apply this distinction to:

- `screening_decision.schema.json` -> AI-output
- `intervention_report.schema.json` -> AI-output or worker-output
- `normalized_job.schema.json` -> code-generated storage
- `application_packet.schema.json` -> code-generated storage
- `run_log.schema.json` -> runtime log
- `cover_letter_request.schema.json` -> code-generated storage

### 2. Tighten validators

Wherever JSON validation happens:

- enforce strict validation for AI-output objects
- reject extra properties
- add conditional validation where appropriate
- prefer `null` over empty strings for unavailable values

### 3. Update prompts and code paths

If prompts, parsers, or code paths still reference removed fields, update them.

Important:
- do not leave dead references to removed schema fields in prompts, tests, or packet builders
- do not let the model generate fields that code should compute deterministically

---

# Exact schema changes

## A. `schemas/normalized_job.schema.json`

### Intent
This is a factual, ingestion-stage object. It should not include soft inferred fields.

### Remove these fields
- `seniority_hint`
- `remote_hint`
- `requires_cover_letter_hint`

### Tighten `metadata`
If there is a generic `metadata` object, replace it with a clearer field such as:
- `source_attributes`

This field should represent copied or normalized source data, not model inference.

### Recommended shape
Use a shape equivalent to this:

```json
{
  "job_id": "string",
  "source": "string",
  "source_posting_id": "string|null",
  "fetched_at": "datetime",
  "company": "string",
  "title": "string",
  "location": "string|null",
  "employment_type": "string|null",
  "apply_url": "string",
  "source_url": "string",
  "description_raw": "string",
  "description_clean": "string|null",
  "salary_text": "string|null",
  "source_attributes": {}
}
```

### Code changes
Update any normalization code so these removed fields are no longer populated or expected.

### Tests
Add or update tests to ensure:
- `NormalizedJob` can be created without inferred hint fields
- normalization does not fail if certain source fields are missing
- extra unexpected properties are rejected if strict validation is intended

---

## B. `schemas/screening_decision.schema.json`

### Intent
This is an AI-output schema and must be especially strict.

### Remove these fields
- `hard_reject_rule_triggered`
- `confidence`

### Replace
Replace:
- `cover_letter_likely_required`

With:
- `cover_letter_signal`

Enum:
- `unknown`
- `no_signal`
- `optional_signal`
- `explicitly_required`

### Add
Add:
- `evidence` as an array of short strings grounded in the posting text

### Recommended shape
Use a shape equivalent to this:

```json
{
  "job_id": "string",
  "decision": "apply|reject",
  "matched_reject_rules": ["string"],
  "reason_summary": "string",
  "evidence": ["string"],
  "cover_letter_signal": "unknown|no_signal|optional_signal|explicitly_required",
  "generated_at": "datetime"
}
```

### Validation rules
Implement conditional validation logic:

- if `decision == "reject"`:
  - `matched_reject_rules` must be non-empty
  - `evidence` must be non-empty
- if `decision == "apply"`:
  - `matched_reject_rules` may be empty
- `additionalProperties` must be `false`

### Prompt changes
Update the screening prompt so the model is instructed to:
- default to `apply`
- reject only if a hard reject rule clearly fires
- provide supporting `evidence` for rejections
- output `cover_letter_signal` instead of guessing likelihood
- never emit removed fields

### Code changes
Update code that reads screening results so it:
- no longer expects `confidence`
- no longer expects `hard_reject_rule_triggered`
- reads `cover_letter_signal`
- treats any non-reject result as proceed/apply

### Tests
Add or update tests for:
- reject decisions require evidence
- ambiguous jobs default to `apply`
- extra keys are rejected
- `cover_letter_signal` accepts only the allowed enum values

---

## C. `schemas/application_packet.schema.json`

### Intent
This is a code-generated storage object, not an AI-output schema.

### Remove
Remove:
- `status`

Reason:
Queue state should not be duplicated in both queue location and packet JSON unless one is clearly derived. Prefer the queue location as the source of truth.

### Keep
Keep these kinds of fields:
- identifying info
- file paths
- deterministic ATS classification
- deterministic trust tier
- deterministic submit policy
- deterministic escalation policy

### Tighten policy fields
If `submit_policy` and `escalation_policy` are currently vague objects or strings, turn them into small structured objects.

Recommended shape:

```json
"submit_policy": {
  "human_approval_required": true,
  "auto_submit_allowed": false
}
```

```json
"escalation_policy": {
  "manual_signup_only": true,
  "max_field_retries": 2,
  "max_issue_minutes": 3
}
```

### Recommended shape
Use a shape equivalent to this:

```json
{
  "packet_id": "string",
  "job_id": "string",
  "company": "string",
  "title": "string",
  "location": "string|null",
  "source": "string",
  "source_url": "string",
  "apply_url": "string",
  "ats_type": "linkedin_easy_apply|greenhouse|workday|other",
  "trust_tier": "tier_a|tier_b|tier_c",
  "resume_path": "string",
  "cover_letter_status": "not_needed|predicted_needed_draft_pending|draft_ready_waiting_approval|approved|required_discovered_mid_apply",
  "cover_letter_path": "string|null",
  "applicant_answers_path": "string",
  "job_snapshot_path": "string",
  "screening_decision_path": "string",
  "submit_policy": {
    "human_approval_required": true,
    "auto_submit_allowed": false
  },
  "escalation_policy": {
    "manual_signup_only": true,
    "max_field_retries": 2,
    "max_issue_minutes": 3
  },
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

### Validation rules
Add conditional logic:
- if `cover_letter_status == "approved"`, then `cover_letter_path` must be non-null
- if `cover_letter_status != "approved"`, `cover_letter_path` may be null

### Code changes
Update packet builders and queue code so:
- packet JSON no longer stores runtime `status`
- queue placement is the authoritative runtime state
- `ats_type`, `trust_tier`, submit policy, and escalation policy are computed by code, not AI

### Tests
Add or update tests for:
- packet creation without a cover letter
- packet creation with an approved cover letter
- queue transitions do not rely on packet `status`

---

## D. `schemas/run_log.schema.json`

### Intent
This is a runtime log object. It should be structured enough to analyze later, but not invite freeform junk.

### Tighten
Replace or supplement freeform escalation text with a typed issue field.

### Add or rename
Use:
- `issue_type`

Enum:
- `signup_required`
- `captcha`
- `otp_required`
- `missing_answer`
- `cover_letter_required`
- `field_mapping_failure`
- `unknown`
- `null`

### Recommended shape
Use a shape equivalent to this:

```json
{
  "run_id": "string",
  "packet_id": "string",
  "worker": "string",
  "started_at": "datetime",
  "finished_at": "datetime|null",
  "result": "submitted|waiting_for_signup|waiting_for_cover_letter|waiting_for_human_review|failed",
  "confirmation_number": "string|null",
  "issue_type": "signup_required|captcha|otp_required|missing_answer|cover_letter_required|field_mapping_failure|unknown|null",
  "notes": "string|null"
}
```

### Validation rules
Add conditional validation where useful, for example:
- if `result == "waiting_for_signup"`, then `issue_type` should be `signup_required`

### Code changes
Update logging code to populate `issue_type` consistently and avoid depending on vague freeform escalation text.

### Tests
Add or update tests for:
- successful run logs with no issue
- signup escalation logs
- cover-letter-required logs
- nullable confirmation number handling

---

## E. `schemas/intervention_report.schema.json`

### Intent
This should classify a blockage cleanly rather than generate speculative advice.

### Replace
Replace:
- `suggested_next_action`

With:
- `required_human_action`

Enum:
- `create_account`
- `solve_captcha`
- `complete_verification`
- `approve_cover_letter`
- `answer_missing_question`
- `review_application`
- `inspect_site`

### Recommended shape
Use a shape equivalent to this:

```json
{
  "packet_id": "string",
  "issue_type": "signup_required|captcha|otp_required|missing_answer|cover_letter_required|field_mapping_failure|suspicious_site|unknown",
  "issue_summary": "string",
  "current_url": "string|null",
  "required_human_action": "create_account|solve_captcha|complete_verification|approve_cover_letter|answer_missing_question|review_application|inspect_site",
  "created_at": "datetime"
}
```

### Validation rules
- `additionalProperties` must be `false`

### Code changes
Update any intervention generation logic to classify the required human action instead of inventing prose recommendations.

### Tests
Add or update tests for:
- signup intervention reports
- captcha intervention reports
- cover-letter approval reports

---

## F. `schemas/cover_letter_request.schema.json`

### Intent
This schema was referenced in the repo structure but not clearly defined. Define it now explicitly.

### Recommended shape
Use a shape equivalent to this:

```json
{
  "packet_id": "string",
  "job_id": "string",
  "company": "string",
  "title": "string",
  "source_url": "string",
  "apply_url": "string",
  "job_snapshot_path": "string",
  "cover_letters_master_path": "string",
  "reason": "predicted_needed|discovered_mid_apply",
  "created_at": "datetime"
}
```

### Code changes
Ensure there is a single code path for generating cover-letter requests:
- when screening predicts a cover letter is needed
- when the browser worker discovers a required cover letter mid-application

### Tests
Add or update tests for both trigger conditions.

---

# Additional implementation requirements

## 1. Update docs

Update any docs that still reference removed fields:
- architecture docs
- workflow docs
- state machine docs
- prompts docs
- setup docs if relevant

## 2. Update fixtures

Update any fixture JSON files so they reflect the new schema shapes.

## 3. Update CLI / script behavior

Check all scripts that consume or emit these objects, especially:
- normalization
- screening
- packet building
- queue transitions
- cover-letter request creation
- run logging
- Google Sheets sync if it relies on removed fields

## 4. Keep AI outputs narrow

Do not let the model emit `ApplicationPacket` or `NormalizedJob`.
Those should remain code-generated.

The screening model should emit only a strict `ScreeningDecision`.

If there is an AI-generated intervention object, it must be limited to the strict `InterventionReport` schema.

## 5. Add anti-fabrication prompt language

Where relevant, update prompts to say things like:

- “Do not infer values unless explicitly required by schema and grounded in the job posting.”
- “If the posting does not provide enough information, use the allowed `unknown` enum value or leave nullable fields null.”
- “Do not output any fields not defined in the schema.”
- “For any rejection, include direct evidence from the posting.”

---

# Acceptance criteria for this update

This refactor is complete when all of the following are true:

1. The updated schemas reflect the field changes above.
2. AI-output schemas are minimal and strict.
3. Removed fields are no longer referenced by prompts, validators, or business logic.
4. Queue state no longer depends on a packet `status` field.
5. Screening rejects require evidence.
6. Unknown or unavailable values are represented safely via enums or nulls.
7. Tests pass after fixture updates.
8. No dead code remains referencing removed schema fields.

---

# Deliverables

Please make the changes directly in the repo and then summarize:

1. Which schema files changed
2. Which code files changed
3. Which prompts changed
4. Which tests were added or updated
5. Any assumptions or migration notes
