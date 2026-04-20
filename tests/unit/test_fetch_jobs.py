"""Tests for the LinkedIn RapidAPI fetcher."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from ingest.fetch_jobs import (  # noqa: E402
    _build_title_filter,
    _map_api_job,
    fetch_from_linkedin,
)
from ingest.normalize_jobs import normalize_job  # noqa: E402
from utils.json_validate import validate_normalized_job  # noqa: E402


@pytest.fixture
def linkedin_api_sample(fixtures_dir):
    """Load the sample LinkedIn API response."""
    with open(fixtures_dir / "linkedin_api_sample.json") as f:
        return json.load(f)


class TestTitleFilter:
    def test_quotes_each_phrase(self):
        result = _build_title_filter(["IAM Analyst", "SOC Analyst I"])
        assert result == '"IAM Analyst" OR "SOC Analyst I"'

    def test_skips_blanks(self):
        result = _build_title_filter(["IAM Analyst", "", "  ", "SOC Analyst"])
        assert result == '"IAM Analyst" OR "SOC Analyst"'

    def test_empty(self):
        assert _build_title_filter([]) == ""


class TestMapApiJob:
    def test_prefers_external_apply_url(self, linkedin_api_sample):
        api_job = dict(linkedin_api_sample[0])
        api_job["external_apply_url"] = "https://joveo.com/careers/123"
        mapped = _map_api_job(api_job)
        assert mapped["apply_url"] == "https://joveo.com/careers/123"
        assert mapped["source_url"] == api_job["url"]

    def test_falls_back_to_linkedin_url(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[0])
        assert mapped["apply_url"] == linkedin_api_sample[0]["url"]
        assert mapped["source_url"] == linkedin_api_sample[0]["url"]

    def test_first_employment_type(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[0])
        assert mapped["employment_type"] == "FULL_TIME"

    def test_first_location(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[1])
        assert mapped["location"] == "New York, New York, United States"

    def test_metadata_carries_linkedin_fields(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[1])
        md = mapped["metadata"]
        assert md["directapply"] is False
        assert md["seniority"] == "Mid-Senior level"
        assert md["linkedin_org_slug"] == "capital-one"
        assert md["ats_duplicate"] is True

    def test_stringifies_source_posting_id(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[0])
        assert mapped["source_posting_id"] == "2114102402"
        assert isinstance(mapped["source_posting_id"], str)


class TestIntegrationWithNormalizer:
    """Mapped jobs must feed cleanly into normalize_job + schema validation."""

    def test_mapped_job_normalizes_and_validates(self, linkedin_api_sample):
        mapped = _map_api_job(linkedin_api_sample[0])
        # save_raw_jobs adds these; simulate it.
        mapped["_source"] = "linkedin"
        mapped["_fetched_at"] = "2026-04-18T19:00:00Z"

        normalized = normalize_job(mapped)
        is_valid, errors = validate_normalized_job(normalized)
        assert is_valid, f"Validation errors: {errors}"
        assert normalized["source"] == "linkedin"
        assert normalized["company"] == "Joveo Ai"
        assert normalized["title"] == "Graduate Data Engineer"
        # Metadata flowed into source_attributes via normalizer.
        assert normalized["source_attributes"]["seniority"] == "Not Applicable"


class TestFetchFromLinkedin:
    def test_missing_api_key_returns_empty(self, monkeypatch, capsys):
        monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
        result = fetch_from_linkedin(["IAM Analyst"], {})
        assert result == []
        assert "RAPIDAPI_KEY is not set" in capsys.readouterr().out

    def test_unknown_endpoint_returns_empty(self, monkeypatch, capsys):
        monkeypatch.setenv("RAPIDAPI_KEY", "dummy")
        result = fetch_from_linkedin(
            ["IAM Analyst"], {"linkedin_api": {"endpoint": "bogus"}}
        )
        assert result == []
        assert "Unknown linkedin_api.endpoint" in capsys.readouterr().out

    def test_no_titles_returns_empty(self, monkeypatch, capsys):
        monkeypatch.setenv("RAPIDAPI_KEY", "dummy")
        result = fetch_from_linkedin([], {})
        assert result == []
        assert "No titles configured" in capsys.readouterr().out

    def test_pagination_stops_on_short_page(self, monkeypatch, linkedin_api_sample):
        monkeypatch.setenv("RAPIDAPI_KEY", "dummy")
        monkeypatch.setenv("RAPIDAPI_HOST", "example.test")

        calls = []

        def fake_request(host, endpoint_path, params, api_key):
            calls.append(params["offset"])
            return linkedin_api_sample, {"x-ratelimit-jobs-remaining": "100"}

        with patch("ingest.fetch_jobs._request_linkedin_page", side_effect=fake_request):
            result = fetch_from_linkedin(
                ["IAM Analyst"],
                {"linkedin_api": {"max_jobs": 500, "endpoint": "7d"}},
            )

        # Fixture has 2 records (< page size 100), so we stop after one call.
        assert calls == [0]
        assert len(result) == 2
        assert result[0]["company"] == "Joveo Ai"

    def test_respects_max_jobs(self, monkeypatch, linkedin_api_sample):
        monkeypatch.setenv("RAPIDAPI_KEY", "dummy")
        with patch(
            "ingest.fetch_jobs._request_linkedin_page",
            return_value=(linkedin_api_sample, {}),
        ):
            result = fetch_from_linkedin(
                ["IAM Analyst"],
                {"linkedin_api": {"max_jobs": 1, "endpoint": "7d"}},
            )
        assert len(result) == 1
