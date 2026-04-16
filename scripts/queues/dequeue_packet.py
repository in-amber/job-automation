#!/usr/bin/env python3
"""
Dequeue the next packet from ready_to_apply for processing.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.timestamps import now_iso


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"


def dequeue_next() -> dict | None:
    """
    Get the next packet from ready_to_apply and move it to in_progress.

    Returns the packet or None if queue is empty.
    """
    ready_dir = QUEUE_DIR / "ready_to_apply"
    in_progress_dir = QUEUE_DIR / "in_progress"
    in_progress_dir.mkdir(parents=True, exist_ok=True)

    ready_files = list_json_files(ready_dir)

    if not ready_files:
        return None

    # Get oldest packet (first by name, which includes timestamp)
    packet_file = ready_files[0]
    packet = read_json(packet_file)

    # Update status
    packet['status'] = 'in_progress'
    packet['updated_at'] = now_iso()

    # Move to in_progress
    target_path = in_progress_dir / packet_file.name
    write_json(target_path, packet)
    packet_file.unlink()

    return packet


def main() -> int:
    parser = argparse.ArgumentParser(description="Dequeue next packet for processing")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output packet as JSON"
    )
    args = parser.parse_args()

    packet = dequeue_next()

    if packet is None:
        print("No packets in ready_to_apply queue")
        return 1

    if args.json:
        import json
        print(json.dumps(packet, indent=2))
    else:
        print(f"Dequeued: {packet['packet_id']}")
        print(f"  Company: {packet['company']}")
        print(f"  Title: {packet['title']}")
        print(f"  ATS: {packet['ats_type']}")
        print(f"  Submit policy: {packet['submit_policy']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
