#!/usr/bin/env python3
"""
Screen normalized jobs using OpenAI with hard-reject logic.

CRITICAL: This implements the volume-first screening policy.
Default is APPLY unless a hard reject rule clearly triggers.

AI-output schema: ScreeningDecision (minimal, strict)
- Rejections require evidence from the posting
"""
import argparse
import copy
import json
import os
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files, read_text
from utils.timestamps import now_iso
from utils.json_validate import validate_screening_decision


def _load_env_file() -> None:
    """Best-effort .env loader so OPENAI_API_KEY is picked up without manual export."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())

from openai import OpenAI


SYSTEM_PROMPT_DIR = PROJECT_ROOT / "prompts" / "screening" / "system"
FACTORS_DIR = SYSTEM_PROMPT_DIR / "factors"
FACTOR_PLACEHOLDER = "{{factor_sections}}"
ACTIVE_REJECT_FACTORS_PLACEHOLDER = "{{active_reject_factors}}"

APPROVED_ROLE_DOMAINS_PATH = PROJECT_ROOT / "config" / "search" / "approved_role_domains.md"
APPROVED_ROLE_DOMAINS_PLACEHOLDER = "{{approved_role_domains}}"

APPROVED_INDUSTRIES_PATH = PROJECT_ROOT / "config" / "search" / "approved_industries.md"
APPROVED_INDUSTRIES_PLACEHOLDER = "{{approved_industries}}"


def _available_factors() -> list[str]:
    """Factor fragment names in alphabetical order (deterministic prompt assembly)."""
    return sorted(p.stem for p in FACTORS_DIR.glob("*.md"))


def _parse_md_categories(md_path: Path) -> list[str]:
    """Extract '### Heading' titles from an approved-categories markdown file.

    These titles double as the enum values for the corresponding factor's
    output field, so the model is constrained to the same labels the prompt
    lists. Edits to the markdown propagate to the schema on the next run.
    """
    text = read_text(md_path)
    return re.findall(r"^###\s+(.+?)\s*$", text, flags=re.MULTILINE)


def _factor_field_spec(name: str) -> dict | None:
    """Return ``{"field": <field_name>, "schema": <fragment>, "unknown": <value>}``
    for a factor's audit output field, or ``None`` if the factor doesn't add one.

    Every factor with a spec is always included in the response schema and the
    prompt — the model categorizes every factor on every decision regardless of
    which factors are enabled for *rejection*. ``unknown`` is the sentinel used
    when the LLM never runs (e.g., the location prefilter short-circuits).

    The schema fragment is OpenAI-strict-mode compatible: no numeric bounds
    or string-length constraints. Storage-side validation is looser (any
    string / int|null) — see ``schemas/screening_decision.schema.json``.
    """
    if name == "role_domain":
        cats = _parse_md_categories(APPROVED_ROLE_DOMAINS_PATH) + ["unknown"]
        return {
            "field": "role_domain",
            "unknown": "unknown",
            "schema": {
                "type": "string",
                "enum": cats,
                "description": (
                    "Which approved role-domain category this role fits. "
                    "Use the exact category name from the Approved Role Domains "
                    "list, or 'unknown' if it does not fit any."
                ),
            },
        }
    if name == "industry":
        cats = _parse_md_categories(APPROVED_INDUSTRIES_PATH) + ["unknown"]
        return {
            "field": "industry",
            "unknown": "unknown",
            "schema": {
                "type": "string",
                "enum": cats,
                "description": (
                    "Which approved industry category the company fits. "
                    "Use the exact category name from the Approved Industries "
                    "list, or 'unknown' if it does not fit any."
                ),
            },
        }
    if name == "experience":
        return {
            "field": "experience_years_required",
            "unknown": None,
            "schema": {
                "type": ["integer", "null"],
                "description": (
                    "Minimum years of relevant experience the posting hard-requires "
                    "(not 'preferred' or 'ideally'). Use null if unspecified or ambiguous."
                ),
            },
        }
    return None


def _factor_audit_specs() -> list[dict]:
    """Audit specs for every factor that defines an output field, in stable order."""
    out = []
    for name in _available_factors():
        spec = _factor_field_spec(name)
        if spec is not None:
            out.append(spec)
    return out


def build_response_schema() -> dict:
    """Build the OpenAI structured-output schema.

    Every factor's audit field is always required regardless of whether the
    factor is enabled for *rejection*. This guarantees every screening
    decision carries the full categorization for downstream auditing and
    dashboard breakdowns.

    The base schema lives in ``prompts/screening/schema.json``; this function
    returns a deep copy with factor fields injected so the file on disk stays
    the canonical "always-present" set.
    """
    base = copy.deepcopy(read_json(PROJECT_ROOT / "prompts" / "screening" / "schema.json"))
    schema = base["schema"]
    for spec in _factor_audit_specs():
        schema["properties"][spec["field"]] = spec["schema"]
        schema["required"].append(spec["field"])
    return base


def _unknown_factor_fields() -> dict:
    """Sentinel factor-field values for decisions produced without an LLM call."""
    return {spec["field"]: spec["unknown"] for spec in _factor_audit_specs()}


def _load_factor_fragment(name: str) -> str:
    """Read a factor fragment and inject any per-factor config data it depends on."""
    fragment = read_text(FACTORS_DIR / f"{name}.md")
    if name == "role_domain":
        if APPROVED_ROLE_DOMAINS_PLACEHOLDER not in fragment:
            raise ValueError(
                f"role_domain fragment is missing required placeholder "
                f"{APPROVED_ROLE_DOMAINS_PLACEHOLDER!r}; the approved-categories list "
                f"won't reach the model."
            )
        fragment = fragment.replace(
            APPROVED_ROLE_DOMAINS_PLACEHOLDER,
            read_text(APPROVED_ROLE_DOMAINS_PATH),
        )
    if name == "industry":
        if APPROVED_INDUSTRIES_PLACEHOLDER not in fragment:
            raise ValueError(
                f"industry fragment is missing required placeholder "
                f"{APPROVED_INDUSTRIES_PLACEHOLDER!r}; the approved-industries list "
                f"won't reach the model."
            )
        fragment = fragment.replace(
            APPROVED_INDUSTRIES_PLACEHOLDER,
            read_text(APPROVED_INDUSTRIES_PATH),
        )
    return fragment


def build_system_prompt(enabled_factors: list[str]) -> str:
    """Compose the system prompt.

    All factor fragments are *always* included so the model categorizes every
    factor on every decision (audit data). ``enabled_factors`` controls which
    factors may *trigger a rejection* — that subset is injected into the core
    prompt as the active-reject-factors list, and the model is instructed to
    only reject based on factors named there.
    """
    available = set(_available_factors())
    unknown = [f for f in enabled_factors if f not in available]
    if unknown:
        raise ValueError(
            f"Unknown screening factor(s): {unknown}. "
            f"Add a fragment at {FACTORS_DIR}/<name>.md or remove from enabled_factors. "
            f"Available: {sorted(available)}"
        )

    core = read_text(SYSTEM_PROMPT_DIR / "core.md")
    fragments = [_load_factor_fragment(name) for name in _available_factors()]
    factor_block = "\n\n".join(fragments)
    active_block = ", ".join(enabled_factors) if enabled_factors else "(none)"
    return (
        core
        .replace(ACTIVE_REJECT_FACTORS_PLACEHOLDER, active_block)
        .replace(FACTOR_PLACEHOLDER, factor_block)
    )


def load_user_template() -> str:
    """Load the screening user-prompt template."""
    return read_text(PROJECT_ROOT / "prompts" / "screening" / "user_template.md")


def build_user_prompt(job: dict, template: str) -> str:
    """Build the user prompt from template — only per-job data, no per-user config."""
    return template.replace(
        "{{job_id}}", job.get("job_id", "")
    ).replace(
        "{{company}}", job.get("company", "")
    ).replace(
        "{{title}}", job.get("title", "")
    ).replace(
        "{{description_clean}}", job.get("description_clean") or job.get("description_raw", "")
    )


def screen_job_with_openai(
    job: dict,
    client: "OpenAI",
    model: str,
    system_prompt: str,
    user_template: str,
    response_schema: dict,
) -> dict:
    """Screen a single job using OpenAI."""
    user_prompt = build_user_prompt(job, user_template)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": response_schema
        },
        temperature=0.1  # Low temperature for consistent decisions
    )

    decision = json.loads(response.choices[0].message.content)

    # Enforce volume-first policy: if no rules matched, must apply
    if not decision.get("matched_reject_rules"):
        decision["decision"] = "apply"

    return decision


def _location_matches_allowed(job_location: str, allowed_locations: list[str]) -> bool:
    """Return True if the job's location string matches any allowed entry.

    Uses case-insensitive matching with two strategies per allowed entry:
    - single-word entries (e.g. "Sacramento") require a whole-word hit;
    - multi-word entries (e.g. "San Francisco Bay Area") match on any
      adjacent two-word subsequence (so "San Francisco, CA" matches via
      "san francisco" and "Greater Bay Area" matches via "bay area").

    The literal entry "Remote" is skipped here — remoteness is handled
    separately via ``source_attributes.remote_derived``.
    """
    if not job_location:
        return False
    loc = job_location.lower()
    for entry in allowed_locations:
        entry_l = (entry or "").lower().strip()
        if not entry_l or entry_l == "remote":
            continue
        words = re.findall(r"[a-z]+", entry_l)
        if len(words) == 1:
            if re.search(rf"\b{re.escape(words[0])}\b", loc):
                return True
            continue
        if entry_l in loc:
            return True
        for i in range(len(words) - 1):
            if f"{words[i]} {words[i + 1]}" in loc:
                return True
    return False


def screen_location_prefilter(
    job: dict,
    search_filters: dict,
    reject_rules: dict,
) -> dict | None:
    """Deterministic location check that runs before the LLM/local screener.

    Returns a fully-formed ``ScreeningDecision`` rejecting the job when its
    location is outside the configured allowed list and the job is not
    remote. Returns ``None`` to defer to the downstream screener when the
    location is allowed, missing, or the rule is disabled.
    """
    if not reject_rules.get("reject_if_location_mismatch", False):
        return None

    allowed_locations = search_filters.get("locations", []) or []
    allowed_lower = {(e or "").lower().strip() for e in allowed_locations}
    remote_allowed = bool(search_filters.get("remote_allowed", False)) or ("remote" in allowed_lower)

    job_location = (job.get("location") or "").strip()
    source_attrs = job.get("source_attributes") or {}
    is_remote = bool(source_attrs.get("remote_derived"))
    if not is_remote and job_location and "remote" in job_location.lower():
        is_remote = True

    if is_remote and remote_allowed:
        return None
    if not job_location:
        return None
    if _location_matches_allowed(job_location, allowed_locations):
        return None

    decision = {
        "job_id": job.get("job_id", ""),
        "decision": "reject",
        "matched_reject_rules": ["reject_if_location_mismatch"],
        "reason_summary": "Job location is outside the configured allowed list and the posting is not remote.",
        "evidence": [f"Job location: {job_location}"],
        "generated_at": now_iso(),
    }
    # Prefilter rejects skip the LLM, so factor categorizations are unknown.
    # The schema requires these fields on every decision; populate sentinels.
    decision.update(_unknown_factor_fields())
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen normalized jobs")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "normalized_jobs",
        help="Directory containing normalized job files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "screened_jobs",
        help="Directory for screening decisions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show decisions without saving"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of jobs to screen"
    )
    args = parser.parse_args()

    _load_env_file()

    # Load configuration
    reject_rules = read_json(PROJECT_ROOT / "config" / "search" / "reject_rules.json")
    search_filters = read_json(PROJECT_ROOT / "config" / "search" / "search_filters.json")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "ERROR: OPENAI_API_KEY is not set. Screening requires OpenAI; refusing to run.",
            file=sys.stderr,
        )
        return 2
    client = OpenAI(api_key=api_key)

    enabled_factors = reject_rules.get("enabled_factors", [])
    system_prompt = build_system_prompt(enabled_factors)
    response_schema = build_response_schema()
    user_template = load_user_template()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Find jobs to screen
    normalized_files = list_json_files(args.input_dir)

    # Filter out already-screened jobs
    screened_ids = {f.stem for f in list_json_files(args.output_dir)}
    to_screen = [f for f in normalized_files if f.stem not in screened_ids]

    if args.limit:
        to_screen = to_screen[:args.limit]

    print(f"Screening {len(to_screen)} jobs via OpenAI model={model}")
    print()

    apply_count = 0
    reject_count = 0
    error_count = 0

    for job_file in to_screen:
        # Screening logic
        try:
            job = read_json(job_file)
            print(f"Screening: {job.get('company', '?')} - {job.get('title', '?')}")

            # Prefilter by location
            decision = screen_location_prefilter(job, search_filters, reject_rules)
            if decision is None:
                decision = screen_job_with_openai(
                    job, client, model, system_prompt, user_template, response_schema,
                )

            # Validate decision
            is_valid, errors = validate_screening_decision(decision)
            if not is_valid:
                print(f"  Invalid decision: {errors}")
                error_count += 1
                continue

            if decision["decision"] == "apply":
                apply_count += 1
                print(f"  -> APPLY")
            else:
                reject_count += 1
                print(f"  -> REJECT ({decision.get('matched_reject_rules', [])})")
                if decision.get("evidence"):
                    for ev in decision["evidence"][:2]:
                        print(f"     Evidence: {ev}")

            if not args.dry_run:
                output_file = args.output_dir / f"{job['job_id']}.json"
                write_json(output_file, decision)

        except Exception as e:
            print(f"  Error: {e}")
            error_count += 1

    print()
    print(f"Results: {apply_count} apply, {reject_count} reject, {error_count} errors")
    if (apply_count + reject_count) > 0:
        print(f"Apply rate: {apply_count / (apply_count + reject_count) * 100:.1f}%")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
