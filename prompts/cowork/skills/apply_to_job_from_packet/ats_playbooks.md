# ATS Playbooks

Supporting reference for `apply_to_job_from_packet/SKILL.md`. Compact per-ATS guidance. Consult the relevant section based on `packet.ats_type`.

## LinkedIn Easy Apply (`linkedin_easy_apply`)

- Trusted v1 automated flow.
- Auto-submit is allowed when `config/runtime.json: auto_submit_linkedin_easy_apply` is true.
- Do not invent answers. If unexpected multi-step questions appear and required answers are not in the packet or master answers, escalate.
- Resume is typically pre-attached from the LinkedIn profile; confirm it matches `packet.resume_path` before proceeding.

## Greenhouse (`greenhouse`)

- Trusted structured ATS.
- Fill from packet and master answers.
- Submit only if `config/runtime.json: auto_submit_greenhouse` is true; otherwise stop at submit per `submit_policy`.
- Escalate on missing required answers, signup/account prompts, or unusual custom fields.

## Workday (`workday`)

- Trusted but error-prone.
- Expect resume-parser damage: check education and work history fields carefully and re-enter values when parsing is wrong.
- Attempt corrections within retry limits (`escalation_policy.md`) before escalating.
- Submit only if `config/runtime.json: auto_submit_workday` is true.
- If field mapping remains broken after retry limits, create an intervention report and move on.

## Other / unknown (`other`)

- Auto-submit is allowed when `config/runtime.json: auto_submit_other` is true; the packet's `submit_policy` is the source of truth at runtime.
- Treat as trust Tier C by default for risk weighting.
- Be conservative with escalation thresholds — prefer creating a review request over attempting risky field corrections.
