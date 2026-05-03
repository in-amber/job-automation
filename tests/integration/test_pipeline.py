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

    def test_packet_starts_with_no_cover_letter(
        self,
        sample_normalized_job,
        sample_screening_decision_apply,
        sample_runtime_config,
        sample_trusted_domains,
    ):
        """Fresh packets always start without a cover letter attached.

        The apply step moves the packet to waiting_for_cover_letter_approval
        if the form actually demands one — screening no longer predicts it.
        """
        from packets.build_application_packets import build_packet

        packet = build_packet(
            sample_normalized_job,
            sample_screening_decision_apply,
            sample_runtime_config,
            sample_trusted_domains,
        )

        assert packet['cover_letter_path'] is None
