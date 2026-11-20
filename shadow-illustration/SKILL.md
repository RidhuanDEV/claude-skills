---
name: shadow-illustration
description: "Use when creating branded illustrations for mobile apps, including mascots, onboarding scenes, banners, status artwork, pose variants, and SVG or Lottie handoff. Works across agents with the image tools available on each host."
---

# Shadow Illustration

Produce an illustration family that matches the app and its approved artwork. Establish the visual direction before expanding to multiple poses.

## Choose the deliverable

| Request | Deliverable |
|---|---|
| Art direction, mascot exploration, static onboarding or banner | Raster concept or approved PNG/WebP sized for its placement |
| Transparent character or object | RGBA PNG with clean edges, checked on light and dark surfaces |
| Editable illustration, recoloring, or independent motion | Authored SVG with named parts and, when requested, Lottie through the project's existing pipeline |

Use the host's built-in or explicitly configured image generator for raster generation or reference-guided edits. In Codex, load the installed imagegen skill when available. Discover the equivalent capability on other hosts before promising a generated image. When raster generation is unavailable, deliver the visual brief and prompt, or continue with SVG if it meets the request. Keep proprietary references within approved tools and destinations.

## Build the illustration family

1. Inspect the product screen, existing assets and brand palette. Record the artwork role, canvas ratio, focal point, crop, background, and smallest display size. Use a character or visual asset the user has supplied or approved.
2. Select one master image. Record proportions, facial features, hair, clothing, palette, outline and shading. Supply that same reference for variants if the host supports reference inputs. Specify pose, expression and props separately so the brief shows what can change.
3. Generate or draw one representative scene first. Review it at app size and enlarged. Check silhouette, readable gesture, elbow and wrist transitions, hand proportions, visual hierarchy, and crop. Keep live UI text and buttons in the app. Use distinct gestures and shape cues to communicate success, waiting, failure, and recovery.
4. Use the reviewed master and the same comparison scale for the rest of the set. Place variants side by side to spot drift. Track the source, prompt or vector source, dimensions, and intended screen or state.
5. For SVG and Lottie, build deliberate paths from the visual reference. Separate background, character, movable limbs, expression and status marks as needed. Use a continuous arm-and-palm silhouette, stable pivots, and explicit paint order. Render the SVG and check the exported animation in the target player where available. Use a static fallback and reduced-motion treatment when integrating motion.

For example, if a mobile finance app already uses a teal-uniform mascot, use the approved success scene as the master. A recording scene can present a floating note and pencil. A failure scene can show a mild shrug and a red status mark. Give each pose the same character proportions and keep copy and actions as UI components.

## Deliver and report

Deliver requested assets in their editable or runtime formats, with a preview or comparison and clear filenames. State whether the result was checked as a static render, animation, or in the app on a device. For implementation under Shadow Monarch, consult its MOBILE-DESIGN.md for runtime integration and verification.
