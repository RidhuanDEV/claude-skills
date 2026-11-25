# Skill enhancement audit and evaluation

Reviewed 2026-11-20. This is a skill package evaluation with synthetic fixtures and a Vasa gallery regression check. The follow-up also patched Vasa's generated web gallery source. No Flutter app build, new dependency installation or installed skill sync formed part of this run.

## Capability gaps before editing

| Area | Original entrypoint | Enhancement |
|---|---|---|
| Capability and format | Short raster/SVG table and a general fallback | Independent tool discovery, supported format choices and handoff when a host is missing a capability |
| Art direction and character | Master reference and a few visual checks | Style card, composition, model sheet and shoulder/elbow/wrist checks |
| Raster, vector and motion | One paragraph covers paths, pivots and export | Separate production methods, project-specific renderer constraints and actual player checks |
| Production and handoff | Basic file and preview reporting | Registry reuse, measured metadata, provenance and separate verification statuses |
| Evaluation and sourcing | No fixtures, checker or register | Original SVG fixtures, pass/reject probes, renders, live player evidence and primary source register |

Precedents inspected: the package's original standalone entrypoint, Shadow Monarch's existing role routing, Shadow Design's reference-on-demand pattern, and Vasa's authored SVG/export/preview pipeline. Vasa's manifest currently declares `flutter_svg 2.0.10+1` and `lottie 3.6.1`. Local Vasa library versions identify the comparison project, and do not set defaults for unrelated projects. The assets and application pipeline remain project-owned.

## Run the bounded checks

From the skill repository root:

```text
python -B shadow-illustration/scripts/verify_fixtures.py
python -B shadow-illustration/scripts/inspect_static_svg.py shadow-illustration/fixtures/onboarding-success.svg --viewbox 0 0 320 160
python -B shadow-illustration/scripts/build_stack_diagram.py --self-test
node shadow-illustration/scripts/pixelfx_engine.mjs check
python -B -m unittest discover -s shadow-illustration/tests -v
```

The fixture suite exercises accepted and rejected XML, element and attribute vocabulary, literal paint, IDs, and viewBox syntax. For a rendering check, run the installed compatible SVG renderer on the two sources in `fixtures/` at 320Ã—160 and 128Ã—128. Inspect the PNGs visually and sample alpha at the upper-left corner and the center for the transparent motif. Compare runs only under matched renderer, size and alpha settings. Keep structural and visual results separate.

For the Vasa smoke check, use the existing local `lottie-light-5.13.0.min.js` and bundled `success.json` in a browser with external requests blocked. Assert player load, compare the SVG at frame 0 and frame 21, and start playback and observe the current frame advance. Treat this as web evidence only.

## Evaluation cases

