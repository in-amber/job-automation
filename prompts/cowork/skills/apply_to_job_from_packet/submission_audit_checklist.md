# Submission Audit Checklist

Supporting reference for `apply_to_job_from_packet/SKILL.md`. Run this checklist immediately before clicking submit. If any item fails, do not submit - escalate or create a review request per `submit_policy`.

## Pre-submit checks

- [ ] Company on the page matches `packet.company`.
- [ ] Title on the page matches `packet.title`.
- [ ] Application URL / domain matches the expected target from `packet.apply_url`.
- [ ] Resume uploaded correctly (file name and preview match the resume at `packet.resume_path`).
- [ ] Cover letter uploaded when the packet requires one, or omitted when the packet says it's not needed. Never upload an unapproved draft.
- [ ] All required fields are filled. No empty required fields, no error indicators, no validation warnings.
- [ ] No invented facts or unsupported answers entered - every field value traces back to packet or master answers.
- [ ] `submit_policy` is checked and permits submission (`auto`). If `manual` or `require_approval`, stop here and create a review request instead.

## Submission capture

When submission proceeds and completes:

- [ ] Confirmation number or ID extracted, if present.

## Review-request path

If `submit_policy == "require_approval"`:

1. Stop at the submit button - do not click it.
2. Create a review request.
3. Move the packet to `waiting_for_human_review`.
