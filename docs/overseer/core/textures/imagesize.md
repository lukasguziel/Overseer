# core/imagesize

Header-only image dimension reader. Pure, no `c4d`, so it is unit-testable in CI.

Reads just enough bytes to pull `(width, height)` out of the common archviz texture formats — never decodes pixels, so an 8K EXR is as cheap as a thumbnail. Everything is best-effort: unknown/corrupt files return `None`.

## Public functions
- `resolution_tag(px)`: human "nK" tag for the larger edge (4096 -> "4K", 8192 -> "8K"). Below 1K the raw pixel edge is shown ("512px") so tiny maps stay honest. Non-positive returns "".
- `image_size(path)`: returns `(width, height)` from the file header, or `None`. Detects format by magic bytes: PNG, GIF, BMP, PSD/PSB (`8BPS`), OpenEXR, WebP, TIFF, JPEG, HDR/Radiance. TGA carries no magic number, so it is decided by the `.tga` extension. Any exception yields `None`.

## Internal helpers (format-specific header parsers)
- `_read_cstr(f)`: reads a NUL-terminated latin-1 string.
- `_exr_size(f)`: scans EXR header attributes for `dataWindow`, computing size from the xmin/ymin/xmax/ymax bounding box.
- `_webp_size(f)`: handles VP8, VP8L, and VP8X chunk variants.
- `_tiff_size(f, head)`: honors byte-order (`II`/`MM`), reads IFD tags 256 (width) / 257 (height), SHORT vs LONG typed.
- `_jpeg_size(f)`: walks markers, skipping fill bytes and payload-less markers, until a SOF marker yields dimensions.
- `_hdr_size(f)`: parses the Radiance resolution line (e.g. "-Y 1080 +X 1920"); first token is the Y (height) axis in canonical form.
- `_tga_size(path)`: reads width/height from the 18-byte TGA header.