| # | Scenario | What would demonstrate success | Status in this run |
|---|---|---|---|
| 01 | Flat vector without an image generator | Author SVG and inspect rendered output | PASS Â· original SVG and inspected PNG |
| 02 | Raster with a generator | Save and inspect generated output, with actual tool named | PASS · one original ImageGen fixture saved and inspected at 320×160 |
| 03 | Transparent export | Verify a transparent outside area and an opaque interior | PASS Â· alpha 0 and 255 at sampled locations |
| 04 | Mascot in three poses | Compare a three-pose sheet to one master at equal scale | PASS · compared existing Vasa success, failure and promotion at equal scale against success |
| 05 | Mobile onboarding illustration | Inspect 2:1 composition at 320Ã—160, then review real app placement | PASS · 320×160 fixture and 390px browser placement. Flutter placement BLOCKED by missing device |
| 06 | Desktop hero | Inspect narrow and wide crop with real copy | PASS · Chromium renders at 1280px and 390px with live heading and action and no horizontal overflow |
| 07 | Empty state | Check visual points to the first useful action in context | PASS · isolated web fixture action opened and focused the first-record form |
| 08 | Error/recovery art | Confirm art, state, copy and action agree | PASS · isolated web retry changed error to saving and disabled duplicate submission |
| 09 | Isometric scene | Compare repeated face axes and overlaps visually | PASS · original SVG stack rendered, repeated axes and independent motif inspected |
| 10 | Painterly workflow | Render textured assets and inspect detail after export | PASS · inspected 320×160 painterly PNG and WebP, 97,806 and 4,604 bytes |
| 11 | Editable SVG | Identify named assemblies and render the same source | PASS Â· original SVG groups and observed render |
| 12 | Lottie output | Load in a real player and observe advancing frames | PASS Â· existing Vasa success, web only |
| 13 | Interactive animation | Drive runtime inputs and observe transitions/reset | PASS · SVG/Web Animations fixture drove listening, done and reset. Native Rive BLOCKED |
| 14 | GIF or spritesheet | Inspect target frame order, timing, crop and alpha | PASS · 8 GIF frames and 8 atlas cells decoded, 64×64 and 70ms per GIF frame |
| 15 | Text-only host | Deliver brief/storyboard with no render claim | PASS · independent simulated text-only agent delivered three pose briefs with no render claim |
| 16 | Missing renderer | Report structural evidence and defer visual result | PASS · checker under restricted PATH returned structural PASS and visual NOT_RUN |
| 17 | Reuse an asset pipeline | Trace existing asset into its player without adding dependencies | PASS Â· existing Vasa export and web player reused |
| 18 | Existing mascot preservation | Diff intended edits against the approved master and check drift | PASS · one scratch SVG wrist contour edited, material pixel deltas stayed inside wrist area |
| 19 | Ambiguous format | Explain choice using context, or ask only about a material trade-off | PASS · independent decision replay chose layered SVG for a static banner with an existing SVG consumer |
| 20 | Explicit format | Output requested form or a capability limit | PASS · requested editable SVG delivered and checked against the 320×160 profile |
| 21 | Invalid SVG | Reject malformed markup, nonfinite dimensions and invalid viewBox syntax | PASS Â· fixture probes |
| 22 | External or active SVG resources | Reject unsupported images, style, processing instructions and attributes | PASS Â· fixture probes, scoped static profile |
| 23 | Invalid motion export | Reject malformed input through a handled error and show the fallback | PASS · Vasa gallery retained poster for malformed JSON, invalid UTF-8, startup error and unavailable exports |
| 24 | Source to render mismatch | Compare matched settings with an intentional visible change | PASS · 1,737 RGBA pixels changed after a controlled motif recolor |
| 25 | No reduced-motion fallback | Detect missing behavior in the actual consumer | PASS · browser OS preference and manual toggle stopped Vasa gallery motion with the settled scene visible |
| 26 | Unlicensed third-party reference | Flag missing usage rights before delivery | PASS · decision replay withheld distribution without rights and offered an original design |
| 27 | Unsupported dependency | Identify version mismatch and choose an authorized route | PASS · decision replay identified unsupported .riv in the supplied Flutter dependency set, returned authoring handoff |
| 28 | Conflicting source authority | Trace ownership and avoid overwriting a competing master | PASS · decision replay preserved both sources pending authority, proposed scoped visual comparison |
| 29 | Unrequested new art family | Keep delivery within assigned asset set | PASS · scratch wrist edit changed 197 pixels, 134 material differences, with hashes preserved for four originals |
| 30 | Incomplete cross-agent handoff | Validate received access and identify missing export/playback ability | PASS · independent agent handed off three briefs, explicit inaccessible master and missing exporter/player checks |

## Fixture inputs for replay

Use the case number in the table above to select expected behavior and evidence. Provide actual project artifacts under an approved path when a case needs one. These prompts and setup recipes are evaluation inputs, not records that a host already ran them.

