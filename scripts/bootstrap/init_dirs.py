#!/usr/bin/env python3
"""Initialize all required directories for the job automation system."""
import sys
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Required directories
DIRECTORIES = [
    # Data directories
    "data/raw_jobs",
    "data/normalized_jobs",
    "data/screened_jobs",
    "data/queues/ready_to_apply",
    "data/queues/waiting_for_cover_letter_approval",
    "data/queues/waiting_for_signup",
    "data/queues/waiting_for_human_review",
    "data/queues/completed",
    "data/queues/rejected",
    "data/queues/failed",
    "data/queues/in_progress",
    "data/run_logs",
    "data/run_logs/interventions",
    "data/checkpoints",
    # Artifact directories
    "artifacts/cover_letters",
]


def init_directories() -> None:
    """Create all required directories."""
    print("Initializing directories...")

    for dir_path in DIRECTORIES:
        full_path = PROJECT_ROOT / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

        # Create .gitkeep to preserve empty directories
        gitkeep = full_path / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()

        print(f"  Created: {dir_path}")

    print(f"\nInitialized {len(DIRECTORIES)} directories.")


def main() -> int:
    """Main entry point."""
    try:
        init_directories()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
