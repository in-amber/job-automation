#!/usr/bin/env python3
"""
Enqueue application packets to ready_to_apply or appropriate waiting state.

Queue placement is the authoritative runtime state.
Packets do not store a status field - their location IS their status.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.timestamps import now_iso


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"


def get_target_queue(packet: dict) -> str:
    """
    Determine which queue a packet should go to based on cover_letter_status.

    Queue placement is the source of truth for runtime state.
    """
    cover_letter_status = packet.get('cover_letter_status', 'not_needed')

    # If cover letter is needed but not ready, wait for it
    if cover_letter_status in ('predicted_needed_draft_pending', 'required_discovered_mid_apply'):
        return 'waiting_for_cover_letter_approval'

    if cover_letter_status == 'draft_ready_waiting_approval':
        return 'waiting_for_cover_letter_approval'

    # Otherwise, ready to apply
    return 'ready_to_apply'


def enqueue_packet(packet_path: Path, target_queue: str | None = None) -> bool:
    """Move a packet to the appropriate queue."""
    packet = read_json(packet_path)

    if target_queue is None:
        target_queue = get_target_queue(packet)

    target_dir = QUEUE_DIR / target_queue
    target_dir.mkdir(parents=True, exist_ok=True)

    # Update packet timestamp (but not status - queue location IS status)
    packet['updated_at'] = now_iso()

    # Write to new location
    target_path = target_dir / f"{packet['packet_id']}.json"
    write_json(target_path, packet)

    # Remove from old location if different
    if packet_path.parent != target_dir and packet_path.exists():
        packet_path.unlink()

    print(f"Enqueued {packet['packet_id']} -> {target_queue}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Enqueue application packets")
    parser.add_argument(
        "packet_ids",
        nargs="*",
        help="Specific packet IDs to enqueue (or 'all' for all pending)"
    )
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "application_packets",
        help="Directory containing packets to enqueue"
    )
    parser.add_argument(
        "--force-queue",
        choices=["ready_to_apply", "waiting_for_cover_letter_approval"],
        help="Force packets to a specific queue"
    )
    args = parser.parse_args()

    packet_files = list_json_files(args.source_dir)

    if not args.packet_ids or args.packet_ids == ['all']:
        # Enqueue all packets in source dir
        to_enqueue = packet_files
    else:
        # Filter to specific packet IDs
        packet_ids = set(args.packet_ids)
        to_enqueue = [f for f in packet_files if f.stem in packet_ids]

    print(f"Enqueuing {len(to_enqueue)} packets")

    success = 0
    failed = 0

    for packet_file in to_enqueue:
        try:
            if enqueue_packet(packet_file, args.force_queue):
                success += 1
            else:
                failed += 1
        except Exception as e:
            print(f"Error enqueuing {packet_file.name}: {e}")
            failed += 1

    print(f"\nSuccess: {success}, Failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
