#!/usr/bin/env python3
"""
Fetch raw job postings from configured sources.

This is a scaffold that needs to be connected to actual job sources.
Current implementation creates placeholder structure for manual job input.
"""
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import write_json, read_json, read_lines
from utils.timestamps import now_iso, timestamp_for_filename


def fetch_from_linkedin(search_titles: list[str], filters: dict) -> list[dict]:
    """
    Fetch jobs from LinkedIn.

    TODO: Implement actual LinkedIn job fetching.
    This could use:
    - LinkedIn API (requires partner access)
    - Browser automation with Cowork
    - RSS feeds
    - Manual CSV import
    """
    print("LinkedIn fetching not yet implemented.")
    print("To add jobs manually, create JSON files in data/raw_jobs/")
    return []


def fetch_from_greenhouse(search_titles: list[str], filters: dict) -> list[dict]:
    """
    Fetch jobs from Greenhouse job boards.

    TODO: Implement Greenhouse board scraping.
    """
    print("Greenhouse fetching not yet implemented.")
    return []


def fetch_from_workday(search_titles: list[str], filters: dict) -> list[dict]:
    """
    Fetch jobs from Workday career sites.

    TODO: Implement Workday fetching.
    """
    print("Workday fetching not yet implemented.")
    return []


def save_raw_jobs(jobs: list[dict], source: str) -> int:
    """Save raw jobs to the raw_jobs directory."""
    raw_dir = PROJECT_ROOT / "data" / "raw_jobs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    saved = 0

    for i, job in enumerate(jobs):
        filename = f"{timestamp}_{source}_{i:04d}.json"
        job["_fetched_at"] = now_iso()
        job["_source"] = source
        write_json(raw_dir / filename, job)
        saved += 1

    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch raw job postings")
    parser.add_argument(
        "--source",
        choices=["linkedin", "greenhouse", "workday", "all"],
        default="all",
        help="Job source to fetch from"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without saving"
    )
    args = parser.parse_args()

    # Load configuration
    titles = read_lines(PROJECT_ROOT / "config" / "search" / "titles.txt")
    filters = read_json(PROJECT_ROOT / "config" / "search" / "search_filters.json")

    print(f"Search titles: {titles}")
    print(f"Filters: {filters}")
    print()

    all_jobs = []

    if args.source in ("linkedin", "all"):
        jobs = fetch_from_linkedin(titles, filters)
        all_jobs.extend(jobs)

    if args.source in ("greenhouse", "all"):
        jobs = fetch_from_greenhouse(titles, filters)
        all_jobs.extend(jobs)

    if args.source in ("workday", "all"):
        jobs = fetch_from_workday(titles, filters)
        all_jobs.extend(jobs)

    if args.dry_run:
        print(f"Would save {len(all_jobs)} jobs")
        return 0

    if all_jobs:
        saved = save_raw_jobs(all_jobs, args.source)
        print(f"Saved {saved} raw jobs")
    else:
        print("No jobs fetched.")
        print("\nTo add jobs manually, create JSON files in data/raw_jobs/ with structure:")
        print("""
{
  "source_posting_id": "unique-id-from-source",
  "company": "Company Name",
  "title": "Job Title",
  "location": "Location",
  "apply_url": "https://...",
  "source_url": "https://...",
  "description": "Full job description...",
  "salary": "optional salary info"
}
""")

    return 0


if __name__ == "__main__":
    sys.exit(main())
