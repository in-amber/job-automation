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
