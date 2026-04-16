#!/usr/bin/env python3
"""
Update Google Sheets with application data.
"""
import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from utils.fileio import read_json, list_json_files
from utils.timestamps import now_iso, parse_iso, format_datetime

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False


QUEUE_DIR = PROJECT_ROOT / "data" / "queues"
RUN_LOGS_DIR = PROJECT_ROOT / "data" / "run_logs"


def get_sheets_service():
    """Get authenticated Google Sheets service."""
    creds_path = os.environ.get(
        'GOOGLE_SHEETS_CREDENTIALS_PATH',
        str(PROJECT_ROOT / 'config' / 'google_credentials.json')
    )

    if not Path(creds_path).exists():
        raise FileNotFoundError(f"Google credentials not found: {creds_path}")

    credentials = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )

    return build('sheets', 'v4', credentials=credentials)


def append_to_sheet(service, sheet_id: str, tab_name: str, values: list[list]) -> int:
    """Append rows to a Google Sheet tab."""
    body = {'values': values}
    result = service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!A:A",
        valueInputOption='USER_ENTERED',
        insertDataOption='INSERT_ROWS',
        body=body
    ).execute()

    return result.get('updates', {}).get('updatedRows', 0)


def packet_to_application_row(packet: dict, run_log: dict | None = None) -> list:
    """Convert a packet to an applications row."""
    return [
        packet.get('packet_id', ''),
        format_datetime(parse_iso(packet.get('created_at', now_iso()))),
        format_datetime(parse_iso(run_log.get('finished_at', now_iso()))) if run_log else '',
        packet.get('company', ''),
        packet.get('title', ''),
        packet.get('location', ''),
        packet.get('source', ''),
        packet.get('source_url', ''),
        packet.get('apply_url', ''),
        packet.get('ats_type', ''),
        packet.get('status', ''),
        packet.get('submit_policy', ''),
        'Yes' if packet.get('cover_letter_path') else 'No',
        packet.get('packet_id', ''),  # artifact_folder
        run_log.get('confirmation_number', '') if run_log else '',
        run_log.get('notes', '') if run_log else ''
    ]


def packet_to_rejection_row(packet: dict, decision: dict) -> list:
    """Convert a rejected packet to a rejections row."""
    return [
        packet.get('job_id', ''),
        format_datetime(parse_iso(decision.get('generated_at', now_iso()))),
        packet.get('company', ''),
        packet.get('title', ''),
        packet.get('source_url', ''),
        ', '.join(decision.get('matched_reject_rules', [])),
        decision.get('reason_summary', ''),
        packet.get('job_snapshot_path', '')
    ]


def intervention_to_row(intervention: dict) -> list:
    """Convert an intervention report to a row."""
    return [
        intervention.get('packet_id', ''),
        intervention.get('company', ''),
        intervention.get('title', ''),
        intervention.get('issue_type', ''),
        intervention.get('issue_summary', ''),
        'open',
        format_datetime(parse_iso(intervention.get('created_at', now_iso()))),
        ''
    ]


def run_log_to_row(run_log: dict) -> list:
    """Convert a run log to a row."""
    return [
        run_log.get('run_id', ''),
        run_log.get('packet_id', ''),
        format_datetime(parse_iso(run_log.get('started_at', now_iso()))),
        format_datetime(parse_iso(run_log.get('finished_at', now_iso()))),
        run_log.get('worker', ''),
        run_log.get('result', ''),
        run_log.get('escalation_reason', ''),
        run_log.get('confirmation_number', ''),
        ''  # log_path
    ]


def sync_completed_applications(service, sheet_id: str) -> int:
    """Sync all completed applications to the sheet."""
    completed_dir = QUEUE_DIR / "completed"
    completed_files = list_json_files(completed_dir)

    rows = []
    for packet_file in completed_files:
        packet = read_json(packet_file)

        # Try to find matching run log
        run_log = None
        for log_file in list_json_files(RUN_LOGS_DIR):
            log = read_json(log_file)
            if log.get('packet_id') == packet.get('packet_id'):
                run_log = log
                break

        rows.append(packet_to_application_row(packet, run_log))

    if rows:
        return append_to_sheet(service, sheet_id, 'applications', rows)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Update Google Sheets")
    parser.add_argument(
        "--sync-all",
        action="store_true",
        help="Sync all completed applications"
    )
    parser.add_argument(
        "--packet-id",
        help="Sync a specific packet"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be synced without updating"
    )
    args = parser.parse_args()

    if not HAS_GOOGLE:
        print("Google API client not installed.")
        print("Install with: pip install google-api-python-client google-auth")
        return 1

    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    if not sheet_id:
        print("GOOGLE_SHEET_ID not set")
        return 1

    try:
        service = get_sheets_service()
    except Exception as e:
        print(f"Failed to connect to Google Sheets: {e}")
        return 1

    if args.dry_run:
        print("Dry run - would sync to sheet:", sheet_id)
        return 0

    if args.sync_all:
        count = sync_completed_applications(service, sheet_id)
        print(f"Synced {count} applications")

    elif args.packet_id:
        # Find and sync specific packet
        from scripts.queues.transition_packet import find_packet
        packet_path = find_packet(args.packet_id)
        if packet_path is None:
            print(f"Packet not found: {args.packet_id}")
            return 1

        packet = read_json(packet_path)
        row = packet_to_application_row(packet)
        count = append_to_sheet(service, sheet_id, 'applications', [row])
        print(f"Synced packet {args.packet_id}")

    else:
        print("Specify --sync-all or --packet-id")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
