# Skill: Read Application Packet

## Purpose
Load and parse an application packet to understand the job and available data before starting the application process.

## Input
- Path to application packet JSON file

## Steps

1. Read the packet JSON file
2. Validate it matches the ApplicationPacket schema
3. Extract key fields:
   - Company, title, location
   - Apply URL
   - ATS type and trust tier
   - Submit policy
   - Cover letter status and path
   - Resume path
   - Applicant answers path
4. Load the applicant master answers file
5. Load the cover letter if status is "approved"
6. Load the job snapshot for context

## Output

Structured understanding of:
- Where to apply
- What documents to use
- What answers are available
- What submission policy applies
- What escalation rules to follow

## Validation

- All required paths must exist
- Resume must be present
- If cover letter status is "approved", cover letter must exist
- ATS type must be one of: linkedin_easy_apply, greenhouse, workday, other

## Error Handling

If any required file is missing:
- Log the error
- Create intervention report
- Move packet to failed state
- Do not attempt the application
