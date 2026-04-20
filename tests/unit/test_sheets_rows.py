"""Tests for Google Sheets row builders. Pure functions; no live API calls."""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from sheets.update_google_sheet import (  # noqa: E402
    TAB_SCHEMAS,
    _submission_mode,
    decision_to_rejection_row,
    intervention_to_row,
    packet_to_application_row,
    run_log_to_row,
)


@pytest.fixture
def sample_run_log():
    return {
        "run_id": "run_abc",
        "packet_id": "pkt123abc",
        "worker": "cowork",
        "started_at": "2026-04-19T10:00:00Z",
        "finished_at": "2026-04-19T10:02:00Z",
        "result": "submitted",
        "confirmation_number": "CONF-9999",
        "issue_type": None,
        "notes": "clean apply",
    }


@pytest.fixture
def sample_normalized_for_reject():
    return {
        "company": "Capital One",
        "title": "Lead Data Engineer",
        "source_url": "https://www.linkedin.com/jobs/view/abc",
    }


class TestSubmissionMode:
    def test_human_approval_required_wins(self):
        assert _submission_mode(
            {"human_approval_required": True, "auto_submit_allowed": True}
        ) == "human_approval_required"

    def test_auto_submit_only(self):
        assert _submission_mode(
            {"human_approval_required": False, "auto_submit_allowed": True}
        ) == "auto_submit"

    def test_neither_falls_to_manual(self):
        assert _submission_mode(
            {"human_approval_required": False, "auto_submit_allowed": False}
        ) == "manual"

    def test_none_policy(self):
        assert _submission_mode(None) == "manual"


class TestApplicationRow:
    def test_column_count_matches_schema(self, sample_application_packet, sample_run_log):
        row = packet_to_application_row(
            sample_application_packet, status="completed", run_log=sample_run_log
        )
        assert len(row) == len(TAB_SCHEMAS["applied"])

    def test_status_passes_through(self, sample_application_packet):
        row = packet_to_application_row(sample_application_packet, status="in_progress")
        idx = TAB_SCHEMAS["applied"].index("status")
        assert row[idx] == "in_progress"

    def test_submission_mode_derived(self, sample_application_packet):
        # Fixture has both flags True → human_approval_required wins.
        row = packet_to_application_row(sample_application_packet, status="completed")
        idx = TAB_SCHEMAS["applied"].index("submission_mode")
        assert row[idx] == "human_approval_required"

    def test_cover_letter_used_no(self, sample_application_packet):
        # Fixture has cover_letter_path = None.
        row = packet_to_application_row(sample_application_packet, status="completed")
        idx = TAB_SCHEMAS["applied"].index("cover_letter_used")
        assert row[idx] == "No"

    def test_cover_letter_used_yes(self, sample_application_packet):
        packet = {**sample_application_packet, "cover_letter_path": "artifacts/cover_letters/x.txt"}
        row = packet_to_application_row(packet, status="completed")
        idx = TAB_SCHEMAS["applied"].index("cover_letter_used")
        assert row[idx] == "Yes"

    def test_run_log_fields_carry(self, sample_application_packet, sample_run_log):
        row = packet_to_application_row(
            sample_application_packet, status="completed", run_log=sample_run_log
        )
        cols = TAB_SCHEMAS["applied"]
        assert row[cols.index("confirmation_number")] == "CONF-9999"
        assert row[cols.index("notes")] == "clean apply"
        assert row[cols.index("date_applied")]  # non-empty

    def test_missing_run_log_blank_application_fields(self, sample_application_packet):
        row = packet_to_application_row(sample_application_packet, status="completed")
        cols = TAB_SCHEMAS["applied"]
        assert row[cols.index("date_applied")] == ""
        assert row[cols.index("confirmation_number")] == ""
        assert row[cols.index("notes")] == ""

    def test_null_location_becomes_empty_string(self, sample_application_packet):
        packet = {**sample_application_packet, "location": None}
        row = packet_to_application_row(packet, status="completed")
        idx = TAB_SCHEMAS["applied"].index("location")
        assert row[idx] == ""


