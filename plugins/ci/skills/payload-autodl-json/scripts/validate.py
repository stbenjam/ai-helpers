#!/usr/bin/env python3
"""Validate a payload-analysis autodl JSON file against the schema.

Usage: python3 validate.py <path-to-json>

Exits 0 if valid, 1 if invalid (prints errors to stderr).
Uses only Python standard library.
"""

import json
import sys

EXPECTED_TABLE = "payload_triage"

SCHEMA_FIELDS = {
    "payload_tag": "string",
    "version": "string",
    "stream": "string",
    "architecture": "string",
    "phase": "string",
    "release_controller_url": "string",
    "analyzed_at": "string",
    "rejection_streak": "int64",
    "total_blocking_jobs": "int64",
    "failed_blocking_jobs": "int64",
    "force_accept_recommended": "int64",
    "job_name": "string",
    "prow_url": "string",
    "failure_type": "string",
    "root_cause_summary": "string",
    "streak_length": "int64",
    "is_new_failure": "int64",
    "originating_payload_tag": "string",
    "candidate_pr_url": "string",
    "candidate_title": "string",
    "candidate_repo": "string",
    "candidate_confidence_score": "int64",
    "candidate_rationale": "string",
    "revert_pr_url": "string",
    "revert_pr_status": "string",
}

INT64_FIELDS = {
    k for k, v in SCHEMA_FIELDS.items() if v == "int64"
}

VALID_FAILURE_TYPES = {"test", "install", "upgrade", "infra", ""}
VALID_REVERT_STATUSES = {"open", "merged", "draft", "closed", ""}


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Root must be a JSON object"]

    if data.get("table_name") != EXPECTED_TABLE:
        errors.append(
            f"table_name: expected '{EXPECTED_TABLE}', "
            f"got '{data.get('table_name')}'"
        )

    schema = data.get("schema")
    if not isinstance(schema, dict):
        errors.append("schema: must be an object")
    else:
        for field, typ in SCHEMA_FIELDS.items():
            if field not in schema:
                errors.append(f"schema: missing field '{field}'")
            elif schema[field] != typ:
                errors.append(
                    f"schema.{field}: expected type '{typ}', "
                    f"got '{schema[field]}'"
                )
        for field in schema:
            if field not in SCHEMA_FIELDS:
                errors.append(f"schema: unexpected field '{field}'")

    if data.get("schema_mapping") is not None:
        errors.append("schema_mapping: must be null")

    if data.get("chunk_size") != 0:
        errors.append(f"chunk_size: expected 0, got {data.get('chunk_size')}")
    if data.get("expiration_days") != 0:
        errors.append(
            f"expiration_days: expected 0, got {data.get('expiration_days')}"
        )
    if data.get("partition_column") != "":
        errors.append(
            f"partition_column: expected '', "
            f"got '{data.get('partition_column')}'"
        )

    rows = data.get("rows")
    if not isinstance(rows, list):
        errors.append("rows: must be an array")
    else:
        if len(rows) == 0:
            errors.append("rows: must have at least one row")

        for i, row in enumerate(rows):
            prefix = f"rows[{i}]"
            if not isinstance(row, dict):
                errors.append(f"{prefix}: must be an object")
                continue

            for field in SCHEMA_FIELDS:
                if field not in row:
                    errors.append(f"{prefix}: missing field '{field}'")
                    continue
                val = row[field]
                if not isinstance(val, str):
                    errors.append(
                        f"{prefix}.{field}: all values must be strings, "
                        f"got {type(val).__name__}"
                    )
                elif field in INT64_FIELDS and val != "":
                    try:
                        int(val)
                    except ValueError:
                        errors.append(
                            f"{prefix}.{field}: '{val}' is not a valid "
                            f"integer string"
                        )

            for field in row:
                if field not in SCHEMA_FIELDS:
                    errors.append(f"{prefix}: unexpected field '{field}'")

            ft = row.get("failure_type", "")
            if ft not in VALID_FAILURE_TYPES:
                errors.append(
                    f"{prefix}.failure_type: '{ft}' not in "
                    f"{VALID_FAILURE_TYPES}"
                )

            rs = row.get("revert_pr_status", "")
            if rs not in VALID_REVERT_STATUSES:
                errors.append(
                    f"{prefix}.revert_pr_status: '{rs}' not in "
                    f"{VALID_REVERT_STATUSES}"
                )

            inf = row.get("is_new_failure", "")
            if inf not in ("0", "1", ""):
                errors.append(
                    f"{prefix}.is_new_failure: must be '0' or '1', "
                    f"got '{inf}'"
                )

            far = row.get("force_accept_recommended", "")
            if far not in ("0", "1", ""):
                errors.append(
                    f"{prefix}.force_accept_recommended: must be '0' or '1', "
                    f"got '{far}'"
                )

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-json>", file=sys.stderr)
        sys.exit(2)

    path = sys.argv[1]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate(data)

    if errors:
        print(f"Validation failed ({len(errors)} errors):", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Valid: {path}", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
