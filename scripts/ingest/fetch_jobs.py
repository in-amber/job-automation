#!/usr/bin/env python3
"""
Fetch raw job postings from configured sources.

LinkedIn is wired to the RapidAPI LinkedIn Job Search API (fantastic.jobs).
Greenhouse and Workday are still stubs.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import write_json, read_json, read_lines
from utils.timestamps import now_iso, timestamp_for_filename


LINKEDIN_ENDPOINTS = {
    "24h": "/active-jb-24h",
    "7d": "/active-jb-7d",
    "6m": "/active-jb-6m",
}
# Per-endpoint page-size cap. The 6m endpoint supports 500 per request;
# all others cap at 100. Getting this right matters because requests are
# metered — forcing pagination on 6m would burn 5x the request credits.
LINKEDIN_PAGE_SIZE_BY_ENDPOINT = {
    "24h": 100,
    "7d": 100,
    "6m": 500,
}


def _load_env_file() -> None:
    """Best-effort .env loader (avoids python-dotenv dep at fetch time)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _build_title_filter(titles: list[str]) -> str:
    """OR-join titles as RapidAPI title_filter terms.

    Each title is quoted so the API matches it as an in-order phrase
    (e.g. `"IT Support"` matches "IT Support Specialist", "Senior IT Support
    Engineer", etc.). Per the API docs, quoted = in-order phrase match;
    unquoted multi-word = AND of the words in any order.

    Titles in `titles.txt` are intentionally short concept roots, not full
    job titles — that's what gives the OR-of-quoted-roots its breadth.
    """
    quoted = [f'"{t.strip()}"' for t in titles if t.strip()]
    return " OR ".join(quoted)


def _map_api_job(api_job: dict) -> dict:
    """
    Map a LinkedIn RapidAPI record to the raw_job shape expected by
    scripts/ingest/normalize_jobs.py::normalize_job.
    """
    locations = api_job.get("locations_derived") or []
    employment = api_job.get("employment_type") or []
    api_url = api_job.get("url") or ""
    external_url = api_job.get("external_apply_url")
    # Prefer external apply URL when present; LinkedIn view URL otherwise.
    apply_url = external_url or api_url

    return {
        "source_posting_id": str(api_job.get("id", "")),
        "company": api_job.get("organization") or "",
        "title": api_job.get("title") or "",
        "location": locations[0] if locations else None,
        "employment_type": employment[0] if employment else None,
        "apply_url": apply_url,
        "source_url": api_url,
        "description": api_job.get("description_text") or "",
        "salary_text": None,
        "metadata": {
            "date_posted": api_job.get("date_posted"),
            "directapply": api_job.get("directapply"),
            "seniority": api_job.get("seniority"),
            "source_domain": api_job.get("source_domain"),
            "remote_derived": api_job.get("remote_derived"),
            "linkedin_org_industry": api_job.get("linkedin_org_industry"),
            "linkedin_org_employees": api_job.get("linkedin_org_employees"),
            "linkedin_org_recruitment_agency_derived": api_job.get(
                "linkedin_org_recruitment_agency_derived"
            ),
            "linkedin_org_slug": api_job.get("linkedin_org_slug"),
            "ats_duplicate": api_job.get("ats_duplicate"),
            "salary_raw": api_job.get("salary_raw"),
        },
    }