class TestRejectionRow:
    def test_column_count(self, sample_screening_decision_reject, sample_normalized_for_reject):
        row = decision_to_rejection_row(
            sample_screening_decision_reject, sample_normalized_for_reject
        )
        assert len(row) == len(TAB_SCHEMAS["skipped"])

    def test_reject_rules_joined(self, sample_screening_decision_reject):
        row = decision_to_rejection_row(sample_screening_decision_reject)
        idx = TAB_SCHEMAS["skipped"].index("reject_rule")
        assert row[idx] == "reject_senior_titles"

    def test_company_title_from_normalized(
        self, sample_screening_decision_reject, sample_normalized_for_reject
    ):
        row = decision_to_rejection_row(
            sample_screening_decision_reject, sample_normalized_for_reject
        )
        cols = TAB_SCHEMAS["skipped"]
        assert row[cols.index("company")] == "Capital One"
        assert row[cols.index("title")] == "Lead Data Engineer"

    def test_missing_normalized_blank_company(self, sample_screening_decision_reject):
        row = decision_to_rejection_row(sample_screening_decision_reject, None)
        idx = TAB_SCHEMAS["skipped"].index("company")
        assert row[idx] == ""

    def test_snapshot_path_uses_job_id(self, sample_screening_decision_reject):
        row = decision_to_rejection_row(sample_screening_decision_reject)
        idx = TAB_SCHEMAS["skipped"].index("job_snapshot_path")
        assert row[idx] == "data/normalized_jobs/abc123def456.json"


class TestInterventionRow:
    def test_column_count(self):
        intervention = {
            "packet_id": "pkt1",
            "issue_type": "captcha",
            "issue_summary": "hCaptcha on apply page",
            "required_human_action": "solve_captcha",
            "created_at": "2026-04-19T10:00:00Z",
        }
        row = intervention_to_row(intervention)
        assert len(row) == len(TAB_SCHEMAS["interventions"])

    def test_pulls_company_title_from_packet(self, sample_application_packet):
        intervention = {
            "packet_id": "pkt123abc",
            "issue_type": "missing_answer",
            "issue_summary": "no answer for 'sponsorship'",
            "required_human_action": "answer_missing_question",
            "created_at": "2026-04-19T10:00:00Z",
        }
        row = intervention_to_row(intervention, sample_application_packet)
        cols = TAB_SCHEMAS["interventions"]
        assert row[cols.index("company")] == "Acme Corp"
        assert row[cols.index("title")] == "Software Engineer"

    def test_default_status_open(self):
        intervention = {
            "packet_id": "pkt1",
            "issue_type": "captcha",
            "issue_summary": "x",
            "required_human_action": "solve_captcha",
            "created_at": "2026-04-19T10:00:00Z",
        }
        row = intervention_to_row(intervention)
        idx = TAB_SCHEMAS["interventions"].index("status")
        assert row[idx] == "open"


class TestRunRow:
    def test_column_count(self, sample_run_log):
        row = run_log_to_row(sample_run_log)
        assert len(row) == len(TAB_SCHEMAS["runs"])

    def test_log_path_uses_run_id(self, sample_run_log):
        row = run_log_to_row(sample_run_log)
        idx = TAB_SCHEMAS["runs"].index("log_path")
        assert row[idx] == "data/run_logs/run_abc.json"

    def test_escalation_reason_from_issue_type(self):
        log = {
            "run_id": "run_x",
            "packet_id": "pkt1",
            "worker": "cowork",
            "started_at": "2026-04-19T10:00:00Z",
            "result": "waiting_for_signup",
            "issue_type": "signup_required",
        }
        row = run_log_to_row(log)
        idx = TAB_SCHEMAS["runs"].index("escalation_reason")
        assert row[idx] == "signup_required"

    def test_null_issue_type_blank(self, sample_run_log):
        row = run_log_to_row(sample_run_log)
        idx = TAB_SCHEMAS["runs"].index("escalation_reason")
        assert row[idx] == ""
