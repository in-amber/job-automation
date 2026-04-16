#!/usr/bin/env python3
"""
Normalize raw job postings to the standard NormalizedJob schema.

This produces factual, ingestion-stage objects with no inferred hints.
All fields come from source data, not model inference.
"""
import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.hashing import hash_job_id
from utils.timestamps import now_iso
from utils.json_validate import validate_normalized_job


def clean_description(raw_html: str) -> str | None:
    """Remove HTML tags and clean up whitespace."""
    if not raw_html:
        return None
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip() or None


def normalize_job(raw_job: dict) -> dict:
    """
    Convert a raw job posting to normalized format.

    Only includes factual data from source. No inference or hints.
    """
    source = raw_job.get('_source', raw_job.get('source', 'other'))
    source_id = raw_job.get('source_posting_id', raw_job.get('id', ''))

    description_raw = raw_job.get('description', raw_job.get('description_raw', ''))

    # Extract source attributes (non-inferred metadata from source)
    source_attributes = {}
    for key in ['posted_date', 'applicant_count', 'company_size', 'industry']:
        if key in raw_job:
            source_attributes[key] = raw_job[key]
    if raw_job.get('metadata'):
        source_attributes.update(raw_job['metadata'])

    normalized = {
        'job_id': hash_job_id(source, str(source_id)),
        'source': source,
        'source_posting_id': str(source_id) if source_id else None,
        'fetched_at': raw_job.get('_fetched_at', now_iso()),
        'company': raw_job.get('company', ''),
        'title': raw_job.get('title', ''),
        'location': raw_job.get('location') or None,
        'employment_type': raw_job.get('employment_type') or None,
        'apply_url': raw_job.get('apply_url', ''),
        'source_url': raw_job.get('source_url', raw_job.get('apply_url', '')),
        'description_raw': description_raw,
        'description_clean': clean_description(description_raw),
        'salary_text': raw_job.get('salary', raw_job.get('salary_text')) or None,
        'source_attributes': source_attributes
    }

    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize raw job postings")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "raw_jobs",
        help="Directory containing raw job files"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "normalized_jobs",
        help="Directory for normalized job files"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        default=True,
        help="Validate output against schema"
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    raw_files = list_json_files(args.input_dir)
    print(f"Found {len(raw_files)} raw job files")

    normalized_count = 0
    error_count = 0

    for raw_file in raw_files:
        try:
            raw_job = read_json(raw_file)
            normalized = normalize_job(raw_job)

            if args.validate:
                is_valid, errors = validate_normalized_job(normalized)
                if not is_valid:
                    print(f"Validation errors in {raw_file.name}:")
                    for err in errors:
                        print(f"  - {err}")
                    error_count += 1
                    continue

            output_file = args.output_dir / f"{normalized['job_id']}.json"
            write_json(output_file, normalized)
            normalized_count += 1

        except Exception as e:
            print(f"Error processing {raw_file.name}: {e}")
            error_count += 1

    print(f"\nNormalized: {normalized_count}, Errors: {error_count}")
    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
