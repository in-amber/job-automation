"""Read/validate/backup/write helpers for config/* files.

Write path: validate -> backup -> atomic replace. Reads are unguarded.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

from dashboard.data_io import CONFIG_DIR

SCHEMAS_DIR = Path(os.environ.get("DASHBOARD_SCHEMAS_DIR", "/app/schemas"))
BACKUPS_DIR = CONFIG_DIR / ".backups"


class ValidationError(Exception):
    """Raised when a save is rejected by schema validation."""


def _resolve(rel_path: str) -> Path:
    path = (CONFIG_DIR / rel_path).resolve()
    config_root = CONFIG_DIR.resolve()
    if config_root not in path.parents and path != config_root:
        raise ValueError(f"path escapes config dir: {rel_path}")
    return path


def load_json(rel_path: str) -> dict:
    with _resolve(rel_path).open() as fh:
        return json.load(fh)


def load_text(rel_path: str) -> str:
    return _resolve(rel_path).read_text()


def _load_schema(schema_name: str) -> dict:
    with (SCHEMAS_DIR / schema_name).open() as fh:
        return json.load(fh)


def _validate(data: dict, schema_name: str) -> None:
    schema = _load_schema(schema_name)
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        loc = ".".join(str(p) for p in exc.absolute_path) or "<root>"
        raise ValidationError(f"{loc}: {exc.message}") from exc


def _backup(target: Path, rel_path: str) -> None:
    if not target.exists():
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = BACKUPS_DIR / f"{rel_path}.{stamp}.bak"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, backup_path)


def _atomic_write(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content)
    os.replace(tmp, target)


def save_json(rel_path: str, data: dict, schema_name: str) -> None:
    _validate(data, schema_name)
    target = _resolve(rel_path)
    _backup(target, rel_path)
    _atomic_write(target, json.dumps(data, indent=2) + "\n")


def save_text(rel_path: str, content: str, max_bytes: int | None = None) -> None:
    if max_bytes is not None and len(content.encode("utf-8")) > max_bytes:
        raise ValidationError(f"content exceeds {max_bytes} bytes")
    target = _resolve(rel_path)
    _backup(target, rel_path)
    _atomic_write(target, content)


def save_bytes(rel_path: str, content: bytes, max_bytes: int | None = None) -> None:
    if max_bytes is not None and len(content) > max_bytes:
        raise ValidationError(f"content exceeds {max_bytes} bytes")
    target = _resolve(rel_path)
    _backup(target, rel_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_bytes(content)
    os.replace(tmp, target)
