from nicegui import ui

from dashboard.pages import admin, applicant, overview, runs, search_prefs

TABS = ("Overview", "Search prefs", "Applicant", "Runs", "Admin")


@ui.page("/")
def index() -> None:
    with ui.header().classes("items-center"):
        ui.label("Job Automation Dashboard").classes("text-lg font-semibold")

    with ui.tabs().classes("w-full") as tabs:
        tab_refs = {name: ui.tab(name) for name in TABS}

    with ui.tab_panels(tabs, value=tab_refs["Overview"]).classes("w-full"):
        with ui.tab_panel(tab_refs["Overview"]):
            overview.render()
        with ui.tab_panel(tab_refs["Search prefs"]):
            search_prefs.render()
        with ui.tab_panel(tab_refs["Applicant"]):
            applicant.render()
        with ui.tab_panel(tab_refs["Runs"]):
            runs.render()
        with ui.tab_panel(tab_refs["Admin"]):
            admin.render()


def main() -> None:
    ui.run(host="0.0.0.0", port=8080, show=False, reload=False, title="Job Automation")
