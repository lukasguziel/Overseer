# core/textures.py

Pure texture analysis and resizing — no `c4d`, so it is fully unit-tested in
CI. The c4d-bound adapter (`cinema/adapter.py`) collects the raw shader
references and calls into this module for everything that only needs the file
on disk.

## Image analysis

`analyze_image(path) -> ImageInfo | None` returns per-file metadata:
`width`, `height`, `bit_depth`, `channels`, `has_alpha`, `greyscale`,
`colorspace`. It uses **Pillow when importable** and otherwise falls back to
struct-based header parsers for PNG, JPEG, TIFF (minimal), EXR, BMP, TGA and
HDR. Unknown or unreadable formats degrade gracefully (`None`, or fields left
at their zero/empty default). We never assume Pillow is installed in the C4D
Python environment.

Colorspace is only reported where the header states it cheaply: `sRGB` from a
PNG `sRGB` chunk, `linear` for EXR/HDR (float formats), `YCbCr` for JPEG,
`ICC` when Pillow finds an embedded profile — otherwise empty.

## VRAM estimate

`vram_bytes(w, h, mipmaps=True)` = `w * h * 4` (uncompressed RGBA, what the map
actually costs in RAM/VRAM regardless of on-disk JPEG compression) times
`MIP_FACTOR` (4/3 ≈ 1.33) for the mip chain. `aggregate(infos)` sums this over
a set of `ImageInfo` (each physical file once) and buckets them into
`8K / 4K / 2K / < 2K` tiers — this drives the Overview **texture-budget** card
(`report.textures.total_vram`).

## Resize

`resize_decision(ext, has_pillow) -> (ok, note)` decides per format whether a
resize is possible: Pillow handles the common raster formats, otherwise only
PNG (the pure path). Anything else is skipped with a human-readable German note
so the batch never fails as a whole.

`resize_file(src, dst, percent, has_pillow)` writes a resized **copy** (Pillow
`BOX` filter, or the pure PNG path). `resize_png_bytes` implements a stdlib-only
PNG decode → box-downscale → encode for 8-bit grey/greyA/RGB/RGBA PNGs; 16-bit
and indexed PNGs are declined (`None`) rather than mangled. `resize_target`
appends the `_<percent>` suffix, preserving the path's relative/absolute form so
the relink keeps the original pipeline convention.

The adapter (`SceneAdapter.texture_resize`) copies each source once, relinks
every shader that referenced it and journals the relink as a `texpath` change;
originals are never overwritten.
