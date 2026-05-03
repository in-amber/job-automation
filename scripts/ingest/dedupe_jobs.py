#!/usr/bin/env python3
"""
Deduplicate normalized jobs against already-processed jobs.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.hashing import hash_content


def load_existing_job_ids(directories: list[Path]) -> set[str]:
    """Load all job IDs from multiple directories."""
    existing_ids = set()

    for directory in directories:
        if not directory.exists():
            continue
        for json_file in list_json_files(directory):
            try:
                job = read_json(json_file)
                if 'job_id' in job:
                    existing_ids.add(job['job_id'])
            except Exception:
                pass

    return existing_ids


def load_content_hashes(directories: list[Path]) -> set[str]:
    """Load content hashes for fuzzy deduplication."""
    hashes = set()

    for directory in directories:
        if not directory.exists():
            continue
        for json_file in list_json_files(directory):
            try:
                job = read_json(json_file)
                # Hash company + title + first 500 chars of description
                content = f"{job.get('company', '')}|{job.get('title', '')}|{job.get('description_clean', '')[:500]}"
                hashes.add(hash_content(content.lower()))
            except Exception:
                pass

    return hashes


def main() -> int:
    parser = argparse.ArgumentParser(description="Deduplicate normalized jobs")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "normalized_jobs",
        help="Directory containing normalized job files"
    )
    parser.add_argument(
        "--fuzzy",
        action="store_true",
        help="Also do fuzzy content-based deduplication"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show duplicates without removing them"
    )
    args = parser.parse_args()

    # Directories to check for existing jobs
    check_dirs = [
        PROJECT_ROOT / "data" / "screened_jobs",
        PROJECT_ROOT / "data" / "queues" / "completed",
        PROJECT_ROOT / "data" / "queues" / "rejected",
        PROJECT_ROOT / "data" / "queues" / "failed",
    ]

    existing_ids = load_existing_job_ids(check_dirs)
    print(f"Found {len(existing_ids)} existing job IDs")

    content_hashes = set()
    if args.fuzzy:
        content_hashes = load_content_hashes(check_dirs)
        print(f"Found {len(content_hashes)} existing content hashes")

    # Process normalized jobs
    normalized_files = list_json_files(args.input_dir)
    print(f"Checking {len(normalized_files)} normalized jobs")

    duplicates = []
    seen_ids = set()
    seen_hashes = set()

    for json_file in normalized_files:
        try:
            job = read_json(json_file)
            job_id = job.get('job_id', '')

            is_dupe = False
            reason = ""

            # Check against existing jobs
            if job_id in existing_ids:
                is_dupe = True
                reason = "already processed"

            # Check against jobs in current batch
            elif job_id in seen_ids:
                is_dupe = True
                reason = "duplicate in batch"

            # Fuzzy check
            elif args.fuzzy:
                content = f"{job.get('company', '')}|{job.get('title', '')}|{job.get('description_clean', '')[:500]}"
                content_hash = hash_content(content.lower())

                if content_hash in content_hashes or content_hash in seen_hashes:
                    is_dupe = True
                    reason = "similar content exists"
                else:
                    seen_hashes.add(content_hash)

            if is_dupe:
                duplicates.append((json_file, reason))
            else:
                seen_ids.add(job_id)

        except Exception as e:
            print(f"Error checking {json_file.name}: {e}")

    # Report and optionally remove
    if duplicates:
        print(f"\nFound {len(duplicates)} duplicates:")
        for filepath, reason in duplicates:
            print(f"  {filepath.name}: {reason}")
            if not args.dry_run:
                filepath.unlink()

        if not args.dry_run:
            print(f"\nRemoved {len(duplicates)} duplicate files")
    else:
        print("\nNo duplicates found")

    remaining = len(normalized_files) - len(duplicates)
    print(f"Remaining jobs to process: {remaining}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
