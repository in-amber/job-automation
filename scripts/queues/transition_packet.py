#!/usr/bin/env python3
"""
Transition a packet between queue states.

Queue placement is the authoritative runtime state.
Moving a packet to a queue IS the state change - no status field needed.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.timestamps import now_iso


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"

# Valid queue locations (these ARE the states)
VALID_QUEUES = [
    'ready_to_apply',
    'waiting_for_cover_letter_approval',
    'waiting_for_signup',
    'waiting_for_human_review',
    'in_progress',
    'completed',
    'rejected',
    'failed'
]

# Valid transitions (from queue -> [allowed destination queues])
VALID_TRANSITIONS = {
    'ready_to_apply': ['in_progress', 'rejected'],
    'waiting_for_cover_letter_approval': ['ready_to_apply', 'rejected'],
    'in_progress': ['completed', 'waiting_for_signup', 'waiting_for_human_review', 'waiting_for_cover_letter_approval', 'failed'],
    'waiting_for_signup': ['ready_to_apply', 'failed'],
    'waiting_for_human_review': ['completed', 'ready_to_apply', 'failed'],
}


def get_packet_queue(packet_id: str) -> tuple[Path | None, str | None]:
    """Find which queue a packet is currently in."""
    for queue_name in VALID_QUEUES:
        queue_dir = QUEUE_DIR / queue_name
        if queue_dir.exists():
            packet_path = queue_dir / f"{packet_id}.json"
            if packet_path.exists():
                return packet_path, queue_name

    return None, None


def find_packet(packet_id: str) -> Path | None:
    """Find a packet file by ID across all queues."""
    path, _ = get_packet_queue(packet_id)
    return path


def transition_packet(packet_id: str, new_queue: str, force: bool = False) -> bool:
    """Transition a packet to a new queue."""
    if new_queue not in VALID_QUEUES:
        print(f"Invalid queue: {new_queue}")
        print(f"Valid queues: {VALID_QUEUES}")
        return False

    packet_path, current_queue = get_packet_queue(packet_id)
    if packet_path is None:
        print(f"Packet not found: {packet_id}")
        return False

    # Check if transition is valid
    if not force and current_queue in VALID_TRANSITIONS:
        allowed = VALID_TRANSITIONS.get(current_queue, [])
        if new_queue not in allowed:
            print(f"Invalid transition: {current_queue} -> {new_queue}")
            print(f"Allowed transitions from {current_queue}: {allowed}")
            return False

    # Read packet and update timestamp in memory
    packet = read_json(packet_path)
    packet['updated_at'] = now_iso()

    # Move via rename (same-filesystem, atomic). Avoids the copy+unlink
    # pattern, which fails under sandboxed runners (e.g. Cowork) that have
    # write perms on the queue dirs but no delete perm on individual files.
    # rename() is a directory-entry change — no file delete involved.
    target_dir = QUEUE_DIR / new_queue
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{packet['packet_id']}.json"

    if packet_path != target_path:
        packet_path.rename(target_path)
    write_json(target_path, packet)

    print(f"Transitioned {packet_id}: {current_queue} -> {new_queue}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Transition packet between queues")
    parser.add_argument("packet_id", help="Packet ID to transition")
    parser.add_argument("new_queue", choices=VALID_QUEUES, help="Target queue")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow invalid transitions"
    )
    args = parser.parse_args()

    success = transition_packet(args.packet_id, args.new_queue, args.force)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
