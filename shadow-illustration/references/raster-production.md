# Raster production

1. Prepare a visual brief with intended placement, pixel dimensions or crop, master reference, stable identity, gesture, emotional intensity, palette, lighting and background/alpha needs. Collect authorized source images and identify the host's supported reference and editing features.
2. Generate one focused concept or work in the existing raster editor. Preserve a layered master when editability is required. Use separate layer groups or masks for background, figure, foreground props and shadows. Compare edits against the approved master, especially when changing one region.
3. For painterly work, establish values before texture. Align brush density to the display scale. For pixel work, set the source grid before drawing and verify the intended scaling filter. Avoid strong sharpening or compression that adds edge noise.
4. Inspect transparent exports against both light and dark surfaces. Check that non-art pixels are transparent, edge antialiasing has no colored halo, and a crop does not remove intentionally soft shadows. A preview checkerboard is not proof of alpha.
5. Export to the requested format and pixel dimensions with the required color profile. Prefer the project's established profile, often sRGB for web and app assets. Compare the compressed export with the master at actual display size and inspect detail where artifacts are likely.
6. Record output dimensions, byte size, alpha if expected, source or master link, prompt and available model/tool metadata. Keep the actual approved raster output. Generative reruns do not establish pixel reproducibility.

Use [the source register](open-source-source-register.md) for authoritative editor and interchange documentation. Verify layered round trip before promising editability across editors.
