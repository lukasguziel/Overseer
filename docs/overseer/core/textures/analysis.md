# core/textures/analysis.py

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

`vram_bytes(w, h, mipmaps=True, channels=0, bit_depth=0)` =
`w * h * channels * bit_depth / 8` (uncompressed, what the map actually costs
in RAM/VRAM regardless of on-disk JPEG compression) times `MIP_FACTOR`
(4/3 ≈ 1.33) for the mip chain. Unknown metadata (0) falls back to 8-bit RGBA
(`4` bytes/pixel), so a 32-bit EXR counts 4x an 8-bit map of the same size
instead of being underestimated. GPU texture compression (BC/DXT) is not
modelled. `aggregate(infos)` sums this over a set of `ImageInfo` (each physical
file once) and buckets them into `8K / 4K / 2K / < 2K` tiers — this drives the
Overview **texture-budget** card (`report.textures.total_vram`).

## Resize

There are three resize engines, tried best first: the host's bitmap engine
(Cinema 4D's own, always there inside the plugin — no third-party dependency,
and HDR/EXR stay float end to end with no tonemapping or depth reduction),
Pillow (only if the user installed it), and the built-in PNG writer
(dependency-free, but PNG only). `HOST_RESIZE_EXTS` lists the formats the host
engine reads and writes back.

`resize_decision(ext, has_pillow, has_host=False) -> (ok, note)` decides per
format whether a resize is possible against those three engines. Anything no
engine can handle is skipped with a human-readable note so the batch never fails
as a whole.

`resize_file(src, dst, percent, has_pillow)` writes a resized **copy** via
Pillow or the pure PNG path. The Pillow path (`_resize_pillow`) uses **LANCZOS**,
the best-quality resampler Pillow offers, and carries over everything that makes
a texture a texture: the pixel mode (so RGBA keeps its alpha and an `I;16` / `F`
map keeps its bit depth), the ICC profile, and for JPEG a high quality + 4:4:4
chroma so the copy is not visibly worse than the original beyond the intended
downscale. Exotic modes (paletted, 1-bit) are converted first, never silently
mangled.

`resize_png_bytes` implements a stdlib-only PNG decode → box-downscale → encode
for 8-bit grey/greyA/RGB/RGBA PNGs; 16-bit, indexed, and **interlaced** (Adam7)
PNGs are declined (`None`) rather than mangled — Adam7 rows are laid out per
pass, not per scanline, so unfiltering them as if sequential would scramble the
image. `resize_target` appends the `_<percent>` suffix, preserving the path's
relative/absolute form so the relink keeps the original pipeline convention.

The adapter (`SceneAdapter.texture_resize`) copies each source once, relinks
every shader that referenced it and journals the relink as a `texpath` change;
originals are never overwritten.
