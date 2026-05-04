# Prompts

## Schema Roles

Prompts are categorized by the type of output they produce:

| Schema | Role | Strictness |
|--------|------|------------|
| ScreeningDecision | AI-output | Strict (additionalProperties: false, evidence required for rejects) |
| InterventionReport | AI/Worker-output | Strict (typed enums for issue_type and required_human_action) |
| NormalizedJob | Code-generated | Storage only (no AI output) |
| ApplicationPacket | Code-generated | Storage only (no AI output) |
| RunLog | Runtime log | Typed enums for result and issue_type |

## Screening Prompt

Located in `prompts/screening/`

### Purpose
Enforce hard-reject filtering with a strict apply-by-default policy.

### Key Directives
- Default to APPLY unless a configured hard rule clearly triggers
- Reject ONLY when a hard rule is clearly matched
- **Provide evidence for rejections** - grounded in posting text
- Ignore "preferred" qualifications
- Never escalate screening to a human
- Output strict JSON schema with no extra properties

### Evidence Requirement
For any rejection, the `evidence` array must contain:
- Short strings quoting or referencing specific text from the job description
- Direct references to what triggered the rule

### Anti-Fabrication Rules
- Do not infer values unless grounded in posting
- Use `unknown` when unclear
- Do not output fields not in schema
- Never fabricate quotes

### Factor Output Fields (always required)

Every factor's audit output field is **always required** on every screening decision, regardless of whether the factor appears in `enabled_factors`. `enabled_factors` only controls whether a factor's rule may *trigger a rejection*; the categorization is captured in all cases for downstream auditing and dashboard breakdowns. The response schema is built by `build_response_schema()` in `screen_jobs.py` and includes:

| Factor | Output field | Type | Notes |
|---|---|---|---|
| `role_domain` | `role_domain` | enum | One of the headings in `approved_role_domains.md`, or `"unknown"`. |
| `industry` | `industry` | enum | One of the headings in `approved_industries.md`, or `"unknown"`. |
| `experience` | `experience_years_required` | integer or null | Hard-required years from the posting; null if unspecified or only "preferred". |

The system prompt (assembled by `build_system_prompt(enabled_factors)`) always includes **every** factor section so the model has the categorization instructions it needs. The `{{active_reject_factors}}` placeholder in `core.md` is replaced with the comma-separated `enabled_factors` list, and the model is instructed to only reject based on factors named there.

The storage schema (`schemas/screening_decision.schema.json`) makes these three fields **required**. Synthetic rejections from the location prefilter (`screen_location_prefilter`) skip the LLM call and therefore can't categorize — they populate sentinel values (`role_domain="unknown"`, `industry="unknown"`, `experience_years_required=null`) so the schema is still satisfied. Historical decisions written before this change won't validate against the strict schema; re-screen if you need their audit data.

Adding a new factor's output field: implement `_factor_field_spec(name)` in `screen_jobs.py` (return `field`, `schema`, and `unknown` sentinel), add an "Output field" section to the factor's `.md`, add the field to the required list and properties of `screening_decision.schema.json`.

### Examples of REJECT (with evidence)
- "Requires 3+ years" → Evidence: `["Requires 3+ years of experience (max allowed: 1)"]`
- "Senior Software Engineer" → Evidence: `["Title contains 'Senior': Senior Software Engineer"]`
- "Food Safety Compliance Analyst" (with `reject_if_role_not_in_approved_domains` enabled) → Evidence: `["Title 'Food Safety Compliance Analyst' does not fit any approved domain"]`

### Examples of APPLY
- "1-3 years preferred" → No evidence needed, apply by default
- "Ideally has X" → No hard rule triggered

### Approved Role Domains rule

The `reject_if_role_not_in_approved_domains` rule (in `config/search/reject_rules.json`) gates the screener on whether the role itself fits one of the categories listed in `config/search/approved_role_domains.md`. The markdown file is loaded by `screen_jobs.py` and injected into the user prompt as `{{approved_role_domains}}`.

