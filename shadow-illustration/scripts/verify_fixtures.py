"""Exercise the narrow static SVG profile with local fixtures and probes."""

import json
from pathlib import Path
from xml.parsers.expat import ExpatError

from inspect_static_svg import inspect

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures"


def svg(body: str, viewbox: str = "0 0 320 160") -> str:
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">{body}</svg>'


def main() -> None:
    positives = {
        "onboarding": ((FIXTURES / "onboarding-success.svg").read_bytes(), (0, 0, 320, 160), 6),
        "transparent source": ((FIXTURES / "transparent-motif.svg").read_bytes(), (0, 0, 128, 128), 2),
        "numeric syntax": (svg('<circle r="2" fill="#abc8"/>', "-1,+2,.32e3,160.").encode(), (-1, 2, 320, 160), 1),
    }
    for name, (source, expected, count) in positives.items():
        result = inspect(source)
        if result != (expected, count):
            raise AssertionError(f"{name}: unexpected result {result}")
        print(f"PASS accept {name}: {result}")

    serialized: object = json.loads((FIXTURES / "negative-cases.json").read_text(encoding="utf-8"))
    if not isinstance(serialized, list):
        raise ValueError("negative-cases.json must contain a list")
    negatives: dict[str, str] = {}
    for case in serialized:
        if not isinstance(case, list) or len(case) != 2 or not all(isinstance(item, str) for item in case):
            raise ValueError("each negative case needs a name and XML fragment")
        name, fragment = case
        negatives[name] = svg(fragment)
    shape = '<circle r="2"/>'
    negatives.update({
        "numeric underscore": svg(shape, "0 0 3_20 160"),
        "duplicate comma": svg(shape, "0,,0,320,160"),
        "trailing comma": svg(shape, "0,0,320,160,"),
        "infinite dimension": svg(shape, "0 0 1e999 160"),
        "zero dimension": svg(shape, "0 0 0 160"),
        "empty shape set": svg("<title>Empty</title>"),
        "wrong namespace": svg(shape).replace("http://www.w3.org/2000/svg", "urn:sample"),
        "processing instruction": '<?xml-stylesheet href="https://example.invalid/theme.css"?>' + svg(shape),
        "doctype": "<!DOCTYPE svg>" + svg(shape),
    })
    for name, source_text in negatives.items():
        try:
            inspect(source_text.encode())
        except (ValueError, ExpatError) as error:
            print(f"PASS reject {name}: {error}")
        else:
            raise AssertionError(f"{name}: unexpectedly accepted")


if __name__ == "__main__":
    main()
