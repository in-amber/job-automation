from __future__ import annotations

from nicegui import ui

from dashboard import config_io

RESUME_MAX_BYTES = 5_000_000


def _text_file_editor(rel_path: str, label: str) -> None:
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


def _render_resume() -> None:
    rel_path = "applicant/resume.pdf"

    with ui.card().classes("w-full mt-4"):
        ui.label("Resume").classes("text-base font-semibold")
        ui.label(f"config/{rel_path}").classes("text-xs text-gray-500")
        ui.label("Upload replaces the current resume.pdf. PDF only, max 5 MB.").classes(
            "text-xs text-gray-600"
        )

        status = ui.label("").classes("text-sm mt-2")

        def handle_upload(e) -> None:
            try:
                data = e.content.read()
                if not data.startswith(b"%PDF"):
                    raise config_io.ValidationError(
                        "uploaded file is not a PDF (missing %PDF header)"
                    )
                config_io.save_bytes(rel_path, data, max_bytes=RESUME_MAX_BYTES)
                status.text = f"Saved {e.name} ({len(data):,} bytes)."
                status.classes(replace="text-sm mt-2 text-green-700")
            except config_io.ValidationError as exc:
                status.text = f"Rejected: {exc}"
                status.classes(replace="text-sm mt-2 text-red-700")
            except Exception as exc:  # noqa: BLE001
                status.text = f"Upload failed: {exc}"
                status.classes(replace="text-sm mt-2 text-red-700")

        ui.upload(
            label="Choose PDF",
            auto_upload=True,
            max_file_size=RESUME_MAX_BYTES,
            on_upload=handle_upload,
        ).props('accept="application/pdf,.pdf"').classes("mt-2")


def render() -> None:
    _text_file_editor("applicant/applicant_master_answers.md", "Applicant master answers")
    _text_file_editor("applicant/cover_letters_master.md", "Cover letters master")
    _render_resume()
