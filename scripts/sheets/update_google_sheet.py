#!/usr/bin/env python3
"""
Update Google Sheets with application activity.

Four tabs per SPEC §15: applied, skipped, interventions, runs.
Tab schemas are the single source of truth — used by both --init (creating
tabs/headers) and the row builders.

Idempotency: tracks pushed records in data/.sheets_synced.json so re-running
--sync-all only appends new rows.
"""
import argparse
import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, write_json, list_json_files
from utils.timestamps import now_iso, parse_iso, format_datetime
from queues.transition_packet import get_packet_queue

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


DATA_DIR = PROJECT_ROOT / "data"
QUEUE_DIR = DATA_DIR / "queues"
RUN_LOGS_DIR = DATA_DIR / "run_logs"
SCREENED_DIR = DATA_DIR / "screened_jobs"
NORMALIZED_DIR = DATA_DIR / "normalized_jobs"
INTERVENTIONS_DIR = DATA_DIR / "interventions"
MANIFEST_PATH = DATA_DIR / ".sheets_synced.json"


# ----------------------------------------------------------------------------
# Tab schema — single source of truth.
# ----------------------------------------------------------------------------

TAB_SCHEMAS: dict[str, list[str]] = {
    "applied": [
        "application_id",
        "date_found",
        "date_applied",
        "company",
        "title",
        "location",
        "source",
        "source_url",
        "apply_url",
        "ats_type",
        "status",
        "submission_mode",
        "cover_letter_used",
        "artifact_folder",
        "confirmation_number",
        "notes",
    ],
    "skipped": [
        "job_id",
        "date_screened",
        "company",
        "title",
        "source_url",
        "reject_rule",
        "reason_summary",
        "job_snapshot_path",
    ],
    "interventions": [
        "packet_id",
        "company",
        "title",
        "issue_type",
        "issue_summary",
        "status",
        "created_at",
        "resolved_at",
    ],
    "runs": [
        "run_id",
        "packet_id",
        "started_at",
        "finished_at",
        "worker",
        "result",
        "escalation_reason",
        "confirmation_number",
        "log_path",
    ],
}


# ----------------------------------------------------------------------------
# Env loading and auth.
# ----------------------------------------------------------------------------

def _load_env_file() -> None:
    """Load .env so GOOGLE_SHEET_ID / GOOGLE_SHEETS_CREDENTIALS_PATH are set."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_sheets_service():
    """Return an authenticated Google Sheets v4 service object."""
    creds_path = os.environ.get(
        "GOOGLE_SHEETS_CREDENTIALS_PATH",
        str(PROJECT_ROOT / "config" / "google_credentials.json"),
    )
    if not Path(creds_path).exists():
        raise FileNotFoundError(f"Google credentials not found: {creds_path}")
    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return build("sheets", "v4", credentials=credentials)


# ----------------------------------------------------------------------------
# Tab bootstrap.
# ----------------------------------------------------------------------------

def init_tabs(service, sheet_id: str) -> dict[str, str]:
    """
    Create missing tabs and write/refresh header rows. Idempotent.

    Returns a dict mapping tab_name -> "created" | "header_set" | "ok".
    """
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    existing = {s["properties"]["title"] for s in meta.get("sheets", [])}

    requests = [
        {"addSheet": {"properties": {"title": tab_name}}}
        for tab_name in TAB_SCHEMAS
        if tab_name not in existing
    ]
    actions: dict[str, str] = {}
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=sheet_id, body={"requests": requests}
        ).execute()
        for tab_name in TAB_SCHEMAS:
            if tab_name not in existing:
                actions[tab_name] = "created"

    # Always write headers (overwrites row 1) so renamed columns get fixed.
    data = [
        {
            "range": f"{tab_name}!A1",
            "values": [headers],
        }
        for tab_name, headers in TAB_SCHEMAS.items()
    ]
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=sheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()
    for tab_name in TAB_SCHEMAS:
        actions.setdefault(tab_name, "header_set")
    return actions


def append_to_sheet(service, sheet_id: str, tab_name: str, values: list[list]) -> int:
    """Append rows to the given tab. Returns rows updated."""
    if not values:
        return 0
    body = {"values": values}
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!A:A",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()
    return result.get("updates", {}).get("updatedRows", 0)


# ----------------------------------------------------------------------------
# Helpers used by row builders.
# ----------------------------------------------------------------------------

def _fmt_iso(value: str | None) -> str:
    """Format an ISO timestamp string for a sheet cell, or '' if missing."""
    if not value:
        return ""
    try:
        return format_datetime(parse_iso(value))
    except (ValueError, TypeError):
        return value


def _submission_mode(submit_policy: dict | None) -> str:
    """Derive the submission_mode string from the packet's submit_policy."""
    if not submit_policy:
        return "manual"
    if submit_policy.get("human_approval_required"):
        return "human_approval_required"
    if submit_policy.get("auto_submit_allowed"):
        return "auto_submit"
    return "manual"


