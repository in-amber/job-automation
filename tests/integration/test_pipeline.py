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
