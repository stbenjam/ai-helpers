#!/usr/bin/env python3
"""Validate a payload-results YAML file against the schema.

Usage: python3 validate.py <path-to-yaml>

Exits 0 if valid, 1 if invalid (prints errors to stderr).
Requires PyYAML (pip install pyyaml).
"""

import sys


def _require_yaml():
    try:
        import yaml
        return yaml
    except ImportError:
        print("Error: PyYAML is required. Install with: pip install pyyaml",
              file=sys.stderr)
        sys.exit(2)


VALID_FAILURE_TYPES = {"test", "install", "upgrade", "infra"}
VALID_ACTION_TYPES = {"revert", "experiment"}
VALID_STATUSES = {
    "open", "merged", "staged", "pending", "passed", "failed",
    "inconclusive", "skipped_conflict", "deferred",
}
VALID_PR_STATES = {"draft", "open", "merged", "closed"}

METADATA_FIELDS = {
    "payload_tag": str,
    "version": str,
    "stream": str,
    "architecture": str,
    "release_controller_url": str,
    "analyzed_at": str,
    "force_accept_recommended": bool,
}

JOB_FIELDS = {
    "job_name": str,
    "prow_url": str,
    "is_aggregated": bool,
    "underlying_job_name": str,
    "failure_type": str,
    "root_cause_summary": str,
    "streak_length": int,
    "originating_payload_tag": str,
    "failure_pattern": str,
}

CANDIDATE_FIELDS = {
    "pr_url": str,
    "pr_number": int,
    "component": str,
    "title": str,
    "confidence_score": int,
    "rationale": str,
    "failing_jobs": list,
    "actions": list,
}

ACTION_FIELDS = {
    "type": str,
    "status": str,
    "revert_pr_url": str,
    "revert_pr_state": str,
    "result_summary": str,
    "jira_key": str,
    "jira_url": str,
    "payload_jobs": list,
}

PAYLOAD_JOB_FIELDS = {
    "command": str,
    "test_url": str,
    "test_prow_url": str,
}


def validate(data: dict) -> list[str]:
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Root must be a YAML mapping"]

    for section in ("metadata", "failing_jobs", "candidates"):
        if section not in data:
            errors.append(f"Missing top-level key: {section}")

    if "metadata" in data:
        errors.extend(_check_fields(data["metadata"], METADATA_FIELDS,
                                    "metadata"))

    if "failing_jobs" in data:
        if not isinstance(data["failing_jobs"], list):
            errors.append("failing_jobs must be a list")
        else:
            for i, job in enumerate(data["failing_jobs"]):
                prefix = f"failing_jobs[{i}]"
                errors.extend(_check_fields(job, JOB_FIELDS, prefix))
                ft = job.get("failure_type", "")
                if ft and ft not in VALID_FAILURE_TYPES:
                    errors.append(
                        f"{prefix}.failure_type: invalid value "
                        f"'{ft}', expected one of {VALID_FAILURE_TYPES}"
                    )

    if "candidates" in data:
        if not isinstance(data["candidates"], list):
            errors.append("candidates must be a list")
        else:
            job_names = set()
            if isinstance(data.get("failing_jobs"), list):
                job_names = {
                    j.get("job_name", "") for j in data["failing_jobs"]
                }

            for i, cand in enumerate(data["candidates"]):
                prefix = f"candidates[{i}]"
                errors.extend(_check_fields(cand, CANDIDATE_FIELDS, prefix))

                score = cand.get("confidence_score", 0)
                if isinstance(score, int) and not (0 <= score <= 100):
                    errors.append(
                        f"{prefix}.confidence_score: {score} not in 0-100"
                    )

                for jn in cand.get("failing_jobs", []):
                    if job_names and jn not in job_names:
                        errors.append(
                            f"{prefix}.failing_jobs: '{jn}' not found "
                            f"in top-level failing_jobs"
                        )

                for j, action in enumerate(cand.get("actions", [])):
                    ap = f"{prefix}.actions[{j}]"
                    errors.extend(_check_fields(action, ACTION_FIELDS, ap))

                    at = action.get("type", "")
                    if at and at not in VALID_ACTION_TYPES:
                        errors.append(
                            f"{ap}.type: '{at}' not in {VALID_ACTION_TYPES}"
                        )
                    st = action.get("status", "")
                    if st and st not in VALID_STATUSES:
                        errors.append(
                            f"{ap}.status: '{st}' not in {VALID_STATUSES}"
                        )
                    ps = action.get("revert_pr_state", "")
                    if ps and ps not in VALID_PR_STATES:
                        errors.append(
                            f"{ap}.revert_pr_state: '{ps}' not in "
                            f"{VALID_PR_STATES}"
                        )

                    for k, pj in enumerate(action.get("payload_jobs", [])):
                        pp = f"{ap}.payload_jobs[{k}]"
                        errors.extend(
                            _check_fields(pj, PAYLOAD_JOB_FIELDS, pp)
                        )

    return errors


def _check_fields(obj: dict, schema: dict, prefix: str) -> list[str]:
    errors = []
    if not isinstance(obj, dict):
        return [f"{prefix}: expected a mapping, got {type(obj).__name__}"]
    for field, expected_type in schema.items():
        if field not in obj:
            errors.append(f"{prefix}: missing field '{field}'")
        elif not isinstance(obj[field], expected_type):
            errors.append(
                f"{prefix}.{field}: expected {expected_type.__name__}, "
                f"got {type(obj[field]).__name__}"
            )
    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <path-to-yaml>", file=sys.stderr)
        sys.exit(2)

    yaml = _require_yaml()
    path = sys.argv[1]

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: file not found: {path}", file=sys.stderr)
        sys.exit(2)
    except yaml.YAMLError as e:
        print(f"Error: invalid YAML: {e}", file=sys.stderr)
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
