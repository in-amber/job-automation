#!/usr/bin/env python3
"""Approve a draft cover letter and move the packet to ready_to_apply."""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json
from utils.timestamps import now_iso
from queues.transition_packet import get_packet_queue, transition_packet


def approve_cover_letter(packet_id: str) -> bool:
    packet_path, current_queue = get_packet_queue(packet_id)
    if packet_path is None:
        print(f"ERROR: packet not found: {packet_id}", file=sys.stderr)
        return False

    if current_queue != "waiting_for_cover_letter_approval":
        print(
            f"ERROR: packet {packet_id} is in '{current_queue}', "
            f"not 'waiting_for_cover_letter_approval'.",
            file=sys.stderr,
        )
        return False

    packet = read_json(packet_path)

    cover_letter_path = packet.get("cover_letter_path")
    if not cover_letter_path:
        print(f"ERROR: packet {packet_id} has no cover_letter_path.", file=sys.stderr)
        return False

    if not (PROJECT_ROOT / cover_letter_path).exists():
        print(f"ERROR: cover letter file missing at {cover_letter_path}", file=sys.stderr)
        return False

    packet["updated_at"] = now_iso()
    write_json(packet_path, packet)

    return transition_packet(packet_id, "ready_to_apply")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Approve a draft cover letter and move the packet to ready_to_apply."
    )
    parser.add_argument("packet_id", help="Packet ID to approve")
    args = parser.parse_args()

    return 0 if approve_cover_letter(args.packet_id) else 1


if __name__ == "__main__":
    sys.exit(main())
