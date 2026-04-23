"""
Integration tests for the full pipeline.

These tests verify end-to-end behavior without external dependencies.
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


class TestScreeningPipeline:
    """Test the screening pipeline end-to-end."""

    def test_volume_first_behavior(self, sample_normalized_job, sample_reject_rules):
        """Verify volume-first: most jobs should pass screening."""
        from screening.screen_jobs import screen_job_locally

        # Jobs without clear reject triggers should apply
        jobs = [
            {"job_id": "1", "title": "Software Engineer", "description_clean": "Join our team."},
            {"job_id": "2", "title": "Backend Developer", "description_clean": "Build APIs."},
            {"job_id": "3", "title": "Full Stack Engineer", "description_clean": "Work on products."},
            {"job_id": "4", "title": "Junior Developer", "description_clean": "Entry level role."},
            {"job_id": "5", "title": "Engineer II", "description_clean": "Mid-level position."},
        ]

        apply_count = 0
        for job in jobs:
            decision = screen_job_locally(job, sample_reject_rules)
            if decision["decision"] == "apply":
                apply_count += 1

        # All should apply (no senior titles, no high experience requirements)
        assert apply_count == len(jobs), "Volume-first: all ambiguous jobs should apply"

    def test_rejection_requires_clear_trigger_and_evidence(self, sample_reject_rules):
        """Verify rejections only happen with clear rule triggers and have evidence."""
        from screening.screen_jobs import screen_job_locally

        # Only jobs with clear triggers should reject
        reject_jobs = [
            {"job_id": "1", "title": "Senior Engineer", "description_clean": "Senior role."},
            {"job_id": "2", "title": "Staff Developer", "description_clean": "Staff level."},
            {"job_id": "3", "title": "Lead Engineer", "description_clean": "Leadership role."},
        ]

        for job in reject_jobs:
            decision = screen_job_locally(job, sample_reject_rules)
            assert decision["decision"] == "reject", f"Clear trigger should reject: {job['title']}"
            assert len(decision["matched_reject_rules"]) > 0, "Rejection must have matched rules"
            assert len(decision["evidence"]) > 0, "Rejection must have evidence"


class TestPacketBuilding:
    """Test packet building from screened jobs."""

    def test_ats_classification(self):
        """Verify ATS types are correctly classified."""
        from packets.build_application_packets import classify_ats

        def job(apply_url, source, directapply=None):
            attrs = {} if directapply is None else {"directapply": directapply}
            return {"apply_url": apply_url, "source": source, "source_attributes": attrs}

        assert classify_ats(job("https://linkedin.com/jobs/easy/123", "linkedin", directapply=True)) == "linkedin_easy_apply"
        assert classify_ats(job("https://linkedin.com/jobs/view/123", "linkedin", directapply=False)) == "other"
        assert classify_ats(job("https://boards.greenhouse.io/company/123", "greenhouse")) == "greenhouse"
        assert classify_ats(job("https://company.myworkdayjobs.com/123", "workday")) == "workday"
        assert classify_ats(job("https://random-company.com/careers", "other")) == "other"

    def test_trust_tier_assignment(self):
        """Verify trust tiers are correctly assigned."""
        from packets.build_application_packets import get_trust_tier

        trusted = {
            "tier_a": ["linkedin.com", "greenhouse.io", "myworkdayjobs.com"],
            "tier_b": ["lever.co"],
            "tier_c_default": True
        }

        assert get_trust_tier("linkedin.com", trusted) == "tier_a"
        assert get_trust_tier("boards.greenhouse.io", trusted) == "tier_a"
        assert get_trust_tier("lever.co", trusted) == "tier_b"
        assert get_trust_tier("unknown.com", trusted) == "tier_c"

    def test_structured_submit_policy(self, sample_runtime_config, sample_trusted_domains):
        """Verify submit policy is built as structured object."""
        from packets.build_application_packets import build_submit_policy

        policy = build_submit_policy("linkedin_easy_apply", "tier_a", sample_runtime_config)

        assert "human_approval_required" in policy
        assert "auto_submit_allowed" in policy
        assert isinstance(policy["human_approval_required"], bool)
        assert isinstance(policy["auto_submit_allowed"], bool)

    def test_structured_escalation_policy(self, sample_runtime_config):
        """Verify escalation policy is built as structured object."""
        from packets.build_application_packets import build_escalation_policy

        policy = build_escalation_policy(sample_runtime_config)

        assert "manual_signup_only" in policy
        assert "max_field_retries" in policy
        assert "max_issue_minutes" in policy
        assert isinstance(policy["max_field_retries"], int)

    def test_cover_letter_status_from_signal(self):
        """Verify cover letter status is determined from signal."""
        from packets.build_application_packets import determine_cover_letter_status

        # Explicitly required
        decision = {"cover_letter_signal": "explicitly_required"}
        assert determine_cover_letter_status(decision) == "predicted_needed_draft_pending"

        # Optional signal
        decision = {"cover_letter_signal": "optional_signal"}
        assert determine_cover_letter_status(decision) == "predicted_needed_draft_pending"

        # No signal or unknown
        decision = {"cover_letter_signal": "no_signal"}
        assert determine_cover_letter_status(decision) == "not_needed"

        decision = {"cover_letter_signal": "unknown"}
        assert determine_cover_letter_status(decision) == "not_needed"


class TestQueueManagement:
    """Test queue management operations."""

    def test_cover_letter_routing(self):
        """Verify packets are routed based on cover letter status."""
        from queues.enqueue_packet import get_target_queue

        # Needing cover letter goes to waiting
        assert get_target_queue({
            "cover_letter_status": "predicted_needed_draft_pending"
        }) == "waiting_for_cover_letter_approval"

        # Not needing cover letter goes to ready
        assert get_target_queue({
            "cover_letter_status": "not_needed"
        }) == "ready_to_apply"

        # Approved cover letter goes to ready
        assert get_target_queue({
            "cover_letter_status": "approved"
        }) == "ready_to_apply"

    def test_no_status_field_dependency(self):
        """Verify queue routing doesn't depend on status field."""
        from queues.enqueue_packet import get_target_queue

        # Packet without status field should work
        packet = {"cover_letter_status": "not_needed"}
        assert get_target_queue(packet) == "ready_to_apply"

        # Packet with status field should ignore it
        packet = {"cover_letter_status": "not_needed", "status": "old_status"}
        assert get_target_queue(packet) == "ready_to_apply"
