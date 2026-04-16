# Screening User Template

Screen the following job posting against the configured reject rules.

## Job Posting

**Job ID**: {{job_id}}
**Company**: {{company}}
**Title**: {{title}}
**Location**: {{location}}
**Source**: {{source}}

### Description

{{description_clean}}

---

## Configured Reject Rules

{{reject_rules_json}}

## Applicant Target Titles

{{titles_list}}

## Search Filters

{{search_filters_json}}

---

## Instructions

1. Analyze the job posting against each reject rule
2. Determine if any rule is CLEARLY triggered
3. If uncertain about any rule, default to APPLY
4. For rejections, provide direct evidence from the posting text
5. Assess cover letter signal based on explicit posting language only

Remember:
- Default to APPLY unless a hard rule clearly triggers
- Rejections require evidence grounded in posting text
- Use `unknown` for cover_letter_signal if unclear
- Do not fabricate or infer information not in the posting

Output a JSON object matching the ScreeningDecision schema.
