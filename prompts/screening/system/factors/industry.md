## Industry Factor

You must **always** categorize the company into one of the approved industry categories below (or `"unknown"`) and output it in the `industry` field — see "Output field" at the end of this section. This is required regardless of whether `industry` appears in the active reject factors list.

The reject rule `reject_if_industry_not_in_approved` rejects jobs whose **company's industry** does not plausibly fit any of the approved industry categories listed below. **Only trigger this rejection when `industry` is in the active reject factors list above.**

Apply this rule as follows:
- A company is approved if it plausibly fits **any** category, even if its specific niche is not listed in that category's examples.
- Category examples are illustrative, not exhaustive. Do not require an exact match — a company that clearly belongs to the category's general scope is approved.
- The role itself does NOT determine the outcome. A finance role at a tech company is approved (the company is Technology); a software engineering role at a food-delivery company is rejected if food delivery does not fit any approved industry.
- When uncertain whether the company fits a category, **apply** (volume-first default).
- Reject only when the company's industry clearly does not fit any approved category (e.g., food service, retail, hospitality, agriculture — unless they fall under one of the approved categories).

Example:
- Software Engineer at a fast-food chain with no technology framing → REJECT (company's industry does not fit any approved category)

For a rejection under this rule, the `evidence` field must quote or reference the company name or description text that establishes the company's industry.

### Output field: `industry` (always required)

Output `industry` with the exact name of the approved industry category the company fits (one of the headings listed below). If the company does not fit any approved category, use `"unknown"`. Provide this field on every decision — `apply` or `reject` — regardless of whether `industry` is in the active reject factors list.

The approved categories are:

{{approved_industries}}
