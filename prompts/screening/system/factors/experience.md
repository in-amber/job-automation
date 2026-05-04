## Experience Factor

You must **always** extract the minimum years of relevant experience the posting hard-requires (or `null`) and output it in the `experience_years_required` field — see "Output field" below. This is required regardless of whether `experience` appears in the active reject factors list.

### Years of Experience rule

The reject rule `max_required_years_experience` sets the maximum number of years of relevant experience the job may explicitly require. If a posting clearly requires more than the configured maximum, reject. **Only trigger this rejection when `experience` is in the active reject factors list above.**

Apply this rule only to **hard requirements**, not preferences:
- "Requires 5+ years of experience" with max = 1 → REJECT
- "Minimum 3 years required" with max = 1 → REJECT
- "3+ years preferred" → APPLY (preferred is not required)
- "Ideally 5 years of experience" → APPLY (ideal is not required)
- Unspecified or ambiguous experience requirements → APPLY

For a rejection, the `evidence` field must quote the specific years requirement from the posting.

### Output field: `experience_years_required` (always required)

Output `experience_years_required` as an integer giving the minimum years of relevant experience the posting **hard-requires**. If the posting does not state a hard requirement (e.g., "preferred", "ideally", or unspecified), output `null`. Provide this field on every decision — `apply` or `reject` — regardless of whether `experience` is in the active reject factors list.

### Seniority rule

The reject rule `reject_senior_titles` rejects jobs whose **title** indicates a senior-level role. The `senior_title_keywords` list defines which keywords trigger this rule. **Only trigger this rejection when `experience` is in the active reject factors list above.**

Apply this rule **only to the job title**. The presence of a senior keyword in the description body (e.g., "you'll work alongside senior engineers") does NOT trigger this rule — only the title itself matters.

- Title: "Senior Software Engineer" with `senior` in keywords → REJECT
- Title: "Staff Engineer" with `staff` in keywords → REJECT
- Title: "Software Engineer II" → APPLY (no senior keyword in title)
- Title: "Engineer" with description mentioning senior team members → APPLY (description doesn't count)

For a rejection, the `evidence` field must quote the job title.
