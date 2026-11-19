"""Check one local delivery artifact against its contracted digest and receipt."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def assess(artifact, receipt):
    if not isinstance(receipt, dict):
        raise ValueError("Expected receipt object")
    pending = []
    for key in ("release", "contract_ref", "sender", "recipient", "criteria", "warranty_owner"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            pending.append(key)
    expected = receipt.get("contract_sha256")
    if not isinstance(expected, str) or not re.fullmatch("[0-9a-fA-F]{64}", expected):
        pending.append("contract_sha256")
    else:
        with artifact.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != expected.lower():
            pending.append("digest_mismatch")
    for key in ("signed_receipt_ref", "operator_demo_ref", "access_receipt_ref"):
        if not isinstance(receipt.get(key), str) or not receipt[key].strip():
            pending.append(key)
    return {"status": "PENDING" if pending else "READY_FOR_RECEIPT_REVIEW", "pending": pending}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("receipt", type=Path)
    args = parser.parse_args()
    try:
        result = assess(args.artifact, json.loads(args.receipt.read_text(encoding="utf-8-sig")))
        print(json.dumps(result))
        raise SystemExit(int(bool(result["pending"])))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