Behavior:
- Categories are inclusive. Any role plausibly within a category is approved, even if its specific specialization is not in the examples.
- The examples under each category are illustrative, not exhaustive. The model is instructed not to require an exact title match.
- The company's industry does **not** decide the outcome. A SWE role at a food-delivery company is approved; a food-safety analyst role at a tech company is not.
- When uncertain, default to APPLY (volume-first).
- Rejections under this rule must include evidence quoting or referencing the title/description text that establishes the role's domain.

To adjust scope:
- Edit `config/search/approved_role_domains.md` — add/remove a category, or expand examples to nudge the model on borderline cases.
- Set `reject_if_role_not_in_approved_domains` to `false` in `reject_rules.json` to disable the rule entirely without changing the prompt.

The current categories are Software Engineering, IT / Systems, and Cybersecurity.

### Approved Industries rule

The `reject_if_industry_not_in_approved` rule (in `config/search/reject_rules.json`) gates the screener on whether the **company's industry** fits one of the categories listed in `config/search/approved_industries.md`. The markdown file is loaded by `screen_jobs.py` and injected into the user prompt as `{{approved_industries}}`. The factor is opt-in via `enabled_factors` and is disabled by default.

Behavior:
- Categories are inclusive. Any company plausibly within a category is approved, even if its specific niche is not in the examples.
- The role itself does **not** decide the outcome. A finance role at a tech company is approved (the company is Technology); a SWE role at a food-delivery company is rejected if food delivery does not fit any approved industry.
- When uncertain, default to APPLY (volume-first).
- Rejections under this rule must include evidence quoting or referencing the company name or description text that establishes the company's industry.

To adjust scope:
- Edit `config/search/approved_industries.md` — add/remove a category, or expand examples to nudge the model on borderline cases.
- Add `"industry"` to `enabled_factors` in `reject_rules.json` to enable the factor's prompt fragment, and set `reject_if_industry_not_in_approved` to `true` to actually reject on it.

The current categories are Technology, Healthcare, Finance, Education, and Government / Public Sector.

## Cover Letter Prompt

Located in `prompts/cover_letter/`

### Purpose
Generate concise, plausible cover letter drafts based on the user's corpus material.

### Key Directives
- Use existing cover-letter corpus as style/material source
- Tailor modestly to the specific job
- Never invent experience
- Keep it concise (3-4 paragraphs)
- Mark as requiring approval

## Cowork Master Operator Prompt

Located in `prompts/cowork/master_operator.md`

### Purpose
Instruct Claude Cowork on browser automation behavior.

### Key Directives
- Read application packet first
- Fill ONLY from packet and applicant answers
- Respect submit policy per ATS type
- Stop on escalation triggers (signup, captcha, OTP)
- Generate structured intervention reports with typed enums

### Intervention Reports
Use typed enums instead of prose:
- `issue_type`: signup_required, captcha, otp_required, etc.
- `required_human_action`: create_account, solve_captcha, etc.

Do not invent suggested actions in prose.

## Cowork Skills

Located in `prompts/cowork/skills/`

A Skill is a reusable playbook, not a tiny function. For v1 there is one Skill.

### `apply_to_job_from_packet/`

End-to-end browser-worker procedure: read a packet, fill the application, branch on ATS specifics, handle escalations, run the submission audit, optionally submit, save artifacts, and return a structured run result.

Files:

- `SKILL.md` - the main procedure
- `escalation_policy.md` - immediate vs. try-then-escalate rules and retry limits
- `submission_audit_checklist.md` - pre-submit verification steps
- `artifact_logging.md` - what to save, what never to store
- `ats_playbooks.md` - compact per-ATS guidance (LinkedIn Easy Apply, Greenhouse, Workday, other)

Packet reading, escalation, signup handling, submission audit, artifact logging, field correction, and queue transitions are **sections of this Skill**, not separate Skills. Do not reintroduce them as standalone Skill files.

### Future optional splits (TODO, not implemented)

Only split these out if the main Skill becomes too long, ATS behavior clearly diverges, Claude starts mixing up platform-specific instructions, or resuming from interrupted applications becomes a common workflow:

- `workday_application/SKILL.md`
- `greenhouse_application/SKILL.md`
- `linkedin_easy_apply/SKILL.md`
- `application_recovery/SKILL.md`
