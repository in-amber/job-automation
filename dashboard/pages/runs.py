from collections import Counter
from datetime import datetime, timedelta, timezone

from nicegui import ui

from dashboard import data_io

RESULT_VALUES = (
    "submitted",
    "waiting_for_signup",
    "waiting_for_cover_letter",
    "waiting_for_human_review",
    "expired_posting",
    "failed",
)


def _row_from_log(entry: dict, locations: dict[str, str]) -> dict:
    packet_id = entry.get("packet_id", "")
    return {
        "started_at": entry.get("started_at") or "",
        "finished_at": entry.get("finished_at") or "",
        "packet_id": packet_id,
        "result": entry.get("result") or "",
        "issue_type": entry.get("issue_type") or "",
        "notes": entry.get("notes") or "",
        "packet_state": locations.get(packet_id, ""),
    }


def _matches(row: dict, results: list[str], start: str, end: str, search: str) -> bool:
    if results and row["result"] not in results:
        return False
    if start and row["started_at"] and row["started_at"][:10] < start:
        return False
    if end and row["started_at"] and row["started_at"][:10] > end:
        return False
    if search and search.lower() not in row["notes"].lower():
        return False
    return True


def render() -> None:
    locations = data_io.packet_locations()
    all_rows = sorted(
        (_row_from_log(e, locations) for e in data_io.iter_run_logs()),
        key=lambda r: r["started_at"],
        reverse=True,
    )

    today = datetime.now(timezone.utc).date()
    default_start = (today - timedelta(days=30)).isoformat()

    state = {
        "results": list(RESULT_VALUES),
        "start": default_start,
        "end": "",
        "search": "",
    }

    columns = [
        {"name": "started_at", "label": "Started", "field": "started_at", "sortable": True, "align": "left"},
        {"name": "finished_at", "label": "Finished", "field": "finished_at", "sortable": True, "align": "left"},
        {"name": "packet_id", "label": "Packet", "field": "packet_id", "sortable": True, "align": "left"},
        {"name": "result", "label": "Result", "field": "result", "sortable": True, "align": "left"},
        {"name": "issue_type", "label": "Issue", "field": "issue_type", "sortable": True, "align": "left"},
        {"name": "packet_state", "label": "Currently in", "field": "packet_state", "sortable": True, "align": "left"},
        {"name": "notes", "label": "Notes", "field": "notes", "align": "left"},
    ]

    summary_label = ui.label().classes("text-sm text-gray-700 mt-2")
    table = ui.table(
        columns=columns,
        rows=[],
        row_key="run_id",
        pagination={"sortBy": "started_at", "descending": True, "rowsPerPage": 25},
    ).classes("w-full mt-2")

    def refresh() -> None:
        filtered = [
            r
            for r in all_rows
            if _matches(r, state["results"], state["start"], state["end"], state["search"])
        ]
        table.rows = filtered
        table.update()

        result_counts = Counter(r["result"] for r in filtered)
        issue_counts = Counter(r["issue_type"] for r in filtered if r["issue_type"])
        result_str = ", ".join(f"{k}: {v}" for k, v in sorted(result_counts.items())) or "none"
        issue_str = ", ".join(f"{k}: {v}" for k, v in sorted(issue_counts.items())) or "none"
        summary_label.text = (
            f"{len(filtered)} runs in window | by result: {result_str} | "
            f"by issue type: {issue_str}"
        )

    with ui.card().classes("w-full"):
        ui.label("Filters").classes("text-sm font-semibold")
        with ui.row().classes("gap-4 items-end flex-wrap"):
            results_select = ui.select(
                options=list(RESULT_VALUES),
                multiple=True,
                value=state["results"],
                label="Result",
            ).classes("min-w-64").props("use-chips")
            results_select.on_value_change(
                lambda e: (state.update(results=list(e.value)), refresh())
            )

            start_input = ui.input("Start (YYYY-MM-DD)", value=state["start"])
            start_input.on_value_change(
                lambda e: (state.update(start=e.value or ""), refresh())
            )

            end_input = ui.input("End (YYYY-MM-DD)", value=state["end"])
            end_input.on_value_change(
                lambda e: (state.update(end=e.value or ""), refresh())
            )

            search_input = ui.input("Search notes")
            search_input.on_value_change(
                lambda e: (state.update(search=e.value or ""), refresh())
            )

    refresh()
