# Artifact Logging

Supporting reference for `apply_to_job_from_packet/SKILL.md`. Defines what to save from every application attempt and what must never be stored.

## Save

### Confirmation details

- Confirmation number or ID extracted from the confirmation page.
- URL of the confirmation page.

### Run notes

- Brief notes on anything non-obvious during the run (field corrections made, retries used, unusual behavior observed).

### Intervention report (if blocked)

- Save to `job-automation/data/run_logs/interventions/`.
- Use the typed enum schema (see `escalation_policy.md`).

### Final structured result

- `RunLog`-compatible JSON saved to `job-automation/data/run_logs/`.
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

Saving the run log is what gets the application into Google Sheets. A cron job inside the project's Docker container runs `update_google_sheet.py --sync-all` every 5 minutes, picks up any new run logs, and appends them to the audit Sheet's `applied`, `runs`, and `interventions` tabs. The sync is idempotent via `job-automation/data/.sheets_synced.json`, so duplicate writes are safe but missing the run log entirely loses the audit trail. Do not skip the final write.
