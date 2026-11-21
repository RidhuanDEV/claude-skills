"""Check the self-contained SVG subset used by the illustration fixtures."""

import argparse
import json
import math
import re
from pathlib import Path
from xml.parsers import expat

SVG = "http://www.w3.org/2000/svg"
MAX_BYTES = 1_000_000
CONTAINERS = frozenset({"svg", "g"})
SHAPES = frozenset({"path", "rect", "circle", "ellipse", "line", "polyline", "polygon"})
METADATA = frozenset({"title", "desc"})
ELEMENTS = CONTAINERS | SHAPES | METADATA
ATTRIBUTES = frozenset({
    "id", "viewBox", "width", "height", "preserveAspectRatio",
    "x", "y", "x1", "y1", "x2", "y2", "cx", "cy", "r", "rx", "ry",
    "d", "points", "transform", "fill", "stroke", "stroke-width",
    "stroke-linecap", "stroke-linejoin", "fill-rule", "opacity",
    "fill-opacity", "stroke-opacity",
})
HEX = frozenset("0123456789abcdefABCDEF")
NUMBER = r"[-+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+)?"
SEPARATOR = r"(?:[ \t\r\n]*,[ \t\r\n]*|[ \t\r\n]+)"
VIEWBOX = re.compile(rf"[ \t\r\n]*({NUMBER}){SEPARATOR}({NUMBER}){SEPARATOR}({NUMBER}){SEPARATOR}({NUMBER})[ \t\r\n]*")


def _literal_paint(value: str) -> bool:
    return (value in {"none", "currentColor", "transparent"}
            or (value.startswith("#") and len(value) in {4, 5, 7, 9}
                and all(digit in HEX for digit in value[1:])))


def _viewbox(value: str) -> tuple[float, float, float, float]:
    match = VIEWBOX.fullmatch(value)
    if match is None:
        raise ValueError("viewBox must contain four SVG numbers")
    values = [float(item) for item in match.groups()]
    if not all(math.isfinite(item) for item in values):
        raise ValueError("viewBox must contain four finite numbers")
    x, y, width, height = values
    if width <= 0 or height <= 0:
        raise ValueError("viewBox width and height must be positive")
    return x, y, width, height


def _reject_markup(*_args: object) -> None:
    raise ValueError("XML processing instructions and DTDs are outside this profile")


def inspect(source: bytes) -> tuple[tuple[float, float, float, float], int]:
    if not source or len(source) > MAX_BYTES:
        raise ValueError("source must contain between 1 and 1,000,000 bytes")

    parser = expat.ParserCreate(namespace_separator=" ")
    parser.StartDoctypeDeclHandler = _reject_markup
    parser.ProcessingInstructionHandler = _reject_markup
    stack: list[str] = []
    ids: set[str] = set()
    viewbox: tuple[float, float, float, float] | None = None
    shape_count = 0

    def start(qualified_name: str, attrs: dict[str, str]) -> None:
        nonlocal viewbox, shape_count
        namespace, _, name = qualified_name.rpartition(" ")
        if namespace != SVG or name not in ELEMENTS:
            raise ValueError(f"element outside static SVG profile: {qualified_name}")
        if not stack:
            if name != "svg":
                raise ValueError("root must be an SVG element")
            viewbox = _viewbox(attrs.get("viewBox", ""))
        elif name == "svg" or stack[-1] not in CONTAINERS:
            raise ValueError(f"unsupported nesting: {stack[-1]} / {name}")
        for attr, value in attrs.items():
            if attr not in ATTRIBUTES:
                raise ValueError(f"attribute outside static SVG profile: {attr}")
            if attr in {"fill", "stroke"} and not _literal_paint(value):
                raise ValueError(f"{attr} must be a literal color in this profile")
        if "id" in attrs:
            identifier = attrs["id"]
            if not identifier or identifier in ids:
                raise ValueError("ids must be nonempty and unique")
            ids.add(identifier)
        if name in SHAPES:
            shape_count += 1
        stack.append(name)

    def end(_name: str) -> None:
        stack.pop()

    def characters(data: str) -> None:
        if data.strip() and (not stack or stack[-1] not in METADATA):
            raise ValueError("only title and desc can contain text")

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = characters
    parser.Parse(source, True)
    if viewbox is None or shape_count == 0:
        raise ValueError("static SVG requires a viewBox and at least one shape")
    return viewbox, shape_count


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("file", type=Path)
    cli.add_argument("--viewbox", nargs=4, type=float)
    args = cli.parse_args()
    try:
        with args.file.open("rb") as stream:
            source = stream.read(MAX_BYTES + 1)
        actual, count = inspect(source)
        if args.viewbox is not None and tuple(args.viewbox) != actual:
            raise ValueError(f"expected viewBox {args.viewbox}, found {actual}")
    except (OSError, ValueError, expat.ExpatError) as error:
        print(json.dumps({"status": "FAIL", "scope": "static SVG profile", "error": str(error)}))
        return 1
    print(json.dumps({
        "status": "PASS", "scope": "static SVG profile", "viewBox": actual, "shapes": count,
        "visual": "NOT_RUN", "runtime": "NOT_RUN",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
