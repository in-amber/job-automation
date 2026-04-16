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

### Cover Letter Signal
Instead of guessing, classify the signal:
- `unknown`: No clear indication
- `no_signal`: Posting suggests not needed
- `optional_signal`: Mentioned but not required
- `explicitly_required`: Explicitly stated as required

### Anti-Fabrication Rules
- Do not infer values unless grounded in posting
- Use `unknown` when unclear
- Do not output fields not in schema
- Never fabricate quotes

### Examples of REJECT (with evidence)
- "Requires 3+ years" → Evidence: `["Requires 3+ years of experience (max allowed: 1)"]`
- "Senior Software Engineer" → Evidence: `["Title contains 'Senior': Senior Software Engineer"]`

### Examples of APPLY
- "1-3 years preferred" → No evidence needed, apply by default
- "Ideally has X" → No hard rule triggered

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

Located in `prompts/cowork/`

### Purpose
Instruct Claude Cowork on browser automation behavior.

### Key Directives
- Read application packet first
- Fill ONLY from packet and applicant answers
- Respect submit policy per ATS type
- Stop on escalation triggers (signup, captcha, OTP)
- Save artifacts (screenshots, PDFs)
- Generate structured intervention reports with typed enums

### Intervention Reports
Use typed enums instead of prose:
- `issue_type`: signup_required, captcha, otp_required, etc.
- `required_human_action`: create_account, solve_captcha, etc.

Do not invent suggested actions in prose.
