# SVG authoring and rendering

Set a deliberate viewBox and preserve aspect ratio. Use a documented project subset. Separate editable source from runtime output if optimization changes naming or editability. Keep referenced IDs stable across optimization. Check visible bounds, internal definitions, transforms, clipping, fill rule, gradients and CSS against the exact renderer.

For untrusted input, use the application's established sanitizer or an approved isolated renderer. Reject unexpected scripts, event attributes, external references, network fonts and embedded resources before rendering. A static structure check is not a general sanitizer. Confirm expected asset dependencies separately when a project intentionally uses embedded rasters.

For self-contained fixtures using basic SVG geometry, run from the skill directory:

```text
python scripts/inspect_static_svg.py fixtures/onboarding-success.svg --viewbox 0 0 320 160
```

The optional checker accepts a conservative SVG element and attribute subset. It rejects constructs outside that subset from the fixture gate, including otherwise valid SVG features. Use the authorized project's validator for other SVG profiles. Its success covers element and attribute vocabulary, literal paint, nesting, unique IDs and a numeric viewBox. The checker does not parse path geometry, transforms or other numeric attributes.

Render spread at the expected app size and an enlarged review size with an installed renderer. Inspect the real output for line quality, clipping and visual drift. For deterministic rendering, compare pixels only under matched dimensions, renderer, color and alpha settings. Use a diff to locate a change and visual inspection to judge it. Record which renderer ran and which target runtime still needs verification.

See [primary SVG references](open-source-source-register.md) for the specification and renderer candidates.
