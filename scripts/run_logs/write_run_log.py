#!/usr/bin/env python3
"""
Write run logs after application attempts.

Uses structured issue_type enum instead of freeform escalation text.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import write_json
from utils.hashing import generate_run_id
from utils.timestamps import now_iso
from utils.json_validate import validate_run_log


RUN_LOGS_DIR = PROJECT_ROOT / "data" / "run_logs"

# Valid result values
VALID_RESULTS = [
    "submitted",
    "waiting_for_signup",
    "waiting_for_cover_letter",
    "waiting_for_human_review",
    "failed"
]

# Valid issue types
VALID_ISSUE_TYPES = [
    "signup_required",
    "captcha",
    "otp_required",
    "missing_answer",
    "cover_letter_required",
    "field_mapping_failure",
    "unknown",
    None
]


def create_run_log(
    packet_id: str,
    result: str,
    worker: str = "cowork",
    started_at: str | None = None,
    confirmation_number: str | None = None,
    issue_type: str | None = None,
    notes: str | None = None,
) -> dict:
    """Create a new run log entry with typed issue classification."""
    run_log = {
        "run_id": generate_run_id(),
        "packet_id": packet_id,
        "worker": worker,
        "started_at": started_at or now_iso(),
        "finished_at": now_iso(),
        "result": result,
        "confirmation_number": confirmation_number,
        "issue_type": issue_type,
        "notes": notes,
    }

    return run_log


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a run log")
    parser.add_argument("packet_id", help="Packet ID for this run")
    parser.add_argument(
        "--result",
        required=True,
        choices=VALID_RESULTS,
        help="Result of the application attempt"
    )
    parser.add_argument(
        "--issue-type",
        choices=[t for t in VALID_ISSUE_TYPES if t is not None],
        help="Type of issue if escalated"
    )
    parser.add_argument("--confirmation", help="Confirmation number if received")
    parser.add_argument("--notes", help="Additional notes")
    args = parser.parse_args()

    run_log = create_run_log(
        packet_id=args.packet_id,
        result=args.result,
        confirmation_number=args.confirmation,
        issue_type=args.issue_type,
        notes=args.notes,
    )

    # Validate
    is_valid, errors = validate_run_log(run_log)
    if not is_valid:
        print(f"Invalid run log: {errors}")
        return 1

    # Save
    RUN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RUN_LOGS_DIR / f"{run_log['run_id']}.json"
    write_json(log_path, run_log)

    print(f"Created run log: {run_log['run_id']}")
    print(f"  Packet: {args.packet_id}")
    print(f"  Result: {args.result}")
    if args.issue_type:
        print(f"  Issue type: {args.issue_type}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
