"""Preview a greenfield capability profile against a real target; never run a generator."""
import argparse
import json
from pathlib import Path
import sys


PROFILES = {
    "cli": ("command entry point", "exit-code and stdout smoke test"),
    "static": ("static entry page", "build and open a generated page"),
    "worker": ("job handler", "process one fixture and retry safely"),
    "http": ("request handler", "exercise one documented request"),
    "library": ("public export", "import and call from a clean consumer"),
}
CAPABILITIES = {
    "database": "migration and disposable local database verification",
    "http_contract": "trace the API source and validate its selected contract format",
    "queue": "delivery acknowledgment, retry and duplicate handling",
    "cache": "key isolation, invalidation and origin fallback",
    "container": "build and run the selected runtime image",
    "ci": "replay the local checks in the selected pipeline",
    "configuration": "validate required runtime settings and redact their values",
    "telemetry": "verify the chosen signals with synthetic data",
}


def preview(target: Path, profile: str, capabilities: list[str]) -> dict:
    if profile not in PROFILES:
        raise ValueError("Choose the product profile before scaffolding.")
    unknown = set(capabilities) - CAPABILITIES.keys()
    if unknown:
        raise ValueError("Unknown capabilities: " + ", ".join(sorted(unknown)))
    if target.is_symlink() or getattr(target, "is_junction", lambda: False)():
        raise ValueError("Select a concrete destination; a linked target requires inspection.")
    if target.exists() and not target.is_dir():
        raise ValueError("Destination is not a directory.")
    existing = sorted(entry.name for entry in target.iterdir()) if target.exists() else []
    planned = [*PROFILES[profile], *(CAPABILITIES[k] for k in dict.fromkeys(capabilities))]
    return {"status": "REVIEW_EXISTING" if existing else "PREVIEW",
            "target": str(target.resolve()), "profile": profile, "existing_entries": existing,
            "deliverables": planned if not existing else [], "selected_capabilities": list(dict.fromkeys(capabilities))}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=Path)
    parser.add_argument("--profile", choices=PROFILES, required=True)
    parser.add_argument("--capability", choices=CAPABILITIES, action="append", default=[])
    args = parser.parse_args()
    try:
        result = preview(args.target, args.profile, args.capability)
    except (OSError, ValueError) as exc:
        result = {"status": "BLOCKED", "reason": str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PREVIEW" else 1


if __name__ == "__main__":
    sys.exit(main())
