# Cowork Skills Spec Patch

## Purpose

Revise the Cowork Skills plan in the job application automation spec.

The current skill plan is too atomic. It treats Claude Skills like individual functions or tiny workflow steps. For this project, Skills should represent repeatable playbooks or substantial workflows, not simple actions such as reading a packet, escalating to a human, or saving artifacts.

## Problem with the current plan

The existing spec uses this structure:

```text
prompts/cowork/skills/
  read_application_packet.md
  fill_structured_form.md
  handle_signup_escalation.md
  submission_audit.md
  save_artifacts_and_log.md
```

This is too granular.

These are not good standalone Skills:

- reading the application packet
- escalating to a human
- saving artifacts
- checking whether submission is allowed
- detecting signup
- detecting captcha
- writing a run log

Those are steps inside a broader browser-execution workflow.

## Better principle

A Claude Skill should be a reusable operating procedure or playbook.

For this project, the right first Skill is:

```text
apply_to_job_from_packet
```

This Skill should cover the full browser-worker process from reading a packet to filling the application, handling branches/escalations, optionally submitting, saving artifacts, and returning a structured result.

## Required replacement

Replace this:

```text
prompts/cowork/skills/
  read_application_packet.md
  fill_structured_form.md
  handle_signup_escalation.md
  submission_audit.md
  save_artifacts_and_log.md
```

With this:

```text
prompts/cowork/skills/
  apply_to_job_from_packet/
    SKILL.md
    escalation_policy.md
    submission_audit_checklist.md
    artifact_logging.md
    ats_playbooks.md
```

## Main Skill behavior

The main `apply_to_job_from_packet/SKILL.md` should cover the full browser-worker procedure.

It should instruct Cowork to:

1. Read and validate the application packet.
2. Confirm the apply URL, ATS type, trust tier, and submit policy.
3. Fill application fields using only the packet and applicant master answers.
4. Apply ATS-specific handling for:
   - LinkedIn Easy Apply
   - Greenhouse
   - Workday
5. Attempt allowed field corrections, especially for Workday.
6. Escalate on:
   - signup required
   - captcha
   - OTP/email/SMS verification
   - missing required answers
   - suspicious domains
   - required cover letter with no approved cover letter available
7. If a cover letter is discovered mid-application:
   - stop work on the current application
   - create the appropriate intervention or cover-letter request
   - move the packet out of the active queue
   - continue to the next packet
8. Before submission, run the submission audit checklist.
9. Submit only if the packet’s submit policy allows it.
10. Save artifacts.
11. Return a structured run result.

## Supporting files

### `escalation_policy.md`

This file should contain the escalation rules, including:

Immediate escalation on:

- signup required
- captcha
- OTP/email/SMS verification
- ambiguous legal or work authorization question not clearly covered
- essay/freeform answer not available in the packet
- unknown suspicious domain
- missing required document
- required cover letter with no approved cover letter

Try-then-escalate on:

- field label mismatch
- date formatting mismatch
- resume parser damage
- upload widget issues
- broken Workday field mapping

Retry limits:

- max 2 retries per field
- max 3 minutes on one unresolved issue
- after that, generate an intervention report and move on

### `submission_audit_checklist.md`

This file should contain the pre-submit checklist:

- company matches packet
- title matches packet
- application URL/domain matches expected target
- resume uploaded correctly
- cover letter uploaded or omitted according to packet
- required fields completed
- no unsupported facts invented
- submit policy checked
- final submission confirmation captured when practical

### `artifact_logging.md`

This file should explain what artifacts to save:

- confirmation page details
- run notes
- intervention report, if blocked
- final structured result

Do not store:

- passwords
- OTP codes
- raw authentication tokens
- sensitive browser credentials

### `ats_playbooks.md`

This file should include compact ATS-specific guidance.

#### LinkedIn Easy Apply

- Treat as trusted v1 automated flow.
- May auto-submit if config allows.
- Should still avoid inventing unsupported answers.
- If unexpected multi-step questions appear and required answers are missing, escalate.

#### Greenhouse

- Treat as trusted structured ATS.
- Fill from packet and applicant answers.
- Submit only if config allows.
- Escalate for missing required answers, signup/account issues, or unusual fields.

#### Workday

- Treat as trusted but more error-prone.
- Attempt to correct resume parsing issues before escalating.
- Re-check education and work history fields carefully.
- Escalate if field mapping remains broken after retry limits.

## What should not be separate Skills

Do not create separate Skills for:

- reading packets
- escalation
- signup handling
- submission audit
- artifact logging
- field correction
- queue transition

These should be sections or supporting references inside `apply_to_job_from_packet`.

## Future optional Skill split

Do not split these out yet, but add TODO notes that future versions may introduce:

```text
prompts/cowork/skills/
  workday_application/
    SKILL.md

  greenhouse_application/
    SKILL.md

  linkedin_easy_apply/
    SKILL.md

  application_recovery/
    SKILL.md
```

Only split them out later if:

- the main skill becomes too long
- ATS-specific behavior clearly diverges
- Claude starts mixing up platform-specific instructions
- resuming from interrupted applications becomes a common workflow

## Required code/doc updates

Update any repo files that reference the old atomic skill files.

Likely files to update:

- `SPEC.md`, if present
- `README.md`
- `docs/prompts.md`
- `docs/architecture.md`
- `docs/workflow-spec.md`
- any tests or scripts that expect the old skill file paths
- any prompt-loading utilities that assume `prompts/cowork/skills/*.md` instead of skill directories

## Acceptance criteria

This patch is complete when:

1. The old atomic Cowork skill files are removed or replaced.
2. The new `apply_to_job_from_packet/` Skill directory exists.
3. `SKILL.md` describes the full browser-worker workflow.
4. Escalation, submission audit, artifact logging, and ATS handling are support files inside the skill directory.
5. No docs or code still describe escalation, packet reading, or artifact saving as standalone Skills.
6. Future ATS-specific Skills are mentioned only as optional TODOs, not implemented prematurely.

## Summary

The desired design is:

- one broad Cowork Skill for v1
- supporting policy/checklist/playbook files inside that Skill
- no tiny function-like Skills
- optional ATS-specific Skills only after real workflow complexity justifies them
