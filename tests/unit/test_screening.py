"""
Tests for screening logic.

CRITICAL: These tests verify the volume-first screening policy.
Default behavior must be APPLY unless a hard reject rule clearly triggers.
Rejections must include evidence.
"""
import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from screening.screen_jobs import screen_job_locally


class TestVolumeFirstPolicy:
    """Test that screening defaults to APPLY."""

    def test_no_rules_triggered_should_apply(self, sample_normalized_job, sample_reject_rules):
        """Jobs with no triggered rules should result in APPLY."""
        decision = screen_job_locally(sample_normalized_job, sample_reject_rules)

        assert decision["decision"] == "apply"
        assert len(decision["matched_reject_rules"]) == 0
        assert "cover_letter_signal" in decision

    def test_preferred_experience_should_apply(self, sample_reject_rules):
        """Preferred experience is not a hard requirement - should APPLY."""
        job = {
            "job_id": "test001",
            "title": "Software Engineer",
            "description_clean": "5 years experience preferred. Nice to have Python skills."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "apply"
        assert len(decision["matched_reject_rules"]) == 0

    def test_ideally_has_should_apply(self, sample_reject_rules):
        """'Ideally has' is soft language - should APPLY."""
        job = {
            "job_id": "test002",
            "title": "Backend Developer",
            "description_clean": "Ideally has 3-5 years of experience building APIs."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "apply"

    def test_ambiguous_level_should_apply(self, sample_reject_rules):
        """Ambiguous seniority levels should APPLY."""
        job = {
            "job_id": "test003",
            "title": "Software Engineer II",
            "description_clean": "Join our growing team."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "apply"

    def test_experience_at_limit_should_apply(self, sample_reject_rules):
        """Experience at the limit (1 year) should APPLY."""
        job = {
            "job_id": "test004",
            "title": "Junior Developer",
            "description_clean": "1 year of experience required."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "apply"


class TestHardRejectRules:
    """Test that hard reject rules trigger properly with evidence."""

    def test_senior_title_should_reject_with_evidence(self, sample_reject_rules):
        """Senior in title should trigger rejection with evidence."""
        job = {
            "job_id": "test101",
            "title": "Senior Software Engineer",
            "description_clean": "Looking for an experienced engineer."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert "reject_senior_titles" in decision["matched_reject_rules"]
        assert len(decision["evidence"]) > 0
        assert any("Senior" in ev for ev in decision["evidence"])

    def test_staff_title_should_reject_with_evidence(self, sample_reject_rules):
        """Staff in title should trigger rejection with evidence."""
        job = {
            "job_id": "test102",
            "title": "Staff Engineer",
            "description_clean": "Staff level position."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert "reject_senior_titles" in decision["matched_reject_rules"]
        assert len(decision["evidence"]) > 0

    def test_lead_title_should_reject(self, sample_reject_rules):
        """Lead in title should trigger rejection."""
        job = {
            "job_id": "test103",
            "title": "Lead Backend Engineer",
            "description_clean": "Technical leadership role."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert len(decision["evidence"]) > 0

    def test_high_experience_required_should_reject_with_evidence(self, sample_reject_rules):
        """Explicit high experience requirement should reject with evidence."""
        job = {
            "job_id": "test104",
            "title": "Software Engineer",
            "description_clean": "Requirements: 5+ years of experience required in software development."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert "max_required_years_experience" in decision["matched_reject_rules"]
        assert len(decision["evidence"]) > 0
        assert any("years" in ev.lower() for ev in decision["evidence"])

    def test_clearance_required_should_reject_with_evidence(self, sample_reject_rules):
        """Security clearance requirement should reject with evidence."""
        job = {
            "job_id": "test105",
            "title": "Software Developer",
            "description_clean": "Must have active TS/SCI security clearance."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert "reject_if_requires_clearance" in decision["matched_reject_rules"]
        assert len(decision["evidence"]) > 0

    def test_top_secret_should_reject(self, sample_reject_rules):
        """Top secret clearance should reject."""
        job = {
            "job_id": "test106",
            "title": "Engineer",
            "description_clean": "Active top secret clearance required."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "reject"
        assert len(decision["evidence"]) > 0


class TestCoverLetterSignal:
    """Test cover letter signal detection."""

    def test_explicit_cover_letter_required(self, sample_reject_rules):
        """Explicitly required cover letter should be detected."""
        job = {
            "job_id": "test201",
            "title": "Software Engineer",
            "description_clean": "Please submit your resume and cover letter required."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["cover_letter_signal"] == "explicitly_required"

    def test_optional_cover_letter_signal(self, sample_reject_rules):
        """Optional cover letter mention should be detected."""
        job = {
            "job_id": "test202",
            "title": "Software Engineer",
            "description_clean": "Submit your resume. Cover letter is welcome but not required."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["cover_letter_signal"] in ["optional_signal", "unknown"]

    def test_no_cover_letter_mention(self, sample_reject_rules):
        """No mention should result in unknown."""
        job = {
            "job_id": "test203",
            "title": "Software Engineer",
            "description_clean": "Join our engineering team. Apply with your resume."
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["cover_letter_signal"] in ["unknown", "no_signal"]


class TestFixtureJobs:
    """Test with fixture jobs that should apply or reject."""

    @pytest.fixture
    def jobs_should_apply(self, fixtures_dir):
        """Load jobs that should apply."""
        with open(fixtures_dir / "jobs_should_apply.json") as f:
            return json.load(f)

    @pytest.fixture
    def jobs_should_reject(self, fixtures_dir):
        """Load jobs that should reject."""
        with open(fixtures_dir / "jobs_should_reject.json") as f:
            return json.load(f)

    def test_all_should_apply_jobs(self, jobs_should_apply, sample_reject_rules):
        """All jobs in should_apply fixture must result in APPLY."""
        for test_case in jobs_should_apply:
            job = test_case["job"]
            decision = screen_job_locally(job, sample_reject_rules)

            assert decision["decision"] == "apply", (
                f"Job '{test_case['name']}' should APPLY. "
                f"Reason: {test_case['reason']}. "
                f"Got: {decision}"
            )

    def test_all_should_reject_jobs_with_evidence(self, jobs_should_reject, sample_reject_rules):
        """All jobs in should_reject fixture must result in REJECT with evidence."""
        for test_case in jobs_should_reject:
            job = test_case["job"]
            expected_rule = test_case.get("expected_rule")

            decision = screen_job_locally(job, sample_reject_rules)

            assert decision["decision"] == "reject", (
                f"Job '{test_case['name']}' should REJECT. "
                f"Reason: {test_case['reason']}. "
                f"Got: {decision}"
            )

            # Rejections must have evidence
            assert len(decision["evidence"]) > 0, (
                f"Job '{test_case['name']}' rejection must have evidence"
            )

            if expected_rule:
                assert expected_rule in decision["matched_reject_rules"], (
                    f"Expected rule '{expected_rule}' not matched for '{test_case['name']}'"
                )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_job_should_apply(self, sample_reject_rules):
        """Empty job with no data should default to APPLY."""
        job = {
            "job_id": "empty001",
            "title": "",
            "description_clean": ""
        }

        decision = screen_job_locally(job, sample_reject_rules)

        assert decision["decision"] == "apply"
        assert decision["cover_letter_signal"] == "unknown"

    def test_disabled_senior_rule(self):
        """With senior rule disabled, senior titles should APPLY."""
        rules = {
            "reject_senior_titles": False,  # Disabled
            "senior_title_keywords": ["senior"],
            "max_required_years_experience": 1
        }
        job = {
            "job_id": "test301",
            "title": "Senior Software Engineer",
            "description_clean": "We need a senior engineer."
        }

        decision = screen_job_locally(job, rules)

        assert decision["decision"] == "apply"

    def test_high_experience_limit(self):
        """With high experience limit, more jobs should APPLY."""
        rules = {
            "reject_senior_titles": False,
            "max_required_years_experience": 10  # High limit
        }
        job = {
            "job_id": "test302",
            "title": "Software Engineer",
            "description_clean": "5 years of experience required."
        }

        decision = screen_job_locally(job, rules)

        assert decision["decision"] == "apply"
