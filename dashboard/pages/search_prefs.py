from __future__ import annotations

from copy import deepcopy

from nicegui import ui

from dashboard import config_io

ENABLED_FACTORS = ("experience", "role_domain", "industry", "clearance", "location")


class StringListEditor:
    """Editable list of strings — add/remove/edit rows in place."""

    def __init__(self, items: list[str], label: str) -> None:
        self.items = items
        self.label = label
        with ui.column().classes("w-full gap-1") as self.container:
            pass
        self._render()

    def _render(self) -> None:
        self.container.clear()
        with self.container:
            ui.label(self.label).classes("text-xs uppercase text-gray-500")
            for i, _ in enumerate(self.items):
                with ui.row().classes("gap-2 items-center w-full no-wrap"):
                    inp = ui.input(value=self.items[i]).classes("flex-1")
                    inp.on_value_change(
                        lambda e, idx=i: self.items.__setitem__(idx, e.value or "")
                    )
                    ui.button(
                        icon="close",
                        on_click=lambda _, idx=i: self._remove(idx),
                    ).props("flat dense round")
            ui.button("+ Add", on_click=self._add).props("flat dense").classes("self-start")

    def _remove(self, idx: int) -> None:
        self.items.pop(idx)
        self._render()

    def _add(self) -> None:
        self.items.append("")
        self._render()


def _bind_bool(state: dict, key: str):
    return lambda e: state.update({key: bool(e.value)})


def _bind_int(state: dict, key: str):
    def setter(e):
        try:
            state[key] = int(e.value) if e.value is not None else 0
        except (TypeError, ValueError):
            pass
    return setter


def _strip_blank(items: list[str]) -> list[str]:
    return [x.strip() for x in items if x and x.strip()]


def _normalize_search_filters(state: dict) -> dict:
    out = deepcopy(state)
    out["locations"] = _strip_blank(out["locations"])
    out["keywords_include"] = _strip_blank(out["keywords_include"])
    out["keywords_exclude"] = _strip_blank(out["keywords_exclude"])
    return out


def _normalize_reject_rules(state: dict) -> dict:
    out = deepcopy(state)
    out["senior_title_keywords"] = _strip_blank(out["senior_title_keywords"])
    out["reject_if_explicitly_unwanted_domain"] = _strip_blank(
        out["reject_if_explicitly_unwanted_domain"]
    )
    return out


SEARCH_FILTERS_OWNED_KEYS = (
    "locations",
    "remote_allowed",
    "onsite_allowed",
    "hybrid_allowed",
    "keywords_include",
    "keywords_exclude",
)


def _render_search_filters() -> None:
    state = config_io.load_json("search/search_filters.json")

    with ui.card().classes("w-full"):
        ui.label("Search filters").classes("text-base font-semibold")
        ui.label("config/search/search_filters.json").classes("text-xs text-gray-500")

        StringListEditor(state["locations"], "Locations")

        with ui.row().classes("gap-4 mt-2"):
            ui.checkbox("Remote allowed", value=state["remote_allowed"]).on_value_change(
                _bind_bool(state, "remote_allowed")
            )
            ui.checkbox("Onsite allowed", value=state["onsite_allowed"]).on_value_change(
                _bind_bool(state, "onsite_allowed")
            )
            ui.checkbox("Hybrid allowed", value=state["hybrid_allowed"]).on_value_change(
                _bind_bool(state, "hybrid_allowed")
            )

        StringListEditor(state["keywords_include"], "Keywords — include")
        StringListEditor(state["keywords_exclude"], "Keywords — exclude")

        status = ui.label("").classes("text-sm mt-2")

        def save() -> None:
            try:
                normalized = _normalize_search_filters(state)
                # Re-read fresh so concurrent edits to linkedin_api (Admin tab)
                # are preserved.
                full = config_io.load_json("search/search_filters.json")
                for key in SEARCH_FILTERS_OWNED_KEYS:
                    full[key] = normalized[key]
                config_io.save_json(
                    "search/search_filters.json",
                    full,
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


def _render_reject_rules() -> None:
    state = config_io.load_json("search/reject_rules.json")

    with ui.card().classes("w-full mt-4"):
        ui.label("Reject rules").classes("text-base font-semibold")
        ui.label("config/search/reject_rules.json").classes("text-xs text-gray-500")

        ui.select(
            options=list(ENABLED_FACTORS),
            multiple=True,
            value=list(state["enabled_factors"]),
            label="enabled_factors",
        ).classes("w-full").props("use-chips").on_value_change(
            lambda e: state.update({"enabled_factors": list(e.value or [])})
        )

        with ui.row().classes("gap-4 items-center mt-2"):
            ui.number(
                "max_required_years_experience",
                value=state["max_required_years_experience"],
                min=0,
                max=50,
            ).on_value_change(_bind_int(state, "max_required_years_experience"))
            ui.checkbox(
                "reject_senior_titles", value=state["reject_senior_titles"]
            ).on_value_change(_bind_bool(state, "reject_senior_titles"))

        StringListEditor(state["senior_title_keywords"], "senior_title_keywords")

        with ui.column().classes("gap-1 mt-2"):
            ui.checkbox(
                "reject_if_requires_clearance",
                value=state["reject_if_requires_clearance"],
            ).on_value_change(_bind_bool(state, "reject_if_requires_clearance"))
            ui.checkbox(
                "reject_if_location_mismatch",
                value=state["reject_if_location_mismatch"],
            ).on_value_change(_bind_bool(state, "reject_if_location_mismatch"))
            ui.checkbox(
                "reject_if_role_not_in_approved_domains",
                value=state["reject_if_role_not_in_approved_domains"],
            ).on_value_change(
                _bind_bool(state, "reject_if_role_not_in_approved_domains")
            )
            ui.checkbox(
                "reject_if_industry_not_in_approved",
                value=state["reject_if_industry_not_in_approved"],
            ).on_value_change(
                _bind_bool(state, "reject_if_industry_not_in_approved")
            )

        StringListEditor(
            state["reject_if_explicitly_unwanted_domain"],
            "reject_if_explicitly_unwanted_domain",
        )

        status = ui.label("").classes("text-sm mt-2")

        def save() -> None:
            try:
                config_io.save_json(
                    "search/reject_rules.json",
                    _normalize_reject_rules(state),
                    "reject_rules.schema.json",
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


def _render_text_file(rel_path: str, label: str) -> None:
    content = config_io.load_text(rel_path)
    state = {"text": content}

    with ui.card().classes("w-full mt-4"):
        ui.label(label).classes("text-base font-semibold")
        ui.label(f"config/{rel_path}").classes("text-xs text-gray-500")
        editor = ui.textarea(value=content).classes("w-full").props("autogrow filled")
        editor.on_value_change(lambda e: state.update({"text": e.value or ""}))

        status = ui.label("").classes("text-sm mt-2")

        def save() -> None:
            try:
                config_io.save_text(rel_path, state["text"])
                status.text = "Saved."
                status.classes(replace="text-sm mt-2 text-green-700")
            except Exception as exc:  # noqa: BLE001
                status.text = f"Save failed: {exc}"
                status.classes(replace="text-sm mt-2 text-red-700")

        ui.button("Save", on_click=save).props("color=primary").classes("mt-2")


def render() -> None:
    _render_search_filters()
    _render_reject_rules()
    _render_text_file("search/approved_role_domains.md", "Approved role domains")
    _render_text_file("search/approved_industries.md", "Approved industries")
    _render_text_file("search/titles.txt", "Titles")
