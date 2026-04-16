# Skill: Save Artifacts and Log

## Purpose
Properly save all artifacts from an application attempt and create the run log.

## Artifacts to Save

### Screenshots
- Location: `artifacts/screenshots/{{packet_id}}/`
- Naming: `{{YYYYMMDD_HHMMSS}}_{{description}}.png`
- Required screenshots:
  - Form completed (before submit)
  - Confirmation page (after submit)
  - Any errors encountered

### PDFs
- Location: `artifacts/pdfs/{{packet_id}}/`
- Naming: `{{company}}_{{title}}_{{date}}.pdf`
- Save application confirmation if browser allows

### Cover Letters Used
- Already saved in `artifacts/cover_letters/`
- Reference path in run log

## Run Log Structure

Create JSON file in `data/run_logs/`:

```json
{
  "run_id": "{{uuid}}",
  "packet_id": "{{packet_id}}",
  "worker": "cowork",
  "started_at": "{{iso_timestamp}}",
  "finished_at": "{{iso_timestamp}}",
  "result": "completed|escalated_signup|escalated_cover_letter|failed",
  "confirmation_number": "{{if_available}}",
  "escalation_reason": "{{if_escalated}}",
  "notes": "{{any_relevant_notes}}",
  "screenshot_paths": ["{{path1}}", "{{path2}}"],
  "pdf_path": "{{if_saved}}"
}
```

## Intervention Reports

If escalation occurred, save to `data/run_logs/interventions/`:

```json
{
  "packet_id": "{{packet_id}}",
  "issue_type": "{{type}}",
  "issue_summary": "{{description}}",
  "current_url": "{{url}}",
  "suggested_next_action": "{{action}}",
  "screenshot_path": "{{path}}",
  "created_at": "{{iso_timestamp}}"
}
```

## Trigger Google Sheets Update

After saving all artifacts and logs:
1. Signal completion to the logging workflow
2. This triggers 05_log_completed_application in n8n
3. Google Sheets gets updated with the run results

## Cleanup

- Remove any temporary files
- Ensure all paths are relative to project root
- Verify all JSON files are valid
