#!/usr/bin/env python3
"""Validate environment configuration for the job automation system."""
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Required environment variables
REQUIRED_ENV_VARS = [
    "OPENAI_API_KEY",
    "RAPIDAPI_KEY",
    "RAPIDAPI_HOST",
]

# Optional but recommended
RECOMMENDED_ENV_VARS = [
    "GOOGLE_SHEET_ID",
    "GOOGLE_SHEETS_CREDENTIALS_PATH",
]

# Required files
REQUIRED_FILES = [
    "config/runtime.json",
    "config/trusted_domains.json",
    "config/search/reject_rules.json",
    "config/search/search_filters.json",
    "config/search/titles.txt",
]

# Required for actual applications (not scaffolding)
APPLICANT_FILES = [
    "config/applicant/applicant_master_answers.md",
    "config/applicant/resume.pdf",
]


def load_env_file() -> None:
    """Load .env file if it exists."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    os.environ.setdefault(key.strip(), value.strip())


def check_env_vars() -> tuple[list[str], list[str]]:
    """Check for required and recommended environment variables."""
    missing_required = []
    missing_recommended = []

    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            missing_required.append(var)

    for var in RECOMMENDED_ENV_VARS:
        if not os.environ.get(var):
            missing_recommended.append(var)

    return missing_required, missing_recommended


def check_files() -> tuple[list[str], list[str]]:
    """Check for required files."""
    missing_required = []
    missing_applicant = []

    for file_path in REQUIRED_FILES:
        if not (PROJECT_ROOT / file_path).exists():
            missing_required.append(file_path)

    for file_path in APPLICANT_FILES:
        if not (PROJECT_ROOT / file_path).exists():
            missing_applicant.append(file_path)

    return missing_required, missing_applicant


def check_docker() -> bool:
    """Check if Docker is available."""
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> int:
    """Main entry point."""
    print("Validating environment...\n")

    # Load .env
    load_env_file()

    errors = []
    warnings = []

    # Check env vars
    missing_req_env, missing_rec_env = check_env_vars()
    if missing_req_env:
        errors.append(f"Missing required environment variables: {', '.join(missing_req_env)}")
    if missing_rec_env:
        warnings.append(f"Missing recommended environment variables: {', '.join(missing_rec_env)}")

    # Check files
    missing_req_files, missing_app_files = check_files()
    if missing_req_files:
        errors.append(f"Missing required files: {', '.join(missing_req_files)}")
    if missing_app_files:
        warnings.append(f"Missing applicant files (needed for actual applications): {', '.join(missing_app_files)}")

    # Check Docker
    if not check_docker():
        warnings.append("Docker not found or not running")

    # Report results
    if errors:
        print("ERRORS:")
        for error in errors:
            print(f"  - {error}")
        print()

    if warnings:
        print("WARNINGS:")
        for warning in warnings:
            print(f"  - {warning}")
        print()

    if not errors and not warnings:
        print("All checks passed!")
        return 0
    elif not errors:
        print("Environment is valid (with warnings).")
        return 0
    else:
        print("Environment validation failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
