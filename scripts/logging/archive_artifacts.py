#!/usr/bin/env python3
"""
Archive artifacts for completed applications.
"""
import argparse
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, list_json_files
from utils.timestamps import timestamp_for_filename


ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
EXPORTS_DIR = ARTIFACTS_DIR / "exports"
QUEUE_DIR = PROJECT_ROOT / "data" / "queues"


def archive_packet_artifacts(packet_id: str, destination: Path | None = None) -> Path:
    """
    Archive all artifacts for a packet into a single directory.

    Returns the archive directory path.
    """
    if destination is None:
        timestamp = timestamp_for_filename()
        destination = EXPORTS_DIR / f"{packet_id}_{timestamp}"

    destination.mkdir(parents=True, exist_ok=True)

    # Copy screenshots
    screenshots_dir = ARTIFACTS_DIR / "screenshots" / packet_id
    if screenshots_dir.exists():
        dest_screenshots = destination / "screenshots"
        shutil.copytree(screenshots_dir, dest_screenshots, dirs_exist_ok=True)

    # Copy PDFs
    pdfs_dir = ARTIFACTS_DIR / "pdfs" / packet_id
    if pdfs_dir.exists():
        dest_pdfs = destination / "pdfs"
        shutil.copytree(pdfs_dir, dest_pdfs, dirs_exist_ok=True)

    # Copy cover letter
    for cl_file in ARTIFACTS_DIR.glob(f"cover_letters/{packet_id}*"):
        shutil.copy2(cl_file, destination / cl_file.name)

    # Copy packet file
    for queue_dir in QUEUE_DIR.iterdir():
        if queue_dir.is_dir():
            for packet_file in queue_dir.glob(f"{packet_id}.json"):
                shutil.copy2(packet_file, destination / "packet.json")
                break

    # Copy run logs
    run_logs_dir = PROJECT_ROOT / "data" / "run_logs"
    for log_file in list_json_files(run_logs_dir):
        log = read_json(log_file)
        if log.get('packet_id') == packet_id:
            shutil.copy2(log_file, destination / f"run_log_{log_file.name}")

    return destination


def archive_all_completed() -> int:
    """Archive all completed applications."""
    completed_dir = QUEUE_DIR / "completed"
    completed_files = list_json_files(completed_dir)

    archived_count = 0
    for packet_file in completed_files:
        packet = read_json(packet_file)
        packet_id = packet.get('packet_id')

        # Check if already archived
        existing = list(EXPORTS_DIR.glob(f"{packet_id}_*"))
        if existing:
            continue

        try:
            archive_path = archive_packet_artifacts(packet_id)
            print(f"Archived: {packet_id} -> {archive_path.name}")
            archived_count += 1
        except Exception as e:
            print(f"Error archiving {packet_id}: {e}")

    return archived_count


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive application artifacts")
    parser.add_argument(
        "--packet-id",
        help="Archive a specific packet"
    )
    parser.add_argument(
        "--all-completed",
        action="store_true",
        help="Archive all completed applications"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Custom output directory"
    )
    args = parser.parse_args()

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.packet_id:
        archive_path = archive_packet_artifacts(args.packet_id, args.output_dir)
        print(f"Archived to: {archive_path}")

    elif args.all_completed:
        count = archive_all_completed()
        print(f"\nArchived {count} applications")

    else:
        print("Specify --packet-id or --all-completed")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
