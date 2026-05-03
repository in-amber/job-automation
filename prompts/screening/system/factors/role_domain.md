## Approved Role Domains

The reject rule `reject_if_role_not_in_approved_domains` rejects roles that do not plausibly fit any of the approved role categories listed below.

Apply this rule as follows:
- A role is approved if it plausibly fits **any** category, even if the specific specialization is not listed in that category's examples.
- Category examples are illustrative, not exhaustive. Do not require an exact title match — a role that clearly belongs to the category's general scope is approved.
- The company's industry does NOT determine the outcome. A software engineering role at a food-delivery company is approved; a food-safety analyst role at a tech company is not.
- When uncertain whether a role fits a category, **apply** (volume-first default).
- Reject only when the role clearly does not fit any approved category (e.g., food compliance, retail operations, healthcare administration, marketing, finance roles unrelated to security/IT/software).

Example:
- "Food Safety Compliance Analyst" with no software/security/IT framing → REJECT (does not fit any approved domain)

For a rejection under this rule, the `evidence` field must quote or reference the title/description text that establishes the role's domain.

The approved categories are:

{{approved_role_domains}}
