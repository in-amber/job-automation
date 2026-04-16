# Skill: Submission Audit

## Purpose
Verify application state before submission and create an audit trail.

## Pre-Submit Checklist

Before clicking submit, verify:

1. **All required fields filled**
   - No error indicators visible
   - No empty required fields

2. **Documents uploaded**
   - Resume upload confirmed
   - Cover letter uploaded (if required and approved)

3. **Submit policy allows**
   - Check packet.submit_policy
   - Check runtime config for ATS type

4. **No obvious errors**
   - Form validation passed
   - No warning messages

## Screenshot Protocol

Capture screenshots at these points:
1. Completed form before submit
2. Any review/confirmation page
3. Final confirmation after submit
4. Any error messages

Save to: `artifacts/screenshots/{{packet_id}}/`

Naming: `{{timestamp}}_{{step}}.png`

## Confirmation Capture

After successful submission:
1. Look for confirmation number/ID
2. Extract and save it
3. Screenshot the confirmation page
4. Try to save/print as PDF if available

## Run Log Entry

Create run log with:
- run_id: Generated UUID
- packet_id: From packet
- worker: "cowork"
- started_at: When application began
- finished_at: Current time
- result: "completed" or appropriate status
- confirmation_number: If found
- screenshot_paths: Array of saved screenshots
- pdf_path: If PDF was saved

## Manual Review Flow

If submit_policy is "require_approval":
1. Stop at the submit button
2. Screenshot the ready-to-submit state
3. Create a review request
4. Move packet to `waiting_for_human_review`
5. Do NOT click submit