def _request_linkedin_page(
    host: str, endpoint_path: str, params: dict, api_key: str
) -> tuple[list[dict], dict]:
    """Make one paginated call. Returns (jobs, response_headers)."""
    query = urllib.parse.urlencode(
        {k: v for k, v in params.items() if v is not None and v != ""}
    )
    url = f"https://{host}{endpoint_path}?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "x-rapidapi-key": api_key,
            "x-rapidapi-host": host,
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            # Lowercase keys so callers can look up headers case-insensitively.
            headers = {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(
            f"LinkedIn API HTTP {e.code}: {e.reason}. URL: {url}. Body: {detail}"
        ) from e
    except urllib.error.URLError as e:
        raise RuntimeError(f"LinkedIn API network error: {e.reason}") from e

    data = json.loads(body)
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected API response shape: {type(data).__name__}")
    return data, headers


def _log_credits(headers: dict) -> None:
    """Print remaining credit headers if present."""
    jobs_rem = headers.get("x-ratelimit-jobs-remaining")
    reqs_rem = headers.get("x-ratelimit-requests-remaining")
    if jobs_rem or reqs_rem:
        print(f"  credits — jobs remaining: {jobs_rem}, requests remaining: {reqs_rem}")


def fetch_from_linkedin(
    search_titles: list[str], filters: dict, max_jobs_override: int | None = None
) -> list[dict]:
    """Fetch jobs from the RapidAPI LinkedIn Job Search API."""
    api_key = os.environ.get("RAPIDAPI_KEY")
    host = os.environ.get("RAPIDAPI_HOST", "linkedin-job-search-api.p.rapidapi.com")
    if not api_key:
        print("RAPIDAPI_KEY is not set. Add it to .env and re-run.")
        return []

    api_cfg = filters.get("linkedin_api", {}) or {}
    endpoint_key = api_cfg.get("endpoint", "7d")
    endpoint_path = LINKEDIN_ENDPOINTS.get(endpoint_key)
    if not endpoint_path:
        print(f"Unknown linkedin_api.endpoint: {endpoint_key!r} — expected one of {list(LINKEDIN_ENDPOINTS)}")
        return []

    title_filter = _build_title_filter(search_titles)
    if not title_filter:
        print("No titles configured in config/search/titles.txt")
        return []

    max_jobs = int(api_cfg.get("max_jobs", 200))
    if max_jobs_override is not None:
        max_jobs = max_jobs_override
    # Only request as many per page as we still need, capped at the API page size.
    endpoint_page_cap = LINKEDIN_PAGE_SIZE_BY_ENDPOINT.get(endpoint_key, 100)
    page_size = max(1, min(endpoint_page_cap, max_jobs))

    base_params = {
        "title_filter": title_filter,
        "location_filter": api_cfg.get("location_filter") or '"United States"',
        "description_type": "text" if api_cfg.get("include_description", True) else None,
        "seniority_filter": api_cfg.get("seniority_filter") or None,
        "limit": page_size,
    }
    remote_val = api_cfg.get("remote")
    if remote_val is True:
        base_params["remote"] = "true"
    elif remote_val is False:
        base_params["remote"] = "false"

    collected: list[dict] = []
    offset = 0

    print(f"Fetching from LinkedIn API ({endpoint_key}), target up to {max_jobs} jobs")
    print(f"  title_filter: {title_filter[:120]}{'...' if len(title_filter) > 120 else ''}")
    print(f"  location_filter: {base_params['location_filter']}")

    while len(collected) < max_jobs:
        params = dict(base_params)
        params["offset"] = offset
        print(f"  requesting offset={offset}")
        page, headers = _request_linkedin_page(host, endpoint_path, params, api_key)
        _log_credits(headers)
        if not page:
            break
        collected.extend(page)
        if len(page) < page_size:
            break
        offset += page_size

    collected = collected[:max_jobs]
    print(f"Fetched {len(collected)} raw jobs from LinkedIn")
    return [_map_api_job(j) for j in collected]


def fetch_from_greenhouse(search_titles: list[str], filters: dict) -> list[dict]:
    """Fetch jobs from Greenhouse job boards. TODO."""
    print("Greenhouse fetching not yet implemented.")
    return []


def fetch_from_workday(search_titles: list[str], filters: dict) -> list[dict]:
    """Fetch jobs from Workday career sites. TODO."""
    print("Workday fetching not yet implemented.")
    return []


def save_raw_jobs(jobs: list[dict], source: str) -> int:
    """Save raw jobs to the raw_jobs directory."""
    raw_dir = PROJECT_ROOT / "data" / "raw_jobs"
    raw_dir.mkdir(parents=True, exist_ok=True)

    timestamp = timestamp_for_filename()
    saved = 0

    for i, job in enumerate(jobs):
        filename = f"{timestamp}_{source}_{i:04d}.json"
        job["_fetched_at"] = now_iso()
        job["_source"] = source
        write_json(raw_dir / filename, job)
        saved += 1

    return saved


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch raw job postings")
    parser.add_argument(
        "--source",
        choices=["linkedin", "greenhouse", "workday", "all"],
        default="all",
        help="Job source to fetch from"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override max_jobs from config — useful for testing against metered APIs"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved config/filters without calling the API (no credits consumed)"
    )
    args = parser.parse_args()

    _load_env_file()

    titles = read_lines(PROJECT_ROOT / "config" / "search" / "titles.txt")
    filters = read_json(PROJECT_ROOT / "config" / "search" / "search_filters.json")

    print(f"Search titles: {len(titles)} configured")
    print()

    if args.dry_run:
        api_cfg = (filters.get("linkedin_api") or {})
        effective_max = args.limit if args.limit is not None else api_cfg.get("max_jobs", 200)
        print("DRY RUN — not calling the API. Resolved settings:")
        print(f"  source:           {args.source}")
        print(f"  endpoint:         {api_cfg.get('endpoint', '7d')}")
        print(f"  title_filter:     {_build_title_filter(titles)}")
        print(f"  location_filter:  {api_cfg.get('location_filter') or '\"United States\"'}")
        print(f"  seniority_filter: {api_cfg.get('seniority_filter')}")
        print(f"  remote:           {api_cfg.get('remote')}")
        print(f"  max_jobs:         {effective_max}")
        return 0

    all_jobs_by_source: list[tuple[str, list[dict]]] = []

    if args.source in ("linkedin", "all"):
        all_jobs_by_source.append(
            ("linkedin", fetch_from_linkedin(titles, filters, max_jobs_override=args.limit))
        )

    if args.source in ("greenhouse", "all"):
        all_jobs_by_source.append(("greenhouse", fetch_from_greenhouse(titles, filters)))

    if args.source in ("workday", "all"):
        all_jobs_by_source.append(("workday", fetch_from_workday(titles, filters)))

    total_saved = 0
    for source, jobs in all_jobs_by_source:
        if jobs:
            total_saved += save_raw_jobs(jobs, source)

    print(f"\nSaved {total_saved} raw jobs to data/raw_jobs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
