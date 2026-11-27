"""Read-only next action for an ambiguous provider mutation; no provider calls."""
import argparse
import json
from pathlib import Path


RECEIPT_TEXT_FIELDS = ("account", "currency", "provider_tx_id")


def _matches_receipt(record: dict, inquiry: dict) -> bool:
    return (
        all(
            isinstance(record.get(field), str)
            and bool(record[field].strip())
            and record[field] == inquiry.get(field)
            for field in RECEIPT_TEXT_FIELDS
        )
        and type(record.get("amount_minor")) is int
        and type(inquiry.get("amount_minor")) is int
        and record["amount_minor"] == inquiry["amount_minor"]
    )


def decide(record: object) -> str:
    if not isinstance(record, dict):
        raise ValueError("Expected an object")
    operation = record.get("operation_id")
    if not isinstance(operation, str) or not operation.strip():
        raise ValueError("Missing local operation ID")
    if record.get("state") in ("CONFIRMED", "FAILED"):
        return "PRESERVE_TERMINAL_STATE"
    if record.get("state") != "UNKNOWN":
        raise ValueError("Expected UNKNOWN or a terminal state")
    inquiry = record.get("inquiry")
    if "inquiry" in record:
        if not isinstance(inquiry, dict) or inquiry.get("operation_id") != operation or inquiry.get("verified") is not True:
            return "MANUAL_RECONCILIATION"
        if inquiry.get("state") in ("CONFIRMED", "FAILED"):
            if not _matches_receipt(record, inquiry):
                return "MANUAL_RECONCILIATION"
            return "RECORD_" + inquiry["state"]
        return "KEEP_PENDING"
    inquiry_supported = record.get("inquiry_supported", False)
    if not isinstance(inquiry_supported, bool):
        return "MANUAL_RECONCILIATION"
    if inquiry_supported:
        return "QUERY_STATUS"
    guarantee = record.get("deduplication")
    if isinstance(guarantee, dict) and all(guarantee.get(k) is True for k in (
        "provider_guarantee_verified", "same_account", "same_key", "same_payload",
        "same_operation", "inside_window", "retry_budget_available",
    )):
        return "ELIGIBLE_FOR_SAME_KEY_REPLAY"
    return "MANUAL_RECONCILIATION"


def self_test() -> dict[str, int]:
    base = {"operation_id": "txn-1", "state": "UNKNOWN"}
    details = {"account": "merchant-1", "currency": "IDR", "provider_tx_id": "tx-1", "amount_minor": 1000}
    receipt = dict(details, verified=True, operation_id="txn-1", state="CONFIRMED")
    guarantee = dict.fromkeys(("provider_guarantee_verified", "same_account", "same_key",
                               "same_payload", "same_operation", "inside_window", "retry_budget_available"), True)
    cases = [
        (base, "MANUAL_RECONCILIATION"),
        (dict(base, inquiry_supported=True), "QUERY_STATUS"),
        (dict(base, **details, inquiry=receipt), "RECORD_CONFIRMED"),
        (dict(base, **details, inquiry=dict(receipt, state="FAILED")), "RECORD_FAILED"),
        (dict(base, inquiry=receipt), "MANUAL_RECONCILIATION"),
        (dict(base, inquiry=None, inquiry_supported=True), "MANUAL_RECONCILIATION"),
        (dict(base, inquiry=dict(receipt, state="PENDING")), "KEEP_PENDING"),
        (dict(base, inquiry=dict(receipt, operation_id="other")), "MANUAL_RECONCILIATION"),
        (dict(base, state="CONFIRMED", inquiry=dict(receipt, state="FAILED")), "PRESERVE_TERMINAL_STATE"),
        (dict(base, deduplication=guarantee), "ELIGIBLE_FOR_SAME_KEY_REPLAY"),
    ]
    cases.extend((dict(base, deduplication=dict(guarantee, **{key: False})), "MANUAL_RECONCILIATION")
                 for key in guarantee)
    for field, mismatch in (
        ("account", "other-account"), ("currency", "USD"),
        ("provider_tx_id", "other-tx"), ("amount_minor", 1001),
        ("amount_minor", 1000.0), ("amount_minor", True),
    ):
        cases.append((dict(base, **details, inquiry=dict(receipt, **{field: mismatch})), "MANUAL_RECONCILIATION"))
    for field in details:
        incomplete = {key: value for key, value in receipt.items() if key != field}
        cases.append((dict(base, **details, inquiry=incomplete), "MANUAL_RECONCILIATION"))
    for record, expected in cases:
        if decide(record) != expected:
            raise AssertionError(expected)
    return {"passed": len(cases)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--assess", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(self_test() if args.self_test else {
            "next_action": decide(json.loads(args.assess.read_text(encoding="utf-8-sig")))
        }))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
