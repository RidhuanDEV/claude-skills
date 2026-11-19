"""Inspect an authorized local workshop snapshot. Never open, create or publish a room."""
import argparse
import json
from pathlib import Path


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be nonempty text")
    return value


def plan_poll(snapshot):
    """A lost create response is reconciled by request ID before any further action."""
    request_id = text(snapshot["request_id"], "request_id")
    attempted = snapshot["create_attempted"]
    if type(attempted) is not bool or not isinstance(snapshot["observed_polls"], list):
        raise ValueError("Expected a create_attempted boolean and observed_polls array")
    matching = {}
    for poll in snapshot["observed_polls"]:
        if not isinstance(poll, dict):
            raise ValueError("Expected a poll record")
        if text(poll["request_id"], "observed request_id") == request_id:
            poll_id = text(poll["poll_id"], "poll_id")
            state = poll["state"]
            if state not in ("draft", "open", "closed"):
                raise ValueError("Unrecognized poll state")
            if poll_id in matching and matching[poll_id] != state:
                return {"status": "HOLD", "reason": "Conflicting poll state; refresh the observation"}
            matching[poll_id] = state
    if len(matching) > 1:
        return {"status": "HOLD", "reason": "Multiple resources matched the request"}
    if matching:
        poll_id, state = next(iter(matching.items()))
        return {"status": "RECONCILED", "poll_id": poll_id, "state": state}
    if attempted:
        return {"status": "HOLD", "reason": "Create outcome unconfirmed; reconcile with workshop owner"}
    return {"status": "DRAFT", "reason": "No previous creation reported"}


def qa_draft(snapshot):
    """Only reviewer-approved public question and answer fields may enter the draft."""
    pages = snapshot["pages"]
    if not isinstance(pages, list) or not pages:
        raise ValueError("At least one observed page required")
    expected_cursor = None
    seen_cursors = set()
    questions = {}
    withheld = set()
    for page in pages:
        cursor = page["cursor"]
        if cursor != expected_cursor or cursor in seen_cursors:
            raise ValueError("Cursor chain is discontinuous or repeated")
        seen_cursors.add(cursor)
        expected_cursor = page["next_cursor"]
        if expected_cursor is not None:
            text(expected_cursor, "next_cursor")
        if not isinstance(page["questions"], list):
            raise ValueError("Expected a questions array")
        for item in page["questions"]:
            key = text(item["id"], "question ID")
            if type(item.get("approved_for_draft")) is not bool:
                raise ValueError("Question requires an explicit disclosure decision")
            if not item["approved_for_draft"]:
                withheld.add(key)
                questions.pop(key, None)
                continue
            if key in withheld:
                continue
            draft = {"id": key, "question": text(item["public_question"], "public question")}
            if item.get("public_answer"):
                draft["answer"] = text(item["public_answer"], "public answer")
            else:
                draft["owner"] = text(item["owner"], "follow-up owner")
                draft["due"] = text(item["due"], "follow-up date")
            if key in questions and draft != questions[key]:
                raise ValueError("Conflicting versions of a public question; reconcile before disclosure")
            questions[key] = draft
    if expected_cursor is not None:
        return {"status": "INCOMPLETE", "reason": "More pages required"}
    return {"status": "DRAFT", "questions": list(questions.values()), "withheld": len(withheld)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("method", choices=("live-polls", "live-qa"))
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.snapshot.read_text(encoding="utf-8-sig"))
        result = plan_poll(snapshot) if args.method == "live-polls" else qa_draft(snapshot)
    except (ValueError, KeyError, OSError, TypeError, AttributeError):
        result = {"status": "HOLD", "reason": "Snapshot unreadable or incompatible with workshop schema"}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("DRAFT", "RECONCILED") else 2


if __name__ == "__main__":
    raise SystemExit(main())
