# Lottie and dotLottie workflow

Verify the project's editor or exporter, interchange format and exact runtime version first. Treat Lottie JSON and dotLottie packaging as separate contracts. Confirm that the runtime supports the chosen masks, blending, strokes, expressions, fonts, assets and playback features. A successful export or generic JSON parse does not confirm compatibility.

1. Write the motion storyboard, source size, layer names, groups and pivots. Establish stable ordering. Confirm frame range and rate against the application contract.
2. Reuse the project's exporter. Produce the required JSON or dotLottie archive. For archives verify manifest, animation IDs, declared assets and applicable spec version. Use the registered motion and fallback paths.
3. Inspect first, key, mid-motion, settled and repeat-boundary frames. Play the real animation in the intended player. Check timing, layer order, shape transforms, crop and missing images or fonts. Compare the exported still to the source render.
4. Capture player/version and scenario evidence. Mark target runtime as NOT_RUN if only a web preview was available. Preserve a suitable static or reduced-motion asset and document lifecycle behavior.

Source dimensions, embedded asset policy and a version-specific feature matrix are more useful than adding unverified exporters. See [official specifications and runtimes](open-source-source-register.md).

For app-owned bundled exports, use verified manifest metadata when available. Catch fetch/decode errors before bytes reach the player. Mount the player separately from its fallback, because cleanup can clear its container. Treat player load events and initialization timeout separately from syntax checks. Exercise invalid data and missing files in the actual consumer before reporting fallback behavior.
