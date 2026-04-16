"""JSON Schema validation utilities."""
import json
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import Draft202012Validator
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False
    Draft202012Validator = None

# Cache for loaded schemas
_schema_cache: dict[str, dict] = {}


def load_schema(schema_name: str, schemas_dir: Path | str | None = None) -> dict:
    """Load a JSON schema by name."""
    if schema_name in _schema_cache:
        return _schema_cache[schema_name]

    if schemas_dir is None:
        # Default to project schemas directory
        schemas_dir = Path(__file__).parent.parent.parent / 'schemas'
    else:
        schemas_dir = Path(schemas_dir)

    schema_file = schema_name if schema_name.endswith('.json') else f"{schema_name}.schema.json"
    schema_path = schemas_dir / schema_file

    with open(schema_path, 'r', encoding='utf-8') as f:
        schema = json.load(f)

    _schema_cache[schema_name] = schema
    return schema


def validate_against_schema(data: dict[str, Any], schema_name: str) -> tuple[bool, list[str]]:
    """
    Validate data against a named schema.

    Returns:
        Tuple of (is_valid, error_messages)
    """
    if not HAS_JSONSCHEMA:
        # If jsonschema not installed, skip validation
        return True, []

    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = list(validator.iter_errors(data))

    if not errors:
        return True, []

    error_messages = []
    for error in errors:
        path = ' -> '.join(str(p) for p in error.absolute_path) if error.absolute_path else 'root'
        error_messages.append(f"{path}: {error.message}")

    return False, error_messages


def validate_normalized_job(data: dict) -> tuple[bool, list[str]]:
    """Validate a normalized job object."""
    return validate_against_schema(data, 'normalized_job')


def validate_screening_decision(data: dict) -> tuple[bool, list[str]]:
    """Validate a screening decision object."""
    return validate_against_schema(data, 'screening_decision')


def validate_application_packet(data: dict) -> tuple[bool, list[str]]:
    """Validate an application packet object."""
    return validate_against_schema(data, 'application_packet')


def validate_run_log(data: dict) -> tuple[bool, list[str]]:
    """Validate a run log object."""
    return validate_against_schema(data, 'run_log')


def validate_intervention_report(data: dict) -> tuple[bool, list[str]]:
    """Validate an intervention report object."""
    return validate_against_schema(data, 'intervention_report')
