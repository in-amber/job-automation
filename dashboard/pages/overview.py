from nicegui import ui

from dashboard import data_io


def _tile(label: str, value: int | str) -> None:
    with ui.card().classes("min-w-40"):
        ui.label(label).classes("text-xs uppercase text-gray-500")
        ui.label(str(value)).classes("text-3xl font-semibold")


def render() -> None:
    completed = data_io.queue_count("completed")
    in_flight = data_io.in_flight_count()
    escalated = data_io.escalated_count()
    failed_30d = data_io.failed_run_count(within_days=30)

    with ui.row().classes("gap-4 w-full"):
        _tile("Applied (all time)", completed)
        _tile("In flight", in_flight)
        _tile("Escalated", escalated)
        _tile("Failed runs (30d)", failed_30d)

    daily = data_io.applications_per_day(within_days=30)
    dates = [d for d, _ in daily]
    counts = [c for _, c in daily]

    with ui.card().classes("w-full mt-4"):
        ui.label("Applications per day (last 30 days)").classes(
            "text-sm font-semibold"
        )
        ui.echart(
            {
                "tooltip": {"trigger": "axis"},
                "grid": {"left": 40, "right": 16, "top": 16, "bottom": 40},
                "xAxis": {
                    "type": "category",
                    "data": dates,
                    "axisLabel": {"rotate": 45, "fontSize": 10},
                },
                "yAxis": {"type": "value", "minInterval": 1},
                "series": [{"type": "bar", "data": counts, "name": "Applications"}],
            }
        ).classes("h-72 w-full")

    locations = data_io.location_breakdown(top_n=10)
    with ui.card().classes("w-full mt-4"):
        ui.label("Top 10 locations (completed packets)").classes("text-sm font-semibold")
        if locations:
            cities = [c for c, _ in locations]
            counts_by_city = [n for _, n in locations]
            ui.echart(
                {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": 120, "right": 16, "top": 16, "bottom": 24},
                    "xAxis": {"type": "value", "minInterval": 1},
                    "yAxis": {
                        "type": "category",
                        "data": list(reversed(cities)),
                    },
                    "series": [
                        {
                            "type": "bar",
                            "data": list(reversed(counts_by_city)),
                            "name": "Applications",
                        }
                    ],
                }
            ).classes("h-72 w-full")
        else:
            ui.label("No completed packets yet.").classes("text-sm text-gray-600")

    decisions = data_io.screening_decision_counts()
    rejects = data_io.reject_reason_counts()
    with ui.row().classes("w-full gap-4 mt-4 no-wrap"):
        with ui.card().classes("flex-1"):
            ui.label("Screening decisions").classes("text-sm font-semibold")
            ui.echart(
                {
                    "tooltip": {"trigger": "axis"},
                    "grid": {"left": 40, "right": 16, "top": 16, "bottom": 30},
                    "xAxis": {"type": "category", "data": ["apply", "reject"]},
                    "yAxis": {"type": "value", "minInterval": 1},
                    "series": [
                        {
                            "type": "bar",
                            "data": [decisions["apply"], decisions["reject"]],
                            "name": "Decisions",
                        }
                    ],
                }
            ).classes("h-64 w-full")

        with ui.card().classes("flex-1"):
            ui.label("Reject reasons").classes("text-sm font-semibold")
            if rejects:
                rule_names = [r for r, _ in rejects]
                rule_counts = [n for _, n in rejects]
                ui.echart(
                    {
                        "tooltip": {"trigger": "axis"},
                        "grid": {"left": 200, "right": 16, "top": 16, "bottom": 24},
                        "xAxis": {"type": "value", "minInterval": 1},
                        "yAxis": {
                            "type": "category",
                            "data": list(reversed(rule_names)),
                            "axisLabel": {"fontSize": 10},
                        },
                        "series": [
                            {
                                "type": "bar",
                                "data": list(reversed(rule_counts)),
                                "name": "Rejects",
                            }
                        ],
                    }
                ).classes("h-64 w-full")
            else:
                ui.label("No rejections recorded.").classes("text-sm text-gray-600")

    queue_counts = data_io.queue_counts()
    with ui.card().classes("w-full mt-4"):
        ui.label("Queue depths").classes("text-sm font-semibold")
        with ui.row().classes("gap-3 flex-wrap"):
            for state, count in queue_counts.items():
                with ui.column().classes("items-center px-3 py-2 bg-gray-50 rounded"):
                    ui.label(str(count)).classes("text-xl font-semibold")
                    ui.label(state).classes("text-xs text-gray-600")