# ----------------------------------------------------------------------------
# Row builders. Pure functions. Pass-through values; no I/O.
# ----------------------------------------------------------------------------

def packet_to_application_row(
    packet: dict, status: str, run_log: dict | None = None
) -> list:
    """Build a row for the `applied` tab."""
    run_log = run_log or {}
    return [
        packet.get("packet_id", ""),
        _fmt_iso(packet.get("created_at")),
        _fmt_iso(run_log.get("finished_at")),
        packet.get("company", ""),
        packet.get("title", ""),
        packet.get("location", "") or "",
        packet.get("source", ""),
        packet.get("source_url", ""),
        packet.get("apply_url", ""),
        packet.get("ats_type", ""),
        status,
        _submission_mode(packet.get("submit_policy")),
        "Yes" if packet.get("cover_letter_path") else "No",
        packet.get("packet_id", ""),
        run_log.get("confirmation_number") or "",
        run_log.get("notes") or "",
    ]


def decision_to_rejection_row(decision: dict, normalized_job: dict | None = None) -> list:
    """Build a row for the `skipped` tab from a screening decision."""
    normalized_job = normalized_job or {}
    return [
        decision.get("job_id", ""),
        _fmt_iso(decision.get("generated_at")),
        normalized_job.get("company", ""),
        normalized_job.get("title", ""),
        normalized_job.get("source_url", ""),
        ", ".join(decision.get("matched_reject_rules", [])),
        decision.get("reason_summary", ""),
        f"data/normalized_jobs/{decision.get('job_id', '')}.json",
    ]


def intervention_to_row(intervention: dict, packet: dict | None = None) -> list:
    """Build a row for the `interventions` tab."""
    packet = packet or {}
    return [
        intervention.get("packet_id", ""),
        packet.get("company", ""),
        packet.get("title", ""),
        intervention.get("issue_type", ""),
        intervention.get("issue_summary", ""),
        intervention.get("resolution_status", "open"),
        _fmt_iso(intervention.get("created_at")),
        _fmt_iso(intervention.get("resolved_at")),
    ]


def run_log_to_row(run_log: dict) -> list:
    """Build a row for the `runs` tab."""
    return [
        run_log.get("run_id", ""),
        run_log.get("packet_id", ""),
        _fmt_iso(run_log.get("started_at")),
        _fmt_iso(run_log.get("finished_at")),
        run_log.get("worker", ""),
        run_log.get("result", ""),
        run_log.get("issue_type") or "",
        run_log.get("confirmation_number") or "",
        f"data/run_logs/{run_log.get('run_id', '')}.json",
    ]


# ----------------------------------------------------------------------------
# Sync manifest — local idempotency.
# ----------------------------------------------------------------------------

def _load_manifest() -> dict[str, list[str]]:
    if MANIFEST_PATH.exists():
        return read_json(MANIFEST_PATH)
    return {tab: [] for tab in TAB_SCHEMAS}


