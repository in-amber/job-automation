## Role Domain Factor

You must **always** categorize the role into one of the approved role-domain categories below (or `"unknown"`) and output it in the `role_domain` field — see "Output field" at the end of this section. This is required regardless of whether `role_domain` appears in the active reject factors list.

The reject rule `reject_if_role_not_in_approved_domains` rejects roles that do not plausibly fit any of the approved role categories listed below. **Only trigger this rejection when `role_domain` is in the active reject factors list above.**

Apply this rule as follows:
- A role is approved if it plausibly fits **any** category, even if the specific specialization is not listed in that category's examples.
- Category examples are illustrative, not exhaustive. Do not require an exact title match — a role that clearly belongs to the category's general scope is approved.
- The company's industry does NOT determine the outcome. A software engineering role at a food-delivery company is approved; a food-safety analyst role at a tech company is not.
- When uncertain whether a role fits a category, **apply** (volume-first default).
- Reject only when the role clearly does not fit any approved category (e.g., food compliance, retail operations, healthcare administration, marketing, finance roles unrelated to security/IT/software).

Example:
- "Food Safety Compliance Analyst" with no software/security/IT framing → REJECT (does not fit any approved domain)

For a rejection under this rule, the `evidence` field must quote or reference the title/description text that establishes the role's domain.

### Output field: `role_domain` (always required)

Output `role_domain` with the exact name of the approved role-domain category this role fits (one of the headings listed below). If the role does not fit any approved category, use `"unknown"`. Provide this field on every decision — `apply` or `reject` — regardless of whether `role_domain` is in the active reject factors list.

The approved categories are:

{{approved_role_domains}}
