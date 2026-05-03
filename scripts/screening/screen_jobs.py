#!/usr/bin/env python3
"""
Screen normalized jobs using OpenAI with hard-reject logic.

CRITICAL: This implements the volume-first screening policy.
Default is APPLY unless a hard reject rule clearly triggers.

AI-output schema: ScreeningDecision (minimal, strict)
- Rejections require evidence from the posting
"""
import argparse
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

APPROVED_ROLE_DOMAINS_PATH = PROJECT_ROOT / "config" / "search" / "approved_role_domains.md"
APPROVED_ROLE_DOMAINS_PLACEHOLDER = "{{approved_role_domains}}"


def _available_factors() -> set[str]:
    return {p.stem for p in FACTORS_DIR.glob("*.md")}


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
    return fragment


def build_system_prompt(enabled_factors: list[str]) -> str:
    """Compose the system prompt from the always-on core plus the enabled factor fragments.

    Each factor's instructions are baked in only when that factor is enabled, so the
    model never sees guidance for criteria the user has chosen not to screen by.
    Per-factor config data (e.g., approved-role-domain categories) is also baked in
    here at build time rather than re-fed in the user prompt on every call.
    """
    available = _available_factors()
    unknown = [f for f in enabled_factors if f not in available]
    if unknown:
        raise ValueError(
            f"Unknown screening factor(s): {unknown}. "
            f"Add a fragment at {FACTORS_DIR}/<name>.md or remove from enabled_factors. "
            f"Available: {sorted(available)}"
        )

    core = read_text(SYSTEM_PROMPT_DIR / "core.md")
    fragments = [_load_factor_fragment(name) for name in enabled_factors]
    factor_block = "\n\n".join(fragments)
    return core.replace(FACTOR_PLACEHOLDER, factor_block)


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
) -> dict:
    """Screen a single job using OpenAI."""
    user_prompt = build_user_prompt(job, user_template)

    # Load the response schema
    schema = read_json(PROJECT_ROOT / "prompts" / "screening" / "schema.json")

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={
            "type": "json_schema",
            "json_schema": schema
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

    return {
        "job_id": job.get("job_id", ""),
        "decision": "reject",
        "matched_reject_rules": ["reject_if_location_mismatch"],
        "reason_summary": "Job location is outside the configured allowed list and the posting is not remote.",
        "evidence": [f"Job location: {job_location}"],
        "generated_at": now_iso(),
    }


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
                    job, client, model, system_prompt, user_template,
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