def _save_manifest(manifest: dict[str, list[str]]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    write_json(MANIFEST_PATH, manifest)


def _intervention_key(intervention: dict) -> str:
    return f"{intervention.get('packet_id', '')}__{intervention.get('created_at', '')}"


# ----------------------------------------------------------------------------
# Sync functions.
# ----------------------------------------------------------------------------

def _find_run_log_for_packet(packet_id: str) -> dict | None:
    for log_file in list_json_files(RUN_LOGS_DIR):
        log = read_json(log_file)
        if log.get("packet_id") == packet_id:
            return log
    return None


def sync_applied(service, sheet_id: str, manifest: dict) -> int:
    completed_dir = QUEUE_DIR / "completed"
    pushed = set(manifest.get("applied", []))
    rows: list[list] = []
    new_ids: list[str] = []
    for packet_file in list_json_files(completed_dir):
        packet = read_json(packet_file)
        pid = packet.get("packet_id")
        if not pid or pid in pushed:
            continue
        run_log = _find_run_log_for_packet(pid)
        rows.append(packet_to_application_row(packet, status="completed", run_log=run_log))
        new_ids.append(pid)
    count = append_to_sheet(service, sheet_id, "applied", rows)
    manifest["applied"] = sorted(pushed | set(new_ids))
    return count


def sync_skipped(service, sheet_id: str, manifest: dict) -> int:
    pushed = set(manifest.get("skipped", []))
    rows: list[list] = []
    new_ids: list[str] = []
    for decision_file in list_json_files(SCREENED_DIR):
        decision = read_json(decision_file)
        if decision.get("decision") != "reject":
            continue
        jid = decision.get("job_id")
        if not jid or jid in pushed:
            continue
        normalized_path = NORMALIZED_DIR / f"{jid}.json"
        normalized_job = read_json(normalized_path) if normalized_path.exists() else None
        rows.append(decision_to_rejection_row(decision, normalized_job))
        new_ids.append(jid)
    count = append_to_sheet(service, sheet_id, "skipped", rows)
    manifest["skipped"] = sorted(pushed | set(new_ids))
    return count


def sync_interventions(service, sheet_id: str, manifest: dict) -> int:
    if not INTERVENTIONS_DIR.exists():
        return 0
    pushed = set(manifest.get("interventions", []))
    rows: list[list] = []
    new_keys: list[str] = []
    for intervention_file in list_json_files(INTERVENTIONS_DIR):
        intervention = read_json(intervention_file)
        key = _intervention_key(intervention)
        if key in pushed:
            continue
        # Try to fetch packet for company/title.
        packet_path, _ = get_packet_queue(intervention.get("packet_id", ""))
        packet = read_json(packet_path) if packet_path else None
        rows.append(intervention_to_row(intervention, packet))
        new_keys.append(key)
    count = append_to_sheet(service, sheet_id, "interventions", rows)
    manifest["interventions"] = sorted(pushed | set(new_keys))
    return count


def sync_runs(service, sheet_id: str, manifest: dict) -> int:
    pushed = set(manifest.get("runs", []))
    rows: list[list] = []
    new_ids: list[str] = []
    for log_file in list_json_files(RUN_LOGS_DIR):
        log = read_json(log_file)
        rid = log.get("run_id")
        if not rid or rid in pushed:
            continue
        rows.append(run_log_to_row(log))
        new_ids.append(rid)
    count = append_to_sheet(service, sheet_id, "runs", rows)
    manifest["runs"] = sorted(pushed | set(new_ids))
    return count


def sync_packet(service, sheet_id: str, packet_id: str, manifest: dict) -> dict[str, int]:
    """Push a single packet's application row + matching run log + interventions."""
    packet_path, queue_name = get_packet_queue(packet_id)
    if packet_path is None:
        raise FileNotFoundError(f"Packet not found in any queue: {packet_id}")

    packet = read_json(packet_path)
    status = queue_name if queue_name and queue_name != "application_packets" else "pending"
    run_log = _find_run_log_for_packet(packet_id)

    written: dict[str, int] = {"applied": 0, "runs": 0, "interventions": 0}

    # Application row.
    if packet_id not in set(manifest.get("applied", [])):
        written["applied"] = append_to_sheet(
            service, sheet_id, "applied",
            [packet_to_application_row(packet, status=status, run_log=run_log)],
        )
        manifest.setdefault("applied", []).append(packet_id)

    # Run log row.
    if run_log:
        rid = run_log.get("run_id")
        if rid and rid not in set(manifest.get("runs", [])):
            written["runs"] = append_to_sheet(
                service, sheet_id, "runs", [run_log_to_row(run_log)]
            )
            manifest.setdefault("runs", []).append(rid)

    # Intervention rows for this packet.
    if INTERVENTIONS_DIR.exists():
        new_int_keys: list[str] = []
        rows: list[list] = []
        pushed_int = set(manifest.get("interventions", []))
        for intervention_file in list_json_files(INTERVENTIONS_DIR):
            intervention = read_json(intervention_file)
            if intervention.get("packet_id") != packet_id:
                continue
            key = _intervention_key(intervention)
            if key in pushed_int:
                continue
            rows.append(intervention_to_row(intervention, packet))
            new_int_keys.append(key)
        if rows:
            written["interventions"] = append_to_sheet(
                service, sheet_id, "interventions", rows
            )
            manifest.setdefault("interventions", []).extend(new_int_keys)

    return written


# ----------------------------------------------------------------------------
# CLI.
# ----------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Update Google Sheets")
    parser.add_argument(
        "--init", action="store_true",
        help="Create the 4 tabs (applied, skipped, interventions, runs) with headers"
    )
    parser.add_argument(
        "--sync-all", action="store_true",
        help="Sync new completed apps, skipped jobs, interventions, and run logs"
    )
    parser.add_argument(
        "--packet-id",
        help="Sync one packet (application + matching run log + interventions)"
    )
    parser.add_argument(
        "--reset-manifest", action="store_true",
        help="Clear the local sync manifest (next sync re-pushes everything)"
    )
    args = parser.parse_args()

    _load_env_file()

    if not HAS_GOOGLE:
        print("Google API client not installed.")
        print("Install with: pip install google-api-python-client google-auth")
        return 1

    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if not sheet_id:
        print("GOOGLE_SHEET_ID not set in .env")
        return 1

    if args.reset_manifest:
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink()
        print("Sync manifest reset.")
        if not (args.init or args.sync_all or args.packet_id):
            return 0

    try:
        service = get_sheets_service()
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        return 1

    if args.init:
        try:
            actions = init_tabs(service, sheet_id)
        except HttpError as e:
            print(f"Sheets API error during --init: {e}")
            return 1
        for tab, action in actions.items():
            print(f"  {tab}: {action}")
        print(f"Initialized sheet {sheet_id}")
        if not (args.sync_all or args.packet_id):
            return 0

    manifest = _load_manifest()

    if args.sync_all:
        results = {
            "applied": sync_applied(service, sheet_id, manifest),
            "skipped": sync_skipped(service, sheet_id, manifest),
            "interventions": sync_interventions(service, sheet_id, manifest),
            "runs": sync_runs(service, sheet_id, manifest),
        }
        _save_manifest(manifest)
        for tab, count in results.items():
            print(f"  {tab}: {count} new rows")
        return 0

    if args.packet_id:
        try:
            written = sync_packet(service, sheet_id, args.packet_id, manifest)
        except FileNotFoundError as e:
            print(str(e))
            return 1
        _save_manifest(manifest)
        for tab, count in written.items():
            print(f"  {tab}: {count} new rows")
        return 0

    if not args.init:
        print("Specify --init, --sync-all, --packet-id, or --reset-manifest")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
