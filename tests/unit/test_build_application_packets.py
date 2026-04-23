"""Tests for the application-packet builder."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from packets.build_application_packets import classify_ats  # noqa: E402


class TestClassifyAts:
    def test_linkedin_easy_apply_when_directapply_true(self):
        job = {
            "source": "linkedin",
            "apply_url": "https://www.linkedin.com/jobs/view/abc-123",
            "source_attributes": {"directapply": True},
        }
        assert classify_ats(job) == "linkedin_easy_apply"

    def test_linkedin_external_when_directapply_false(self):
        job = {
            "source": "linkedin",
            "apply_url": "https://www.linkedin.com/jobs/view/abc-123",
            "source_attributes": {"directapply": False},
        }
        assert classify_ats(job) == "other"

    def test_linkedin_external_when_directapply_missing(self):
        job = {
            "source": "linkedin",
            "apply_url": "https://www.linkedin.com/jobs/view/abc-123",
            "source_attributes": {},
        }
        assert classify_ats(job) == "other"

    def test_greenhouse(self):
        job = {
            "source": "greenhouse",
            "apply_url": "https://boards.greenhouse.io/acme/jobs/123",
            "source_attributes": {},
        }
        assert classify_ats(job) == "greenhouse"

    def test_workday(self):
        job = {
            "source": "workday",
            "apply_url": "https://acme.wd5.myworkdayjobs.com/en-US/External/job/123",
            "source_attributes": {},
        }
        assert classify_ats(job) == "workday"

    def test_unknown_ats(self):
        job = {
            "source": "other",
            "apply_url": "https://jobs.example.com/apply/123",
            "source_attributes": {},
        }
        assert classify_ats(job) == "other"
