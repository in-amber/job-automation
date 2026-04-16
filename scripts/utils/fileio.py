"""File I/O utilities."""
import json
from pathlib import Path
from typing import Any


def ensure_dir(path: Path | str) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json(path: Path | str) -> dict[str, Any]:
    """Read and parse a JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def write_json(path: Path | str, data: dict[str, Any], indent: int = 2) -> None:
    """Write data to a JSON file."""
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def read_text(path: Path | str) -> str:
    """Read a text file."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write_text(path: Path | str, content: str) -> None:
    """Write content to a text file."""
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


def read_lines(path: Path | str, skip_comments: bool = True) -> list[str]:
    """Read non-empty lines from a text file, optionally skipping comments."""
    content = read_text(path)
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if skip_comments and line.startswith('#'):
            continue
        lines.append(line)
    return lines


def list_json_files(directory: Path | str) -> list[Path]:
    """List all JSON files in a directory."""
    directory = Path(directory)
    if not directory.exists():
        return []
    return sorted(directory.glob('*.json'))
