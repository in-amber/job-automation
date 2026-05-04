from __future__ import annotations

from nicegui import ui

from dashboard import config_io


def _bind_text(state: dict, key: str):
    return lambda e: state.update({key: e.value or ""})


def _bind_bool(state: dict, key: str):
    return lambda e: state.update({key: bool(e.value)})


def _bind_int(state: dict, key: str):
    def setter(e):
        try:
            state[key] = int(e.value) if e.value is not None else 0
        except (TypeError, ValueError):
            pass
    return setter


def _render_linkedin_api() -> None:
    full = config_io.load_json("search/search_filters.json")
    api = dict(full.get("linkedin_api") or {})

    with ui.card().classes("w-full"):
        ui.label("LinkedIn API").classes("text-base font-semibold")
        ui.label("config/search/search_filters.json → linkedin_api").classes(
            "text-xs text-gray-500"
        )

        with ui.column().classes("w-full gap-2"):
            ui.input("endpoint", value=api.get("endpoint", "")).classes(
                "w-full"
            ).on_value_change(_bind_text(api, "endpoint"))
            ui.input("location_filter", value=api.get("location_filter", "")).classes(
                "w-full"
            ).on_value_change(_bind_text(api, "location_filter"))
            ui.input("seniority_filter", value=api.get("seniority_filter", "")).classes(
                "w-full"
            ).on_value_change(_bind_text(api, "seniority_filter"))
            with ui.row().classes("gap-4 items-center"):
                ui.number(
                    "max_jobs", value=api.get("max_jobs", 500), min=1, max=5000
                ).on_value_change(_bind_int(api, "max_jobs"))
                ui.checkbox(
                    "include_description", value=api.get("include_description", True)
                ).on_value_change(_bind_bool(api, "include_description"))

        status = ui.label("").classes("text-sm mt-2")

        def save() -> None:
            try:
                # Re-read fresh so concurrent edits to non-LinkedIn fields
                # (Search prefs tab) are preserved.
                fresh = config_io.load_json("search/search_filters.json")
                fresh["linkedin_api"] = dict(api)
                config_io.save_json(
                    "search/search_filters.json",
                    fresh,
                    "search_filters.schema.json",
                )
                status.text = "Saved."
                status.classes(replace="text-sm mt-2 text-green-700")
            except config_io.ValidationError as exc:
                status.text = f"Validation error: {exc}"
                status.classes(replace="text-sm mt-2 text-red-700")
            except Exception as exc:  # noqa: BLE001
                status.text = f"Save failed: {exc}"
                status.classes(replace="text-sm mt-2 text-red-700")

        ui.button("Save", on_click=save).props("color=primary").classes("mt-2")


def render() -> None:
    _render_linkedin_api()