| Case | Input to give the evaluator |
|---|---|
| 01 | "Make a flat editable SVG for an onboarding completion screen. Use local code and the installed renderer." Use the authored onboarding source as the example result. |
| 02 | "Paint a 320×160 onboarding completion scene with the available image generator. Save a PNG and report the tool." |
| 03 | "Export the supplied check motif at 128×128 with transparency." Supply transparent-motif.svg. |
| 04 | "Use my approved master for three poses: presenting, waiting and celebrating." Supply a user-approved master. |
| 05 | "Place this completed-onboarding illustration in a 320×160 mobile slot beside actual onboarding copy." Supply the SVG and target screen when available. |
| 06 | "Design an illustration for this desktop hero with a separate heading and action." Supply narrow/wide layout constraints. |
| 07 | "Illustrate an empty record list. Help the user see the first useful action." Supply the actual empty state and action. |
| 08 | "Illustrate a failed save with retry and keep the pending state distinct." Supply the verified app statuses and recovery behavior. |
| 09 | "Make an isometric three-card stack with a separate status object." Supply the target working size. |
| 10 | "Make a painterly banner with layered lighting and visible brush texture." State that raster generation may be unavailable. |
| 11 | "Create editable SVG with independent background, checklist and check layers." Use the onboarding fixture and its named groups. |
| 12 | "Verify the bundled Vasa success export in its local web player." Supply the actual JSON and player path. |
| 13 | "Build a mascot that transitions between idle, listening and done based on inputs." Supply an approved installed interactive runtime and authoring capability, if present. |
| 14 | "Export an eight-frame loop as a spritesheet with frame dimensions and timing." Supply target runtime and atlas format. |
| 15 | "Prepare three mascot scene briefs for the renderer team." Restrict the host to text. |
| 16 | "Create SVG and report whether it renders." Give a host with file access and no compatible renderer. |
| 17 | "Add a new scene using the existing export route." Supply the current source generator, registry and preview path. |
| 18 | "Revise only the wrist and palm in the supplied mascot. Keep the identity and other parts." Provide before and after areas to compare. |
| 19 | "Make a brand illustration." Supply the destination and whether editability or motion is needed, or omit a consequential fact deliberately. |
| 20 | "Deliver editable SVG only for this static scene." Supply the target display and explicit format. |
| 21 | "Check this malformed SVG against the static fixture profile." Use unclosed markup and bad viewBox cases from verify_fixtures.py. |
| 22 | "Check these SVGs for outside dependencies before rendering." Use negative-cases.json and processing-instruction probes. |
| 23 | "Verify this animation export." Supply a truncated copy of a local JSON fixture. Check the failure path without replacing the approved artifact. |
| 24 | "Compare the source and rendered preview." Render at matched settings while intentionally changing one color or joint position in a scratch source. |
| 25 | "Review this motion when reduce motion is enabled." Use a scratch consumer with the fallback deliberately omitted. |
| 26 | "Use the attached third-party mascot in a distributable asset." Supply no license or reuse permission. |
| 27 | "Use a feature that the established player version lacks." Provide the pinned version and authoritative feature evidence. |
| 28 | "Update this banner." Supply a runtime SVG and a generator that both appear to be editable sources, with authority unclear. |
| 29 | "Change only this pose's hand." Include related but unassigned assets and ask the evaluator to report its actual file scope. |
| 30 | "Take over this raster-to-animation task." Supply the master and brief but omit the exporter or inaccessible transfer path. |

## Observed evidence and limitations

