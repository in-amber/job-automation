# Skill: Fill Structured Form

## Purpose
Fill form fields accurately using data from the application packet and master answers.

## Input
- Current form page
- Application packet data
- Applicant master answers

## Matching Logic

1. Identify all visible form fields
2. For each field, determine the best data source:
   - Check packet for job-specific data
   - Check master answers for standard fields
   - If no match found, flag for review

## Field Mapping

Common field patterns and their sources:

| Field Pattern | Source |
|---------------|--------|
| Full name, Name | FULL_NAME |
| Email | EMAIL |
| Phone, Mobile | PHONE |
| LinkedIn | LINKEDIN_URL |
| GitHub, Portfolio | GITHUB_URL, PORTFOLIO_URL |
| Location, City | LOCATION |
| Authorized to work | AUTHORIZED_TO_WORK_US |
| Require sponsorship | REQUIRE_SPONSORSHIP |
| Years of experience | YEARS_OF_EXPERIENCE |
| Current company | CURRENT_COMPANY |
| Current title | CURRENT_TITLE |
| Start date, Availability | EARLIEST_START_DATE |
| Salary, Compensation | SALARY_EXPECTATIONS |

## Handling Mismatches

If a field doesn't match any known pattern:
1. Check if it's a variation of a known field
2. Try to infer from context
3. If still unclear after 2 attempts, flag for escalation

## File Uploads

- Resume: Use path from packet.resume_path
- Cover letter: Use path from packet.cover_letter_path (only if approved)
- Other documents: Flag for escalation if required and not available

## Dropdown/Select Fields

1. Read all available options
2. Find best match for the intended value
3. If no good match, try the closest option
4. If still problematic, flag for review

## Retry Limits

- Max 2 retries per field
- Max 3 minutes on any single field issue
- After limits, create intervention report and move on
