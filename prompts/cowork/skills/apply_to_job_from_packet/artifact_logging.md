# Artifact Logging

Supporting reference for `apply_to_job_from_packet/SKILL.md`. Defines what to save from every application attempt and what must never be stored.

## Save

### Screenshots

- Location: `artifacts/screenshots/{packet_id}/`
- Naming: `{YYYYMMDD_HHMMSS}_{step}.png`
- Capture points:
  - form completed, before submit
  - any review/confirmation page
  - final confirmation after submit
  - any blocking error or escalation state

### PDFs (when practical)

- Location: `artifacts/pdfs/{packet_id}/`
- Naming: `{company}_{title}_{date}.pdf`
- Save a PDF of the confirmation page when the browser supports it.

### Confirmation details

- Confirmation number or ID extracted from the confirmation page.
- URL of the confirmation page.

### Run notes

- Brief notes on anything non-obvious during the run (field corrections made, retries used, unusual behavior observed).

### Intervention report (if blocked)

- Save to `data/run_logs/interventions/`.
- Use the typed enum schema (see `escalation_policy.md`).

### Final structured result

- `RunLog`-compatible JSON saved to `data/run_logs/`.
- Shape defined in `apply_to_job_from_packet/SKILL.md` step 11.

## Never store

- passwords
- OTP codes
- raw authentication tokens
- browser session cookies or credentials
- any secret copied from the page

## Cleanup

- Remove temporary files after the run.
- Use paths relative to the project root in logs and reports.
- Validate any JSON written (`RunLog`, `InterventionReport`) against its schema before finalizing.

## Downstream

Saving the run log and artifacts is what triggers `05_log_completed_application` in n8n, which updates Google Sheets. Do not skip the final write.
