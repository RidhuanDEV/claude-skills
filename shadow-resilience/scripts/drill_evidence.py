"""Assess one isolated restore drill from recorded evidence. Performs no network I/O."""
import argparse
import json
from datetime import datetime
from pathlib import Path


def timestamp(record, key):
    value = record.get(key)
    if not isinstance(value, str):
        raise ValueError(key)
    parsed = datetime.fromisoformat(value)
    if parsed.utcoffset() is None:
        raise ValueError(key)
    return parsed


def assess(record):
    result = {"rto_seconds": None, "rpo_upper_bound_seconds": None, "issues": []}
    try:
        disruption = timestamp(record, "disruption_at")
    except ValueError:
        result["issues"].append("Missing or invalid disruption timestamp")
        return result
    try:
        restored = timestamp(record, "business_verified_at")
        elapsed = (restored - disruption).total_seconds()
        if elapsed < 0 or not all(record.get(k) is True for k in (
            "consumer_workflow_passed", "required_dependencies_verified"
        )):
            raise ValueError
        result["rto_seconds"] = elapsed
    except ValueError:
        result["issues"].append("Business recovery unverified")
    try:
        # Only a durable contiguous checkpoint in the original timeline bounds loss.
        checkpoint = timestamp(record, "recovered_checkpoint_at")
        age = (disruption - checkpoint).total_seconds()
        if age < 0 or record.get("checkpoint_verified_in_source_timeline") is not True:
            raise ValueError
        result["rpo_upper_bound_seconds"] = age
    except ValueError:
        result["issues"].append("Recovery point unverified")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8-sig"))
        if not isinstance(record, dict):
            raise ValueError("Expected one drill object")
        result = assess(record)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Invalid drill record: {exc}\n")
    print(json.dumps(result, indent=2))
    raise SystemExit(1 if result["issues"] else 0)
