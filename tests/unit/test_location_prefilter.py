"""Tests for the deterministic location prefilter in screen_jobs."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from screening.screen_jobs import screen_location_prefilter  # noqa: E402


SEARCH_FILTERS = {
    "locations": ["San Francisco Bay Area", "Remote", "Sacramento"],
    "remote_allowed": True,
    "onsite_allowed": True,
    "hybrid_allowed": True,
}
REJECT_RULES = {"reject_if_location_mismatch": True}


def _job(location, remote_derived=False):
    return {
        "job_id": "j1",
        "location": location,
        "source_attributes": {"remote_derived": remote_derived},
    }


class TestLocationRejects:
    def test_rejects_onsite_georgia(self):
        decision = screen_location_prefilter(
            _job("Tucker, Georgia, United States"), SEARCH_FILTERS, REJECT_RULES
        )
        assert decision is not None
        assert decision["decision"] == "reject"
        assert decision["matched_reject_rules"] == ["reject_if_location_mismatch"]
        assert "Tucker" in decision["evidence"][0]

    def test_rejects_onsite_rhode_island(self):
        decision = screen_location_prefilter(
            _job("Providence, Rhode Island, United States"), SEARCH_FILTERS, REJECT_RULES
        )
        assert decision is not None
        assert decision["decision"] == "reject"

    def test_rejects_onsite_new_york(self):
        decision = screen_location_prefilter(
            _job("New York, New York, United States"), SEARCH_FILTERS, REJECT_RULES
        )
        assert decision is not None
        assert decision["decision"] == "reject"


class TestLocationAllows:
    def test_allows_san_francisco_ca(self):
        assert screen_location_prefilter(
            _job("San Francisco, California, United States"), SEARCH_FILTERS, REJECT_RULES
        ) is None

    def test_allows_oakland_via_bay_area_bigram(self):
        assert screen_location_prefilter(
            _job("Greater East Bay Area"), SEARCH_FILTERS, REJECT_RULES
        ) is None

    def test_allows_sacramento(self):
        assert screen_location_prefilter(
            _job("Sacramento, California, United States"), SEARCH_FILTERS, REJECT_RULES
        ) is None

    def test_allows_remote_via_remote_derived(self):
        assert screen_location_prefilter(
            _job("Tucker, Georgia, United States", remote_derived=True),
            SEARCH_FILTERS,
            REJECT_RULES,
        ) is None

    def test_allows_remote_via_location_string(self):
        assert screen_location_prefilter(
            _job("Remote, United States"), SEARCH_FILTERS, REJECT_RULES
        ) is None


class TestStateQualifiedEntries:
    """State-qualified entries (e.g. 'Berkeley, California') prevent same-name
    cross-state collisions like 'Berkeley Heights, New Jersey'."""

    QUALIFIED_FILTERS = {
        "locations": [
            "San Francisco, California",
            "Oakland, California",
            "Berkeley, California",
            "Sacramento, California",
            "Remote",
        ],
        "remote_allowed": True,
    }

    def test_rejects_berkeley_heights_new_jersey(self):
        decision = screen_location_prefilter(
            _job("Berkeley Heights, New Jersey, United States"),
            self.QUALIFIED_FILTERS,
            REJECT_RULES,
        )
        assert decision is not None
        assert decision["decision"] == "reject"

    def test_allows_berkeley_california(self):
        assert screen_location_prefilter(
            _job("Berkeley, California, United States"),
            self.QUALIFIED_FILTERS,
            REJECT_RULES,
        ) is None

    def test_allows_san_francisco_california(self):
        assert screen_location_prefilter(
            _job("San Francisco, California, United States"),
            self.QUALIFIED_FILTERS,
            REJECT_RULES,
        ) is None


class TestDefersToDownstream:
    def test_defers_when_location_missing(self):
        assert screen_location_prefilter(
            _job(None), SEARCH_FILTERS, REJECT_RULES
        ) is None

    def test_defers_when_rule_disabled(self):
        assert screen_location_prefilter(
            _job("Tucker, Georgia, United States"),
            SEARCH_FILTERS,
            {"reject_if_location_mismatch": False},
        ) is None

    def test_single_word_requires_whole_word_match(self):
        """'Sacramento' should not match 'Sacramentoville' (whole-word rule)."""
        # Contrived but exercises the whole-word guard.
        decision = screen_location_prefilter(
            _job("Sacramentoville, Nowhere, United States"), SEARCH_FILTERS, REJECT_RULES
        )
        assert decision is not None
        assert decision["decision"] == "reject"
