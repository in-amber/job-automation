"""Read-only loaders for data/* and config/*. No mutation here."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DASHBOARD_DATA_DIR", "/app/data"))
CONFIG_DIR = Path(os.environ.get("DASHBOARD_CONFIG_DIR", "/app/config"))

QUEUE_STATES = (
    "ready_to_apply",
    "in_progress",
    "completed",
    "rejected",
    "failed",
    "waiting_for_cover_letter_approval",
    "waiting_for_human_review",
    "waiting_for_signup",
)
WAITING_STATES = tuple(s for s in QUEUE_STATES if s.startswith("waiting_for_"))
IN_FLIGHT_STATES = ("ready_to_apply", "in_progress")


def _read_json(path: Path) -> dict | None:
    try:
        with path.open() as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("skipping unreadable file %s: %s", path, exc)
        return None


def queue_dir(state: str) -> Path:
    return DATA_DIR / "queues" / state


def queue_count(state: str) -> int:
    d = queue_dir(state)
    if not d.exists():
        return 0
    return sum(1 for _ in d.glob("*.json"))


def queue_counts() -> dict[str, int]:
    return {state: queue_count(state) for state in QUEUE_STATES}


def in_flight_count() -> int:
    return sum(queue_count(s) for s in IN_FLIGHT_STATES)


def escalated_count() -> int:
    return sum(queue_count(s) for s in WAITING_STATES)


def iter_packets(state: str) -> Iterable[dict]:
    d = queue_dir(state)
    if not d.exists():
        return
    for path in d.glob("*.json"):
        packet = _read_json(path)
        if packet is not None:
            yield packet


def packet_locations() -> dict[str, str]:
    """Map packet_id -> queue state for every packet currently in a queue."""
    out: dict[str, str] = {}
    for state in QUEUE_STATES:
        d = queue_dir(state)
        if not d.exists():
            continue
        for path in d.glob("*.json"):
            out[path.stem] = state
    return out


def iter_run_logs() -> Iterable[dict]:
    d = DATA_DIR / "run_logs"
    if not d.exists():
        return
    # Only the modern `run_*.json` shape; older files predate the schema.
    for path in d.glob("run_*.json"):
        log_entry = _read_json(path)
        if log_entry is not None:
            yield log_entry


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def failed_run_count(within_days: int = 30) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=within_days)
    count = 0
    for entry in iter_run_logs():
        if entry.get("result") != "failed":
            continue
        started = _parse_iso(entry.get("started_at"))
        if started is None or started >= cutoff:
            count += 1
    return count


def iter_screened() -> Iterable[dict]:
    d = DATA_DIR / "screened_jobs"
    if not d.exists():
        return
    for path in d.glob("*.json"):
        decision = _read_json(path)
        if decision is not None:
            yield decision


def location_breakdown(top_n: int = 10) -> list[tuple[str, int]]:
    """Top N cities among completed packets, by count.

    City is the substring before the first comma in packet 'location'.
    Packets without a location are bucketed as '(unknown)'.
    """
    counts: dict[str, int] = {}
    for packet in iter_packets("completed"):
        loc = packet.get("location") or ""
        city = loc.split(",", 1)[0].strip() or "(unknown)"
        counts[city] = counts.get(city, 0) + 1
    ordered = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    return ordered[:top_n]


def screening_decision_counts() -> dict[str, int]:
    out = {"apply": 0, "reject": 0}
    for decision in iter_screened():
        d = decision.get("decision")
        if d in out:
            out[d] += 1
    return out


def screened_factor_breakdown(
    field: str, decision: str | None = "apply"
) -> list[tuple[str, int]]:
    """Group screened decisions by a factor field ('role_domain', 'industry',
    'experience_years_required'), filtered by ``decision`` ('apply', 'reject', or
    None for all). Returns ``(value, count)`` pairs sorted by count desc.

    Factor fields are required on every new decision. ``'(missing)'`` only
    appears for legacy decisions written before the audit-fields requirement
    landed; ``'(unspecified)'`` is used when the field is present but null
    (e.g., experience_years_required for postings with no hard requirement, or
    factor sentinels on synthetic location-prefilter rejects).
    """
    counts: dict[str, int] = {}
    for d in iter_screened():
        if decision is not None and d.get("decision") != decision:
            continue
        if field not in d:
            key = "(missing)"
        else:
            value = d[field]
            key = "(unspecified)" if value is None else str(value)
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def reject_reason_counts() -> list[tuple[str, int]]:
    """Counts of matched_reject_rules across all rejected screenings, sorted desc."""
    counts: dict[str, int] = {}
    for decision in iter_screened():
        if decision.get("decision") != "reject":
            continue
        for rule in decision.get("matched_reject_rules") or []:
            counts[rule] = counts.get(rule, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def applications_per_day(within_days: int = 30) -> list[tuple[str, int]]:
    """Return (YYYY-MM-DD, count) for each day in the window, oldest first."""
    today = datetime.now(timezone.utc).date()
    earliest = today - timedelta(days=within_days - 1)
    buckets: dict[str, int] = {
        (earliest + timedelta(days=i)).isoformat(): 0 for i in range(within_days)
    }

    for packet in iter_packets("completed"):
        ts = _parse_iso(packet.get("updated_at")) or _parse_iso(packet.get("created_at"))
        if ts is None:
            continue
        day = ts.astimezone(timezone.utc).date()
        if day < earliest or day > today:
            continue
        buckets[day.isoformat()] += 1

    return sorted(buckets.items())
