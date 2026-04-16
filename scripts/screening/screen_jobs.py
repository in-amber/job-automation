#!/usr/bin/env python3
"""
Screen normalized jobs using OpenAI with hard-reject logic.

CRITICAL: This implements the volume-first screening policy.
Default is APPLY unless a hard reject rule clearly triggers.

AI-output schema: ScreeningDecision (minimal, strict)
- Rejections require evidence from the posting
- Uses cover_letter_signal enum instead of boolean guess
"""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files, read_text, read_lines
from utils.timestamps import now_iso
from utils.json_validate import validate_screening_decision

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: openai package not installed. Install with: pip install openai")


def load_screening_prompt() -> tuple[str, str]:
    """Load the screening system and user prompts."""
    prompts_dir = PROJECT_ROOT / "prompts" / "screening"
    system_prompt = read_text(prompts_dir / "system.md")
    user_template = read_text(prompts_dir / "user_template.md")
    return system_prompt, user_template


def build_user_prompt(
    job: dict,
    reject_rules: dict,
    titles: list[str],
    search_filters: dict,
    template: str
) -> str:
    """Build the user prompt from template."""
    return template.replace(
        "{{company}}", job.get("company", "")
    ).replace(
        "{{title}}", job.get("title", "")
    ).replace(
        "{{location}}", job.get("location") or "Not specified"
    ).replace(
        "{{source}}", job.get("source", "")
    ).replace(
        "{{description_clean}}", job.get("description_clean") or job.get("description_raw", "")
    ).replace(
        "{{reject_rules_json}}", json.dumps(reject_rules, indent=2)
    ).replace(
        "{{titles_list}}", "\n".join(f"- {t}" for t in titles)
    ).replace(
        "{{search_filters_json}}", json.dumps(search_filters, indent=2)
    ).replace(
        "{{job_id}}", job.get("job_id", "")
    )


def screen_job_with_openai(
    job: dict,
    reject_rules: dict,
    titles: list[str],
    search_filters: dict,
    client: "OpenAI",
    model: str
) -> dict:
    """Screen a single job using OpenAI."""
    system_prompt, user_template = load_screening_prompt()
    user_prompt = build_user_prompt(job, reject_rules, titles, search_filters, user_template)

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


def screen_job_locally(job: dict, reject_rules: dict) -> dict:
    """
    Simple local screening without API calls.
    Used for testing or when OpenAI is unavailable.

    Implements basic rule matching with evidence collection.
    """
    title = job.get("title", "").lower()
    description = job.get("description_clean") or job.get("description_raw", "")
    description_lower = description.lower()

    matched_rules = []
    evidence = []

    # Check senior title rule
    if reject_rules.get("reject_senior_titles", False):
        senior_keywords = reject_rules.get("senior_title_keywords", [])
        for keyword in senior_keywords:
            if keyword.lower() in title:
                matched_rules.append("reject_senior_titles")
                evidence.append(f"Title contains '{keyword}': {job.get('title', '')}")
                break

    # Check experience requirement
    max_years = reject_rules.get("max_required_years_experience", float("inf"))
    import re
    exp_match = re.search(r'(\d+)\+?\s*years?\s*(of\s+)?(experience\s+)?(required|minimum)', description_lower)
    if exp_match:
        years_found = int(exp_match.group(1))
        if years_found > max_years:
            matched_rules.append("max_required_years_experience")
            evidence.append(f"Requires {years_found}+ years experience (max allowed: {max_years})")

    # Check clearance
    if reject_rules.get("reject_if_requires_clearance", False):
        clearance_terms = ["security clearance", "ts/sci", "top secret", "secret clearance"]
        for term in clearance_terms:
            if term in description_lower:
                matched_rules.append("reject_if_requires_clearance")
                evidence.append(f"Requires clearance: '{term}' found in description")
                break

    # Determine cover letter signal from posting text
    cover_letter_signal = "unknown"
    cl_lower = description_lower
    if "cover letter required" in cl_lower or "must include cover letter" in cl_lower:
        cover_letter_signal = "explicitly_required"
    elif "cover letter" in cl_lower or "letter of interest" in cl_lower:
        cover_letter_signal = "optional_signal"
    elif any(phrase in cl_lower for phrase in ["resume only", "no cover letter"]):
        cover_letter_signal = "no_signal"

    decision = {
        "job_id": job.get("job_id", ""),
        "decision": "reject" if matched_rules else "apply",
        "matched_reject_rules": matched_rules,
        "reason_summary": f"Matched rules: {matched_rules}" if matched_rules else "No hard reject rules triggered",
        "evidence": evidence,
        "cover_letter_signal": cover_letter_signal,
        "generated_at": now_iso()
    }

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
        "--local",
        action="store_true",
        help="Use local rule matching instead of OpenAI"
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

    # Load configuration
    reject_rules = read_json(PROJECT_ROOT / "config" / "search" / "reject_rules.json")
    search_filters = read_json(PROJECT_ROOT / "config" / "search" / "search_filters.json")
    titles = read_lines(PROJECT_ROOT / "config" / "search" / "titles.txt")

    # Set up OpenAI client
    client = None
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not args.local:
        if not HAS_OPENAI:
            print("OpenAI not available, using local screening")
            args.local = True
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                print("OPENAI_API_KEY not set, using local screening")
                args.local = True
            else:
                client = OpenAI(api_key=api_key)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Find jobs to screen
    normalized_files = list_json_files(args.input_dir)

    # Filter out already-screened jobs
    screened_ids = {f.stem for f in list_json_files(args.output_dir)}
    to_screen = [f for f in normalized_files if f.stem not in screened_ids]

    if args.limit:
        to_screen = to_screen[:args.limit]

    print(f"Screening {len(to_screen)} jobs (mode: {'local' if args.local else 'OpenAI'})")
    print()

    apply_count = 0
    reject_count = 0
    error_count = 0

    for job_file in to_screen:
        try:
            job = read_json(job_file)
            print(f"Screening: {job.get('company', '?')} - {job.get('title', '?')}")

            if args.local:
                decision = screen_job_locally(job, reject_rules)
            else:
                decision = screen_job_with_openai(
                    job, reject_rules, titles, search_filters, client, model
                )

            # Validate decision
            is_valid, errors = validate_screening_decision(decision)
            if not is_valid:
                print(f"  Invalid decision: {errors}")
                error_count += 1
                continue

            if decision["decision"] == "apply":
                apply_count += 1
                print(f"  -> APPLY (cover letter: {decision.get('cover_letter_signal', 'unknown')})")
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
