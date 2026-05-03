#!/usr/bin/env python3
"""
Build application packets from screened jobs that passed screening.

This is a code-generated storage object. All computed fields
(ats_type, trust_tier, policies) are determined by code, not AI.

Queue placement is the authoritative runtime state - packets do not
store their own status field.
"""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.hashing import generate_packet_id
from utils.timestamps import now_iso
from utils.json_validate import validate_application_packet


def classify_ats(job: dict) -> str:
    """Classify the ATS type for a normalized job.

    A linkedin.com apply_url does not imply Easy Apply — LinkedIn hosts
    both Easy Apply listings and listings whose Apply button redirects
    off-platform. The authoritative signal is LinkedIn's own
    ``source_attributes.directapply`` flag: True means Easy Apply,
    False means the listing routes to an external site.
    """
    apply_url = job.get('apply_url', '') or ''
    domain = urlparse(apply_url).netloc.lower()
    source = (job.get('source') or '').lower()

    if source == 'linkedin' or 'linkedin.com' in domain:
        directapply = job.get('source_attributes', {}).get('directapply')
        if directapply is True:
            return 'linkedin_easy_apply'
        return 'other'
    if 'greenhouse.io' in domain or 'boards.greenhouse.io' in domain:
        return 'greenhouse'
    if 'myworkdayjobs.com' in domain or 'workday.com' in domain:
        return 'workday'

    return 'other'


def get_trust_tier(domain: str, trusted_domains: dict) -> str:
    """Determine trust tier for a domain."""
    domain = domain.lower()

    for trusted in trusted_domains.get('tier_a', []):
        if trusted.lower() in domain:
            return 'tier_a'

    for trusted in trusted_domains.get('tier_b', []):
        if trusted.lower() in domain:
            return 'tier_b'

    return 'tier_c'


def build_submit_policy(ats_type: str, trust_tier: str, runtime_config: dict) -> dict:
    """Build structured submit policy based on ATS and config."""
    auto_submit_allowed = False

    if ats_type == 'linkedin_easy_apply' and runtime_config.get('auto_submit_linkedin_easy_apply', False):
        auto_submit_allowed = True
    elif ats_type == 'greenhouse' and runtime_config.get('auto_submit_greenhouse', False):
        auto_submit_allowed = True
    elif ats_type == 'workday' and runtime_config.get('auto_submit_workday', False):
        auto_submit_allowed = True
    elif ats_type == 'other' and runtime_config.get('auto_submit_other', False):
        auto_submit_allowed = True

    human_approval_required = runtime_config.get('human_approval_before_submit', True)

    # If auto-submit is allowed for this ATS, human approval may not be required
    if auto_submit_allowed and not human_approval_required:
        human_approval_required = False

    return {
        "human_approval_required": human_approval_required,
        "auto_submit_allowed": auto_submit_allowed
    }


def build_escalation_policy(runtime_config: dict) -> dict:
    """Build structured escalation policy from config."""
    return {
        "manual_signup_only": runtime_config.get('manual_signup_only', True),
        "max_field_retries": runtime_config.get('max_field_retries', 2),
        "max_issue_minutes": runtime_config.get('max_issue_minutes', 3)
    }


def build_packet(
    job: dict,
    decision: dict,
    runtime_config: dict,
    trusted_domains: dict
) -> dict:
    """Build an application packet from a job and screening decision.

    Cover-letter need is not predicted at packet-build time. Packets start with
    `cover_letter_path=None`; if the apply step encounters a cover-letter
    requirement, it moves the packet to `waiting_for_cover_letter_approval`
    and the drafter generates one on the next cron run.
    """
    apply_url = job.get('apply_url', '')
    domain = urlparse(apply_url).netloc

    ats_type = classify_ats(job)
    trust_tier = get_trust_tier(domain, trusted_domains)
    submit_policy = build_submit_policy(ats_type, trust_tier, runtime_config)
    escalation_policy = build_escalation_policy(runtime_config)

    packet_id = generate_packet_id()

    packet = {
        'packet_id': packet_id,
        'job_id': job['job_id'],
        'company': job.get('company', ''),
        'title': job.get('title', ''),
        'location': job.get('location'),
        'source': job.get('source', ''),
        'source_url': job.get('source_url', ''),
        'apply_url': apply_url,
        'ats_type': ats_type,
        'trust_tier': trust_tier,
        'resume_path': 'config/applicant/resume.pdf',
        'cover_letter_path': None,
        'applicant_answers_path': 'config/applicant/applicant_master_answers.md',
        'job_snapshot_path': f'data/normalized_jobs/{job["job_id"]}.json',
        'screening_decision_path': f'data/screened_jobs/{job["job_id"]}.json',
        'submit_policy': submit_policy,
        'escalation_policy': escalation_policy,
        'created_at': now_iso(),
        'updated_at': None
    }

    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Build application packets")
    parser.add_argument(
        "--screened-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "screened_jobs",
        help="Directory containing screening decisions"
    )
    parser.add_argument(
        "--jobs-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "normalized_jobs",
        help="Directory containing normalized jobs"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "queues" / "ready_to_apply",
        help="Queue directory packets are written into (default: ready_to_apply)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show packets without saving"
    )
    args = parser.parse_args()

    # Load configuration
    runtime_config = read_json(PROJECT_ROOT / "config" / "runtime.json")
    trusted_domains = read_json(PROJECT_ROOT / "config" / "trusted_domains.json")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # Find decisions that should apply
    decision_files = list_json_files(args.screened_dir)
    apply_decisions = []

    for df in decision_files:
        decision = read_json(df)
        if decision.get('decision') == 'apply':
            apply_decisions.append(decision)

    print(f"Found {len(apply_decisions)} jobs to apply to")

    # Skip jobs that already have a packet anywhere in the queue system —
    # ready, in-progress, completed, rejected, etc. all count as "built".
    queues_root = PROJECT_ROOT / "data" / "queues"
    existing_job_ids = set()
    if queues_root.exists():
        for queue_dir in queues_root.iterdir():
            if queue_dir.is_dir():
                for pf in list_json_files(queue_dir):
                    packet = read_json(pf)
                    if packet.get('job_id'):
                        existing_job_ids.add(packet['job_id'])

    apply_decisions = [d for d in apply_decisions if d['job_id'] not in existing_job_ids]
    print(f"After filtering existing: {len(apply_decisions)} new packets to create")

    created_count = 0
    error_count = 0

    for decision in apply_decisions:
        try:
            job_id = decision['job_id']
            job_file = args.jobs_dir / f"{job_id}.json"

            if not job_file.exists():
                print(f"Job file not found: {job_file}")
                error_count += 1
                continue

            job = read_json(job_file)
            packet = build_packet(job, decision, runtime_config, trusted_domains)

            # Validate
            is_valid, errors = validate_application_packet(packet)
            if not is_valid:
                print(f"Invalid packet for {job_id}: {errors}")
                error_count += 1
                continue

            print(f"Created packet: {packet['company']} - {packet['title']} ({packet['ats_type']})")

            if not args.dry_run:
                output_file = args.output_dir / f"{packet['packet_id']}.json"
                write_json(output_file, packet)

            created_count += 1

        except Exception as e:
            print(f"Error creating packet: {e}")
            error_count += 1

    print()
    print(f"Created: {created_count}, Errors: {error_count}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