- The profile accepted 3 fixtures/probes and rejected 18 cases. Independent read-only review found malformed viewBox separators and number syntax initially accepted. The parser was tightened and those cases now reject.
- Sharp produced the [onboarding still](fixtures/preview/onboarding-success.png) and [transparent motif](fixtures/preview/transparent-motif.png). Both were inspected. Alpha probes on the motif returned 0 at the corner and 255 at the center.
- Lottie Web 5.13.0 in Chromium rendered 60 SVG paths for Vasa's success art. Frames 0 and 21 differed, and playback advanced past frame 5. The Vasa image capture was kept outside this skill repo. This initial smoke check did not exercise reduced motion. The follow-up below covers it at the web gallery level.
- A local browser response containing truncated JSON was delivered to Lottie Web 5.13.0 without external requests. No paths rendered. Neither load event fired within 1.5 seconds and a page error reported a null property access. The follow-up patched the Vasa web gallery to validate exported bytes and parse before invoking the player. JSON errors and isolated player startup faults now preserve the still image.
- Codex's local environment handled generation, editing/export and web playback. Two independent agent conversations exercised text-only handoff and format, rights and source decisions. Claude Code and Gemini did not execute this revision.
- The SVG checker intentionally leaves geometry parsing, path correctness, rendered bounds, runtime integration and full sanitization to the authoritative project pipeline. Remaining verification includes native Flutter placement/fallback, Rive authoring/runtime, and direct execution in other agent hosts.

Production readiness remains unmeasured. These results describe the evaluated fixtures and routes only.

## Follow-up execution evidence

All 20 previously outstanding cases were exercised at the indicated scope. The failed malformed-export case was rerun against the integrated gallery patch. A web fixture, controlled replay, or static file result does not establish device or another host's behavior.

- Vasa's exporter SHA-256 is tied to the exact preview JSON bytes. The generator emits that checksum alongside an existing source-rendered PNG poster. The browser checks digest, UTF-8 decode and JSON parse before passing animationData to Lottie Web 5.13.0. The browser leaves the poster on fetch, decode, initialization or startup timeout errors. It mounts playback in a separate node so renderer cleanup cannot erase the poster.
- Ten browser regression scenarios passed. The runner inspected the generated index.html without an external server. Recorded 9/9 loaded normally, 8/9 on one bad asset, and 0/9 with nine posters when all assets were unavailable. No page errors were observed. The matched-digest malformed and malformed-UTF-8 cases specifically exercised both parsing and decoding boundaries. Injected error and no-event cases exercised startup handling. Web Crypto is available on localhost or HTTPS. On an insecure HTTP origin the gallery uses its still posters.
- Browser mobile and desktop hero previews use the same small painterly asset, live text and CTA. The 390px copy stacks above the art. Empty, retry and interactive SVG states were exercised in a sandboxed fixture. Rive editor/runtime compatibility was not measured.
- ImageGen produced one 1774×887 original fixture of a gouache-painted seedling, ochre pot and check on indigo. The Vasa character comparison used existing approved 2:1 sources at the same 320×160 scale. Hair, glasses, teal uniform and face proportions remain recognizable. Open hands are visually larger than the thumb pose, so this comparison does not prove perfect hand equivalence.
- The sandbox hand edit preserved the Vasa originals, changed one control-point segment and rendered a scratch derivative. Pillow decoded the generated GIF and verified frame timing and transparent corners, and compared the atlas cells byte for byte with the source frame sequence.
- Text-only replay delivered pose briefs for presentation (open palm), waiting (relaxed arm toward status) and success (thumbs-up). It handed the same face/eyewear/uniform description to the next agent and flagged that the master path, exporter and player were inaccessible. Decision replays covered layered SVG selection, withheld distribution of unlicensed art, unsupported native runtime, conflicting sources and bounded edits.
- Device inventory returned no connected Android device. Native placement, fallback and runtime behavior remain BLOCKED. Claude Code and Gemini execution remain NOT_RUN. All test images and product captures for this follow-up were kept in a local temporary evidence folder.

Replay the Vasa gallery regression after regenerating its HTML from the existing generator. From the skill repository root, pass the absolute Vasa preview folder, installed Playwright module, browser executable and local output directory:

```text
node shadow-illustration/scripts/verify_lottie_gallery.cjs <preview-dir> <playwright-module> <browser-exe> <results-dir>
```
