# Skill: Handle Signup Escalation

## Purpose
Properly handle situations where account signup is required, which is forbidden in v1.

## Detection

Signup is required when you encounter:
- "Create account" or "Sign up" prompts
- "Register" buttons with no alternative
- Login walls with no guest application option
- "Already have an account?" with required account creation
- Email verification loops requiring account creation

## Immediate Actions

1. **Stop** - Do not attempt to create an account
2. **Screenshot** - Capture the current page showing the signup requirement
3. **Note URL** - Record the exact URL where signup was required

## Create Intervention Report

Use the structured schema with typed human action:

```json
{
  "packet_id": "{{packet_id}}",
  "issue_type": "signup_required",
  "issue_summary": "Application requires account creation at [site name]",
  "current_url": "{{current_url}}",
  "required_human_action": "create_account",
  "screenshot_path": "{{screenshot_path}}",
  "created_at": "{{iso_timestamp}}"
}
```

## Issue Type to Human Action Mapping

| Issue Type | Required Human Action |
|------------|----------------------|
| signup_required | create_account |
| captcha | solve_captcha |
| otp_required | complete_verification |
| cover_letter_required | approve_cover_letter |
| missing_answer | answer_missing_question |
| field_mapping_failure | review_application |
| suspicious_site | inspect_site |

## Queue Transition

1. Save the intervention report to `data/run_logs/interventions/`
2. Move packet to `waiting_for_signup` queue
3. Continue to the next packet in the ready queue

## What NOT To Do

- Do not attempt to create an account
- Do not enter any credentials
- Do not try to bypass the signup
- Do not invent suggested actions in prose - use the typed enum

## After Human Intervention

Once a human creates the account:
1. Human moves packet back to `ready_to_apply` queue
2. Packet will be picked up in next queue processing
3. Application continues from where it left off (if possible) or starts fresh
