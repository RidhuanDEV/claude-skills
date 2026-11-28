# Vector geometry

Use the visual master as a reference for hand-authored geometry. Set the target coordinate system and place silhouette, joints, and landmarks first. Use simple primitive forms where the design benefits, or BÃ©zier segments with handles aligned to the intended tangent at smooth joins.

- Put anchors at deliberate extrema, corners, and changes in curvature. Use aligned tangents for smooth joins and break them where the design needs a cusp. Evaluate contours at target scale before adding nodes.
- Close paths for meaningful fills and choose the intended nonzero or even-odd rule for holes. Inspect winding and overlaps where contours intersect. Verify joins, caps, and miter behavior.
- Keep strokes live where editing and runtime behavior support them. Expand a stroke only when a required export cannot preserve the intended outline or needs filled geometry. Keep the editable original.
- Make paint order explicit. Use transform groups for meaningful assemblies and named layers for animation. Avoid redundant transform nesting and orphaned hidden nodes. Verify that bounds and pivot coordinates share the expected space.
- Keep gradients, clips and masks when the target supports them and the visual result requires them. Compare an optimized export to the master before removing IDs, altering precision, or collapsing transforms.

Review silhouette first, then detail. Coordinate counts, successful parsing and hash matches can support inspection but do not prove quality or closeness to a reference.

## Raster-to-vector tracing (PNG or JPG to SVG)

Tracing is reconstruction, not conversion. Embedding the PNG in an `<image>` element, or shipping an auto-trace with thousands of noisy nodes, does not produce a vector logo.

1. **Inspect the source.** Note pixel size, anti-aliasing, JPEG artefacts and transparency. A 512 px source cannot reveal detail below about 1 px at that scale; record that limit.
2. **Identify primitives and type.** Rebuild circles, straight edges, equal radii and symmetry as real geometry. Text is either re-set in the identified, licensed font and converted to outlines, or redrawn; never trace letters blindly. Ask for the original font or brand vector first, because the owner may already have it.
3. **Use auto-trace only as an underlay.** Tools such as `vtracer` (MIT) or `potrace` (GPL-2.0; check the license before bundling it) give a reference path. Redraw on top of it with the fewest anchors that hold the shape, then delete the underlay.
4. **Fix the frame.** Set a `viewBox` that matches the source aspect ratio with deliberate padding; no fixed `width`/`height` unless the consumer needs them. Sample colours from flat areas, not anti-aliased edges, and map them to brand tokens when they exist.
5. **Compare renders.** Rasterize the SVG at the source size and overlay it on the PNG (difference blend or pixel diff), then check legibility at the real target sizes (for example 16, 32, 64 and 512 px, plus favicon and dark background).
6. **Report verified and assumed separately.**

| Verified (state how) | Assumed (state why) |
| --- | --- |
| Overlay difference at source size, renders at each target size, `viewBox`, anchor count, parse in the target renderer | Exact brand colours without a brand spec, font identity, detail smaller than the source resolution |
