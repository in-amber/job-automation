"""Pytest configuration and fixtures."""
import json
import sys
from pathlib import Path

import pytest

# Add scripts to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


@pytest.fixture
def project_root():
    """Return project root path."""
    return PROJECT_ROOT


@pytest.fixture
def fixtures_dir():
    """Return fixtures directory path."""
    return PROJECT_ROOT / "tests" / "fixtures"


@pytest.fixture
def sample_normalized_job():
    """Return a sample normalized job (no hint fields)."""
    return {
        "job_id": "abc123def456",
        "source": "linkedin",
        "source_posting_id": "12345",
        "fetched_at": "2024-01-15T10:00:00Z",
        "company": "Acme Corp",
        "title": "Software Engineer",
        "location": "San Francisco, CA",
        "employment_type": "full_time",
        "apply_url": "https://linkedin.com/jobs/apply/12345",
        "source_url": "https://linkedin.com/jobs/view/12345",
        "description_raw": "<p>We are looking for a software engineer.</p>",
        "description_clean": "We are looking for a software engineer.",
        "salary_text": "$100,000 - $150,000",
        "source_attributes": {}
    }


@pytest.fixture
def sample_reject_rules():
    """Return sample reject rules."""
    return {
        "max_required_years_experience": 1,
        "reject_senior_titles": True,
        "senior_title_keywords": ["senior", "staff", "principal", "lead", "manager", "director"],
        "reject_if_requires_clearance": True,
        "reject_if_location_mismatch": True,
        "reject_if_explicitly_unwanted_domain": []
    }


@pytest.fixture
def sample_runtime_config():
    """Return sample runtime config."""
    return {
        "mode": "volume_first",
        "default_decision_on_uncertainty": "apply",
        "human_approval_before_submit": True,
        "auto_submit_linkedin_easy_apply": True,
        "auto_submit_greenhouse": False,
        "auto_submit_workday": False,
        "attempt_field_corrections_before_escalation": True,
        "max_field_retries": 2,
        "max_issue_minutes": 3,
        "pause_on_cover_letter_detection": True,
        "manual_signup_only": True,
        "update_google_sheet_after_each_application": True,
        "local_timezone": "America/Los_Angeles"
    }


@pytest.fixture
def sample_trusted_domains():
    """Return sample trusted domains."""
    return {
        "tier_a": ["linkedin.com", "greenhouse.io", "myworkdayjobs.com"],
        "tier_b": [],
        "tier_c_default": True
    }


@pytest.fixture
def sample_screening_decision_apply():
    """Return a sample apply decision with new schema."""
    return {
        "job_id": "abc123def456",
        "decision": "apply",
        "matched_reject_rules": [],
        "reason_summary": "No hard reject rules triggered",
        "evidence": [],
        "generated_at": "2024-01-15T10:00:00Z",
        "role_domain": "Software Engineering",
        "industry": "Technology",
        "experience_years_required": None,
    }


@pytest.fixture
def sample_screening_decision_reject():
    """Return a sample reject decision with evidence."""
    return {
        "job_id": "abc123def456",
        "decision": "reject",
        "matched_reject_rules": ["reject_senior_titles"],
        "reason_summary": "Title contains senior keyword",
        "evidence": ["Title contains 'Senior': Senior Software Engineer"],
        "generated_at": "2024-01-15T10:00:00Z",
        "role_domain": "Software Engineering",
        "industry": "Technology",
        "experience_years_required": 5,
    }


@pytest.fixture
def sample_application_packet():
    """Return a sample application packet with new schema."""
    return {
        "packet_id": "pkt123abc",
        "job_id": "abc123def456",
        "company": "Acme Corp",
        "title": "Software Engineer",
        "location": "San Francisco, CA",
        "source": "linkedin",
        "source_url": "https://linkedin.com/jobs/view/12345",
        "apply_url": "https://linkedin.com/jobs/apply/12345",
        "ats_type": "linkedin_easy_apply",
        "trust_tier": "tier_a",
        "resume_path": "config/applicant/resume.pdf",
        "cover_letter_path": None,
        "applicant_answers_path": "config/applicant/applicant_master_answers.md",
        "job_snapshot_path": "data/normalized_jobs/abc123def456.json",
        "screening_decision_path": "data/screened_jobs/abc123def456.json",
        "submit_policy": {
            "human_approval_required": True,
            "auto_submit_allowed": True
        },
        "escalation_policy": {
            "manual_signup_only": True,
            "max_field_retries": 2,
            "max_issue_minutes": 3
        },
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": None
    }
