# vendor.py

Makes the bundled third-party packages importable. `src/vendor/` holds packages
we ship with the plugin (currently Pillow, for high-quality texture resampling)
so the artist never has to pip-install anything into Cinema's Python. Pure
stdlib, no `c4d` — the path juggling is testable in CI.

The vendor directory is **OPTIONAL**: a checkout without it still runs, so every
caller must degrade gracefully (`import_pillow()` returns `None`).

## Functions

- `vendor_dir()` / `available()` — the resolved `src/vendor` path and whether it
  exists on disk.
- `ensure_path(path=None)` — put the vendor dir on `sys.path` (once); `True` if
  it is there now. Appended, never prepended: a package the user installed into
  Cinema's Python themselves wins over our bundled copy — their machine, their
  call.
- `import_pillow()` — the Pillow `Image` module, or `None` if it is not
  available anywhere (bundled or user-installed).
