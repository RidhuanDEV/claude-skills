# Vector geometry

Use the visual master as a reference for hand-authored geometry. Set the target coordinate system and place silhouette, joints, and landmarks first. Use simple primitive forms where the design benefits, or BÃ©zier segments with handles aligned to the intended tangent at smooth joins.

- Put anchors at deliberate extrema, corners, and changes in curvature. Use aligned tangents for smooth joins and break them where the design needs a cusp. Evaluate contours at target scale before adding nodes.
- Close paths for meaningful fills and choose the intended nonzero or even-odd rule for holes. Inspect winding and overlaps where contours intersect. Verify joins, caps, and miter behavior.
- Keep strokes live where editing and runtime behavior support them. Expand a stroke only when a required export cannot preserve the intended outline or needs filled geometry. Keep the editable original.
- Make paint order explicit. Use transform groups for meaningful assemblies and named layers for animation. Avoid redundant transform nesting and orphaned hidden nodes. Verify that bounds and pivot coordinates share the expected space.
- Keep gradients, clips and masks when the target supports them and the visual result requires them. Compare an optimized export to the master before removing IDs, altering precision, or collapsing transforms.

Review silhouette first, then detail. Coordinate counts, successful parsing and hash matches can support inspection but do not prove quality or closeness to a reference.
