# MOBILE-DESIGN — Consumer UI, illustration and motion

Navigation: [1](#1-establish-scope-from-the-app) · [2](#2-assign-a-visual-role-and-format) · [3](#3-art-direction-and-consistency) · [4](#4-human-anatomy-and-gesture-construction) · [5](#5-separate-emotion-from-context-when-useful) · [6](#6-vector-first-production-workflow) · [7](#7-lottie-authoring-and-motion) · [8](#8-runtime-integration-and-state-truth) · [9](#9-menu-and-section-design) · [10](#10-accessibility-theme-and-performance-review) · [11](#11-sourcing-and-illustrator-handoff) · [12](#12-completion-and-reporting-gates) · [13](#13-reproducible-asset-production-reference-to-app)

Use for mobile art direction, illustrated menus, characters, status scenes and their runtime integration. Read with `DESIGN.md` and the relevant stack guide. Keep product data, task clarity and accessibility ahead of decoration. This reference guides decisions; the user's current scope and execution limits take precedence.

Contents: scope/source audit (§1), visual roles/formats (§2), art direction (§3), anatomy (§4), character/context composition (§5), asset workflow (§6), Lottie (§7), runtime (§8), menus/sections (§9), accessibility/performance (§10), sourcing (§11), delivery gates (§12).

## 1. Establish scope from the app

- Inspect current screens, routes, enum/registry, assets, renderer versions, status/error contracts and component consumers before designing replacements.
- Record what exists, what is proposed and what is explicitly out of scope. Do not invent services, account identities, notifications, campaign offers or data to populate a visual pattern.
- Distinguish a plan request from implementation. For a plan, write phases, source impact and observable acceptance criteria; do not mark future work complete.
- Preserve business outcomes, filters, dates, record identities, permissions and recovery behavior. UI motion must never decide whether an operation succeeded.
- When replacing artwork, keep approved identity/proportions and fix the identified defect. Do not redesign all branding because one hand is wrong.
- Determine the review checkpoint from the user and existing workflow. Work already authorized can proceed; ask only for missing consequential direction. Show concrete sample output before soliciting a design decision.

## 2. Assign a visual role and format

| Role | Suitable format | Decision criteria |
|---|---|---|
| Service/menu illustration | Native SVG; transparent PNG when appropriate | Distinct object composition, readable silhouette, shared optical size and palette; not an enlarged generic icon |
| Character/static editorial scene | Layered SVG or designed bitmap | Native vector when editable limbs and future motion matter; PNG can be reference or final static art if that meets the task |
| Character/status animation | Lottie from intentionally layered art; Rive for justified interactive rigs | Choose the renderer already used where possible; validate exported features on the installed target renderer |
| Detailed static campaign/banner | PNG/WebP or SVG | Choose based on visual fidelity, scaling, alpha, decoded memory and actual platform support |
| Small controls/navigation | Consistent platform/product icon set | Back, close, calendar, filter, edit/delete and bottom navigation remain familiar controls |

A single PNG can fade, translate or scale as a whole; independent hands need separately authored layers or another rig. Lottie can also contain raster assets, so a JSON extension alone does not prove vector quality or a small bundle.

Prefer native vector authoring for flat editable art. Do not use automatic PNG-to-SVG tracing as the main final human-character workflow: it often preserves raster defects, explodes path counts and damages faces/hands. Rendered PNGs remain useful for review. Do not infer an app's asset format from its screenshot.

Bundle UI artwork locally for offline availability; remote marketing assets require an explicit product/cache/fallback policy. Record dimensions and transparent padding. For raster artwork, export density variants where the platform expects them, inspect alpha fringes and set an appropriate decode size.

## 3. Art direction and consistency

Define a compact style sheet before mass production:

- Character identity, audience, emotional range, head/body ratio, shoulder span, hair/glasses/clothing shapes and silhouette references.
- Product palette with semantic accents; flat fills and restrained shading are a useful default, not a ban on every other visual style.
- Outline weight relative to canvas and display size; distinguish outer contour from sparse internal details. Use coherent joins/caps and avoid duplicate outlines along shared boundaries.
- Consistent light direction if shading is used. Shadows stay within their intended forms. Remove details that become noise at mobile size.
- Scene canvas, safe crop, focal point, optical size, spacing and background treatment. Match light/dark intentionally rather than invert colors blindly.
- References explain a visual principle, not permission to copy a brand's artwork. Preserve the product's own identity.

Stylization may enlarge the head or simplify features. Choose proportions that fit the approved cartoon language rather than prescribing anatomical ratios universally. Expressive brows, head tilt, smile and posture are welcome when they fit the scene; “natural” does not require an emotionally neutral face.

## 4. Human anatomy and gesture construction

Build the figure before decorations: line of action → torso orientation/weight → shoulder line → upper arm → elbow → forearm → wrist → palm → digits. Clothes follow the underlying forms. The silhouette should communicate the pose without internal detail.

### Hands

- A human hand has one thumb and four fingers. Show all five clearly in an open-palm study; use varied lengths, joint directions and a plausible thumb origin. Avoid a comb of equal tubes.
- Not every digit must be visible in every pose. Folded/occluded digits must be explained by knuckles, overlap, perspective or the object. Do not use “hidden fingers” to excuse disconnected blobs.
- Use the approved representative pose as a hand-volume benchmark across the family. Compare palm-body width/depth and wrist thickness at the same character scale; do not compare the overall bounding box of an open hand to a folded fist. Extended fingers legitimately increase the silhouette, but the palm must not become a shallow sliver. Keep one shared reviewed hand construction for corresponding gestures and reflect it deliberately for the opposite side.
- Treat wrist and palm as continuous volumes. Do not substitute a palm circle plus arbitrary finger strokes for the construction of a visible editorial hand.
- Keep arm/hand layer boundaries invisible in the final contour. A wrist crease is a short form-following detail, not a thick line closing the whole wrist.
- For grips, establish object plane, palm behind/in front, thumb opposition and finger wrap before drawing details. No floating fingertips in the middle of paper, no object slicing a wrist, no impossible hand span.
- If a grip adds no meaning, simplify the pose or separate the object from the person. Do not force props into every scene.

### Gesture and expression

- Use real human pose reference or a deliberately reviewed construction study. Record what was actually consulted; do not claim photographic reference without inspecting it.
- Vary body orientation, head direction, shoulder height and weight distribution together. Moving hands while freezing the torso is insufficient for a full expressive set.
- Check forearm taper, elbow location, wrist bend, cuff overlap and arm length at the extreme pose, not only at rest.
- Choose one dominant emotion. Success can be relieved or joyful; failure should be empathetic; retry encouraging. Distinguish uncertainty from confirmed failure.
- Verify gaze and face direction; keep glasses, eyes and hair anchored to the same head construction across expressions.

Code-authored human art is a prototype until its visual result passes review. Valid paths and successful rendering do not establish professional illustration quality. If repeated local fixes fail, return to the silhouette/construction or use an illustrator/designer source while preserving the integration contract. Do not repeatedly auto-trace or patch more detail onto a broken figure.

## 5. Separate emotion from context when useful

For reusable promotional/status characters, a useful composition is:

```
scene
  background
  character
    body
    head / face / hair
    left-arm-assembly
    right-arm-assembly
  context-art
  purposeful-accents
```

The character conveys emotion; a sibling context layer conveys analytics, notes, a service, a clock or a result. This separation is a product choice, not a requirement for every illustration. If the user chooses it, do not reintroduce handheld props later.

- Analytics: a separate mini chart/panel. Decorative data must not resemble an actual account result; meaningful charts use real data and accessible labels.
- Recording: a note/pencil card separate from the person. Do not fabricate completed records.
- Success: gesture first, check/short accent second. Failure: calm reaction and clear text, no alarming full-screen treatment by default.
- Promotion: welcoming/presenting pose with a real feature or approved campaign. Do not invent discounts, rewards or promotions solely for visual interest.
- Keep contextual motifs consistent with the approved status treatment. For borderless art, remove generic white cards, navy frames and checkbox-like wrappers; draw note lines/pencil, retry arrow, hourglass or pause as standalone vectors. A solid success/error medallion can be the semantic symbol itself, without an outer border. Use green for confirmed success, red for confirmed failure, amber for uncertainty/waiting, teal for information/retry/recording, and a restrained neutral for unavailable service. Do not recolor the character uniform to indicate status.
- Decorations earn their space: motion lines indicate movement; accents direct attention. Avoid random sparkles and endless confetti.
- Keep message, business values, CTA and localized text in native UI rather than baking them into artwork.

## 6. Vector-first production workflow

1. Audit current art and identify concrete defects. Preserve the approved baseline/reference separately.
2. Create a master character and construction studies, including an open hand and any necessary grip. Render these before producing many poses.
3. Produce a small representative set: normally success, failure and a promotional/neutral pose; plus several menu objects if menus are in scope. Adapt sample count to the user's requested checkpoint.
4. Review silhouette and anatomy first, then expression, color, detail and context. Compare poses side by side at intended mobile size and enlarged.
5. Author deliberate native vector curves. Use enough Bezier points to control the form, without excessive paths. Avoid tiny features that cannot survive small rendering.
6. Keep stable layer names, documented pivots and explicit draw order. Separate static rest transforms from animated transforms, or mathematically compose them with tested semantics; never accidentally overwrite one with the other.
7. Preserve editable source independently of generated outputs. A generation script must not silently overwrite manual approved artwork. Version sources, exports and review renders together.
8. Render SVG to PNG and compare to the approved source/reference. Inspect hands, shoulders, face, stroke joins, overlaps, crop and alpha at rest and planned motion extremes.
9. Only then rig/export animation. Check optimization has not altered contour, fill rule, transform, IDs or draw order needed by the rig.

For a custom exporter, document its supported path commands/styles/transforms and reject unsupported input. Do not silently discard masks, gradients, strokes or groups. Mathematical conversion of native Bezier curves is different from tracing a bitmap.

## 7. Lottie authoring and motion

### Renderer contract

- Read installed dependencies/APIs first. Verify uncertain feature support using target renderer documentation or a focused compatibility prototype; do not assume browser and mobile players are equivalent.
- Prefer shape layers for flat art. Expressions, fonts, effects, masks, mattes, gradients and raster dependencies need explicit compatibility checks when used. Avoid remote dependencies in bundled status scenes.
- Use a maintained design export workflow or a constrained exporter whose output is verified. Do not hand-invent schema fields to make the JSON appear valid.
- Source composition reuse and runtime reuse are separate decisions. A composed scene JSON can synchronize character/context; sibling runtime layers need a shared clock and explicit playback policy.

### Rigging

- Keep shoulder/head pivots in the correct local coordinate space. Rotate about the joint; do not translate a limb away from its shoulder.
- Arms can use a continuous silhouette with grouped transforms. If joints deform, verify every intermediate frame; a rig is not correct merely because endpoints look right.
- When a hand touches the face or holds a prop, preserve the contact constraint. Parent the interacting pieces appropriately or coordinate transforms. Do not independently bob a head away from its touching finger.
- Animate small, intentional gestures. Avoid rubber limbs, large generic bounce or morphing hand topology before the static anatomy is approved.

### Storyboard and timing defaults

| Moment | Suggested sequence | Playback policy |
|---|---|---|
| Success | Anticipation → short celebration → result accent → settle | About 1.2–1.8 s once |
| Failure | Shoulder/face reaction → explaining gesture → quiet hold | About 1.2–1.6 s once |
| Retry | Encouraging lean/gesture → retry cue → settle | About 1.2–1.6 s once |
| Promotion | Welcome → presenting → contextual card reveal | About 1.6–2 s once when visible |
| Processing | Low-amplitude movement and independent progress cue | Loop only while operation active and visible |
| Empty/uncertain/unavailable | Brief entrance/gesture → meaningful resting pose | Once, then static |
| Menu | Gentle entrance; restrained press response | Entrance once per appropriate screen/session; no per-tile loops |

These are starting values, not mandatory fixed durations. Never delay completion, CTA availability or navigation to finish an animation. A brief operation can skip a processing scene. Do not invent percentage progress or automatically turn an unresolved outcome into success.

Select a meaningful static frame explicitly for reduced motion and fallbacks. The final frame may be blank or an exit frame; “show last frame” is not sufficient without inspection. Keep status gestures bounded and haptics tied to real actions and platform preferences.

### Render comparison

Capture start, anticipation, peak, intermediate and settled frames from the actual player. Compare with source artwork for stroke/fill order, z-order, faces, digits, overlap and crop. Inspect motion in playback too: frame snapshots cannot prove smoothness. Label web-player results separately from Flutter/device results.

## 8. Runtime integration and state truth

- Reuse the current rendering library unless a source-backed requirement justifies another. Check exact package APIs instead of guessing from another platform.
- Keep a typed asset registry with id, path, revision, logical dimensions, format, fallback and playback policy. Record source/export hashes, bytes, palette and license in a manifest.
- Separate emotion/context/policy in a typed scene model when composition reuse is needed. Exhaustively map domain states; do not swallow unknown enum cases with misleading default art.
- A confirmed save can show success. A timeout or unconfirmed mutation may need “check result”; do not offer blind write retries. Idempotency/reconciliation must come from the actual operation contract, not a UI assumption.
- Cache compositions appropriately. Guard asynchronous loads against stale responses; dispose controllers/listeners. Stop motion when routes are inactive, app is backgrounded, scenes are offscreen or reduced motion is enabled.
- Preserve title, message and recovery action if artwork fails. Static fallback should keep layout stable. An icon fallback may be acceptable on asset error, not as the normal illustrated service tile.
- Avoid rebuilding whole lists every animation frame. Profile before adding blanket repaint boundaries or preloading every animation.
- Do not introduce a state-management framework just to display artwork. Keep business state in the established architecture.

## 9. Menu and section design

- Audit actual destinations first. Do not enforce a super-app's eight services, avatar, notifications, carousel or reorder feature on a small app without those needs.
- A service tile gets a designed object composition with distinct silhouette and label. A generic glyph in a tinted circle is still an icon, even if exported as SVG.
- Use a common visual scale, baseline, padding and palette. Distinguish similar services by composition, not only color: note/pencil, receipt stack, wallet/cards, exchange pair, analytics panel.
- At small sizes reduce details. Suggested initial sizes: 64–80 source canvas and 40–56 logical display for menu art; section illustration may be larger. Tune after mobile rendering.
- Keep touch target at least 48 dp in the Flutter/Android design, labels readable, and spacing adequate. Adapt grid columns to width and text scale; do not truncate essential labels to force four columns.
- Group sections by user task: services, information/settings and data management. Destructive actions remain clearly labeled controls, not playful promotional cards.
- Section art supports the heading; it does not replace the heading. Decorative headers must not push the main content or financial totals below excessive artwork.
- Keep icons for compact navigation, filters, edit/delete and system-like settings. Do not replace every small control with an illustration.
- Promotional artwork should lead to an existing feature or authorized campaign; avoid competing banners and recurring entrance animations when users return to a task.

## 10. Accessibility, theme and performance review

- Preserve meaningful text and CTA. Exclude decorative art from repeated screen-reader announcements; give meaningful standalone imagery an appropriate description.
- Announce status changes through the existing semantics pattern. Manage focus for modal interactions; do not steal focus for every inline illustration.
- Check light/dark, small widths and 100/130/200% text scale. Do not bake labels into images. Maintain contrast for text and meaningful UI graphics; decorative shading need not individually meet control contrast rules.
- Reduced motion applies to scene gestures, entrance, press effects and processing decoration. Keep a readable non-moving progress/status indication.
- Initial budgets may be menu SVG ≤25 KB, editable scene SVG ≤40 KB, Lottie ≤200 KB/scene, total artwork ≤3 MiB. Treat these as project-adjustable targets; measure actual bytes and decoded memory, not only compressed download size.
- Measure frame timing on the intended device/refresh rate when runtime execution is authorized. 60 Hz allows about 16.7 ms/frame; 120 Hz about 8.3 ms. Report device, mode, scenario and dropped frames rather than asserting zero jank from a web preview.
- Inspect long lists, rapid navigation, scene replacement, background/resume, load failure and offline behavior. Tests/checks must respect the user's explicit execution boundaries.

## 11. Sourcing and illustrator handoff

- Reference screenshots, Dribbble and Behance are not redistributable asset licenses. Do not trace/copy protected characters or logos.
- Check the actual asset license and attribution requirements before using a library asset; a site being called “free” is not sufficient. Keep source and license records per distributed asset.
- A useful brief includes product/audience, identity/palette, desired emotion, pose references, construction rules, composition, target display sizes and named layers/pivots.
- Delivery includes editable sources, exported assets, static fallbacks, provenance and review frames. Do not claim professional designer approval or artist authorship without evidence.
- If human illustration quality remains below the target, describe the specific unresolved construction issue and provide an actionable handoff. Continue authorized engineering/integration work that is independent of the final art.

## 12. Completion and reporting gates

1. Source audit and scoped plan: real screens, state mapping, current assets and proposed changes.
2. Representative artwork: approved identity, understandable five-digit hand construction, connected shoulders/wrists, consistent expression and mobile readability.
3. Export: no unintended double outline, incorrect layer order, deformation or source-to-render drift; registry/fallback/manifest/license in sync.
4. Motion: deliberate anticipation/action/settle, contact constraints, bounded playback and meaningful reduced-motion pose.
5. UI integration: working callbacks, accurate state/data, responsive labels, preserved accessibility and lifecycle.
6. Evidence: show actual preview files and state what was checked. Distinguish source checks, SVG PNGs, Lottie web playback, Flutter screenshots and device profiling.

For a plan-only task, leave implementation criteria unchecked. For a no-build task, provide source/asset previews and clearly leave device verification outstanding. Do not label a prototype “professional quality” or a valid export “production ready” based on tool success alone.


## 13. Reproducible asset production: reference to app

Use this sequence for a new illustration family, an approved reference revision, or an all-assets rollout. Earlier sections provide construction and runtime rules; this section defines concrete working steps and deliverables. Execute already authorized implementation without introducing an additional approval checkpoint. If the user explicitly requests a plan or representative-art checkpoint, preserve it.

### Step 1 — Inventory the real runtime surface

Read project instructions, the asset registry, bundle declarations, rendering widgets and actual screen call sites. Record every active scene and menu/category asset, its consumer, format, fallback, dimensions and semantic purpose. Include error, retry, uncertainty, processing and promotional states that exist in source. Do not fabricate domain states.

Separate runtime assets from historical studies, reference PNGs and generated review files. An all-assets request covers the illustrated product system; it does not automatically authorize changing launcher branding, user-uploaded media, or familiar back/close/delete controls. Identify such boundaries from actual usage. Preserve untracked and unrelated work.

Output: an active-asset inventory and screen-to-asset mapping. Gate: every registered path resolves and the bundle contains its intended folder.

### Step 2 — Freeze the visual reference and comparison conditions

Retain the approved image/source in a versioned design folder. Record which reference is authoritative, the approved identity, intended emotion, display size, composition and limitations. Identify whether the request concerns the character alone or a scene with background and context.

Measure the image/canvas aspect ratio before drawing. A 2:1 mobile banner should be compared against a 2:1 source render; stretching a 4:3 character sheet does not reproduce its composition. Record head bounding box, eye line, shoulder line, elbow/wrist locations, status motif position and deliberate lower-body crop. Measurements guide intentional curves; do not run bitmap contour detection or automatic tracing as the authoring method.

Output: reference image, brief, canvas and landmark notes. Gate: compare at identical aspect ratio and optical scale, with no text/buttons baked into artwork when those belong to UI code.

### Step 3 — Define the family style sheet

Choose character proportions, hairstyle, glasses, uniform/collar/pocket, outer/internal line weights, fill palette and restrained shading. Specify the banner safe area, status colors, menu source size, minimum display size and background treatment.

Record palette roles rather than blindly recoloring every asset: character teal, outline navy, skin/shadow, paper, success green, error red, contextual pastel. Art color and accessible UI text/button color are different contracts; a brighter decorative teal must not silently replace the application's accessible button color.

Output: a compact style sheet shared by scene and menu sources. Gate: the approved silhouette and palette remain recognizable at mobile scale.

### Step 4 — Draw the master figure and hand studies

Construct the head, neck, torso and shoulder line, then arms, elbows, wrists and palms. Make one open-palm study showing one thumb and four fingers and one folded/thumbs-up study with believable occlusion. Use an observed pose reference or a reviewed construction study, and record the actual source consulted.

Draw one continuous silhouette through each visible forearm, wrist and palm. Layers may divide the assembly internally, but the final contour must not contain an artificial closing seam. Build facial features, glasses and hair in the head's coordinate space. Draw clothing around the body, including sleeve overlap and collar/neck continuity.

Output: master SVG and hand studies rendered to PNG. Gate: connected shoulders/wrists, plausible finger count, understandable silhouette, and stable identity before decoration or animation.

### Step 5 — Author a representative native-vector set

Draw success, failure and promotion/information poses in separate versioned sources. Change body language and composition, not only eyebrows or an icon. A thumbs-up celebrates; a restrained shrug explains failure; a presenting gesture introduces a feature. Keep contextual objects separate if that is the approved design.

Use deliberate cubic Bezier contours with enough control points for smooth anatomy. Name groups by their role: background, foliage, character, torso/clothing, left/right arm assembly, hand details, head, expression, glasses, hair and context. Decide draw order explicitly; hair, sleeves and objects must cover the intended forms without accidental overlaps.

For constrained custom exporters, author only their supported path commands and styles. Reject unsupported masks, gradients, transforms and text rather than silently dropping them. If the reference requires a gradient, either implement and verify supported gradient export on the target renderer or record the remaining visual difference. Do not claim exact reproduction while exporting an approximation.

Output: editable SVGs, named layers and an explicit source revision. Gate: no raster embedding, excessive tracing paths, accidental double outline or malformed finger/face silhouette.

### Step 6 — Render and compare before rigging

Render the source at intended display size and enlarged size. Also render at the reference's exact pixel dimensions for a matching composition review. Create a comparison with clearly labeled reference and SVG, preserving aspect ratio and avoiding misleading crops.

Inspect head shape, hairstyle, eye/glasses alignment, expression, shoulder connections, elbow taper, palm/fingers, uniform silhouette, status motif, line weights and background balance. Review neutral and peak poses. Correct the underlying contours when construction is wrong; do not conceal it with a badge, oversized sleeve, extra shadow or crop.

Output: mobile render, enlarged render and reference comparison. Gate: visual acceptance is based on the resulting image. Successful XML parsing or export does not prove fidelity. Never invent a percentage match or designer approval.

### Step 7 — Expand the approved construction to all runtime assets

Apply the reviewed head/clothing/line palette to every registered scene, keeping context-specific gestures and expressions. Do not silently restore an older unapproved anatomy helper. Keep shared identity contours in a clearly versioned source and make revisions reproducible.

For menus, preserve destination meaning and label. Design recognizable object compositions (note/pencil, receipt stack, wallet/cards, chart, exchange pair) with common padding, baseline and optical scale. Use the same outline/palette and restrained pastel background where appropriate. Do not turn all destinations into identical circles or substitute generic glyphs for the illustrated menu family.

Output: full scene set, full menu/category set and contact sheets. Gate: no missing registered item, consistent identity, distinguishable silhouettes and no tiny unreadable detail.

### Step 8 — Rig bounded motion and export

Keep static rest orientation separate from animated transforms. Define head and shoulder pivots in the source coordinate system. A connected arm/palm assembly rotates around its shoulder; fingers do not need independent animation unless the gesture requires it. Avoid large rotations that expose a gap underneath a sleeve.

Storyboard anticipation, action, accent reveal and settled pose. Use subtle motion, finite success/failure/retry playback and processing looping only while the process is active. Choose a settled frame that preserves all meaningful context for reduced motion.

Export from editable native curves to shape groups using a verified design exporter or a constrained converter. For a custom converter, document absolute versus relative commands, contour closure, fill/stroke order, SVG versus Lottie paint order, supported transforms and interpolation. Do not embed a reference bitmap to disguise unfinished vector construction.

Output: local Lottie JSON, static SVG fallback, named motion groups/pivots and storyboard timings. Gate: export rejects unsupported input, preserves visual layering and stays within recorded budgets.

### Step 9 — Review the actual player

Load the exported files with the project's installed renderer or an explicitly labeled web-player preview. Capture rest, anticipation, peak, intermediate and settled frames, and watch playback. Compare actual-player contours against the source renders, checking clipping, stroke/fill order, facial features, fingers and joint continuity.

Exercise reduced motion, repeated playback, pause/resume and asset-load failure where execution is authorized. A source snapshot generator is useful but is not evidence that the actual player reproduces it. Web-player loading is not Flutter/device parity or smoothness proof.

Output: player captures and a concise renderer/version/result record. Gate: every active scene loads; source/player drift and motion defects are resolved or explicitly identified.

### Step 10 — Integrate through the typed registry

Update source canvas, registry dimensions, widget aspect ratio, asset paths, revision, static fallback and bundle declaration together. For example, a 640 x 320 scene has height = width / 2; changing JSON dimensions alone leaves the UI layout inconsistent.

Keep titles, financial values, recovery actions and CTA in native UI. Decorative art should not repeat the adjacent screen-reader label. Use responsive banner sizing: a wide scene can use available width above text on a narrow layout and a smaller leading frame beside text on wider layouts. Preserve minimum tap targets and text-scale adaptation.

Retain real state truth: show success only after confirmed completion; distinguish failure from unconfirmed timeout; connect retry/recovery to the actual operation. Preserve async load guards, composition caching, controller disposal, reduced-motion behavior and background/route pause handling.

Output: actual consumers use the revised files with stable fallbacks and working callbacks. Gate: analyzer/source contracts pass and all registry/bundle paths resolve.

### Step 11 — Make regeneration safe and complete

Choose one authoritative source per asset and version source, export and review artifacts together. If a script owns the SVG, edit the script and regenerate; if manually edited SVG is authoritative, the generator must not overwrite it. Avoid competing old generators that restore rejected artwork.

Provide one documented production command sequence. In the Vasa example, the sequence is:

```powershell
python tool/author_nara_v14.py
python tool/generate_illustrations.py
python tool/preview_nara_lottie.py --node $AssetPreviewNode --modules $AssetPreviewModules
python tool/preview_menu_illustrations.py --node $AssetPreviewNode --modules $AssetPreviewModules
dart analyze lib
```

`AssetPreviewNode` and `AssetPreviewModules` must resolve to the available Node executable and installed module directory. The menu generator refreshes runtime menu art, exports current native scene sources and checks asset contracts. Preview rendering is a review artifact, not an application build. Adapt filenames, checks and commands to the current project; this example does not prescribe Vasa tooling to other applications.

Track ID, runtime path, source path/revision, viewBox, bytes, palette, source/export hashes, format, license, fallback and playback policy. Keep reference PNGs and historical studies out of active asset counts. Check that no active source contains script/image/remote references and no Lottie depends on unexpected raster assets. Preserve provenance rather than replacing a detailed license record with a generic statement.

Output: repeatable commands and consistent manifests/license entries. Gate: regenerating the same sources does not resurrect rejected art or alter unrelated history.

### Step 12 — Deliver reviewable evidence and state boundaries

Provide a contact sheet for menus, an actual-player scene preview and a reference comparison when fidelity was requested. Link editable sources and describe the few meaningful changes. State executed checks and unresolved visual differences plainly.

For a no-build request, source renders, asset checks and analyzer results can be delivered without a Flutter build/run. Device crop, accessibility, renderer parity and frame timing remain device verification work; do not mark those complete. For an implementation request, finish the authorized source/integration work before handing back a plan.

Output: complete active asset set, integrated consumers, reproducible workflow, review artifacts and truthful verification report.
