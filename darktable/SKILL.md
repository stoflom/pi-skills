---
name: darktable
description: Develop raw images (CR3/PEF/RAW/...) with darktable via MCP tools — user's standard 7-step pipeline (WB, lens, orientation, color calibration, contrast equalizer, color balance rgb, AGX), measure tonal stats, import/cull, apply styles, and export in multiple formats. Use when asked to develop, process, grade, or export a raw photo.
---

# darktable via MCP

Server: `darktable-mcp` (headless, links libdarktable directly). Setup/build docs:
[README.md](./README.md). Server reference: `src/mcp/README.md` in the darktable
source tree (upstream: <https://github.com/darktable/darktable/blob/master/src/mcp/README.md>).

## Tools

| Group | Tools |
|---|---|
| Introspection | `list_modules`, `module_schema` (field name/type/offset/min/max/enum + `doc_url`), `decode_params`, `encode_params` |
| Develop | `render` (→ PNG preview), `image_stats` (per-channel min/max/mean/p1/p50/p99/clip counts) — both take `{input:{path\|imgid}, width?, height?, stack?, disable_tone_mappers?, history_end?}` |
| Library | `import_images`, `list_film_rolls`, `list_images`, `get_history`, `get_metadata`, `reset_history`, `set_rating`, `set_color_label` |
| Styles | `list_styles` (filter/limit), `apply_style` (batch, overwrite), `save_style`, `import_style` |
| Config | `list_conf`, `get_conf` (read-only; restart with `--conf k=v` to change) |
| Export | `export_images` — multi-format, single (`input`/`out_path`) or batch (`imgids[]`/`out_dir`) |

`get_metadata {imgid}` returns camera, lens, EXIF (ISO, shutter, aperture, focal length,
capture time) — use it instead of exiftool for the pipeline's lens/WB values. (The `raw`
black/white-point block appears only after the image has been through the pipe once.)

## Critical: edits persist (server ≥ library-tools update)

**A `stack` on an `imgid` input is written to the image's history and its XMP sidecar.**
There is no throwaway duplicate anymore — `render`/`image_stats` with a stack *is* how you
commit an edit, and there is no undo. Same for `disable_tone_mappers` (also written to
history). Implications:

- **Parameter exploration without a trail:** use scratch `input.path` (see below) — the
  stack shapes the pixels but nothing survives the request. That's what makes
  `image_stats` usable for A/B-comparing params.
- **To leave the image alone:** run the server with `--read-only` (flag goes *before*
  `--core`), or against a catalog you can live with.
- **Cleanup:** `reset_history {imgid}` clears edits back to imported state.
- **`history_end` + stack is destructive:** entries past `history_end` are dropped for
  good. Without a stack, `history_end` only selects what to render/export and changes
  nothing (also the only form `export_images` accepts).

## Input semantics (`input: {path}` vs `{imgid}`)

| Input | Behaviour |
|---|---|
| `{imgid}` | The normal route. Edits persist; the XMP sidecar follows the library's `write_sidecar_files` setting. |
| `{path}` **not** in the catalog | **Scratch**: imported so darktable can develop it (the XMP sidecar is read, so committed edits apply), then the rows and roll are removed before the request returns. Nothing persists, the file on disk is never touched. |
| `{path}` **already** in the catalog | **Refused**, naming the `imgid`. Use `input.imgid`; add `history_end: 0` to that call to render it ignoring its existing edits. |

- Prefer `import_images {paths[]|folder, recursive?}` then work by `imgid` — that's the
  route where edits are kept and visible in the catalog. Path input is for looking at a
  file, not working on one.
- This machine's server runs with `--configdir ~/.config/darktable-mcp`, so it has its
  **own persistent catalog** in that directory (no `:memory:` injection when `--configdir`
  or `--library` is given). Its `darktablerc` has `write_sidecar_files=on import`, so
  committed edits (and first-render auto-applied history) **write .xmp files next to your
  raws**. Plain `render` of a never-developed imgid also materializes the ~12
  auto-applied workflow modules into its history + sidecar — that's darktable's own
  default, but it does touch your files.

## Reference pipeline (user's standard workflow — in this order)

1. **White balance — camera reference** → `temperature` (scalar)
   - Leave `red`/`green`/`blue` at 0 (camera WB from the raw), `preset` for camera ref.
2. **Lens correction — per EXIF** → `lens` (scalar)
   - `method: DT_IOP_LENS_METHOD_LENSFUN` (value 1 — camera/lens DB matched from EXIF; this
     is what the user's own XMPs use) or `DT_IOP_LENS_METHOD_EMBEDDED_METADATA` (value 0).
   - `modify_flags: DT_IOP_LENS_MODFLAG_ALL`; set `focal`, `aperture`, `distance` from EXIF
     (`get_metadata`, or `exiftool -FocalLength -FNumber -LensModel <raw>`).
3. **Orientation — per EXIF** → `flip` (scalar)
   - `orientation` takes the EXIF Orientation tag value:
     5=ROTATE_CW_90_DEG, 6=ROTATE_CCW_90_DEG, 3=ROTATE_180_DEG, 2/4=flips. 0=NONE.
4. **Color calibration — camera** → `channelmixerrgb` (**non-scalar**, has arrays → blob_hex)
   - Camera calibration profile is auto-loaded from the camera; usually add the module with
     defaults. `illuminant` enum (e.g. `DT_ILLUMINANT_DETECT_SURFACES`), `gamut`, `adaptation`.
5. **Contrast equalizer — sharpen preset** → `atrous` (**non-scalar** x[][]/y[][] → blob_hex)
   - `octaves` (default 3), `mix` (0–2). The UI "sharpen" preset is an S-curve through (0.5, 0.5);
     build the node arrays in the blob accordingly.
6. **Color balance rgb — saturation up, lift shadows, recover highlights** → `colorbalancergb` (scalar)
   - `saturation_global` (e.g. 0.05–0.15), `brilliance_shadows` (positive = lift shadows),
     `brilliance_highlights` (negative = recover/compress highlights), `vibrance`, `contrast`.
   - Toned zones available: `_shadows`/`_midtones`/`_highlights`/`_global` for Y/C/H, chroma, saturation, brilliance.
7. **AGX — contrast, fit to sRGB, tone mapping** → `agx` (scalar)
   - `curve_contrast_around_pivot` (default 3; 4–5 for punch), `look_slope` (default 1; 1.2–1.5).
   - `base_primaries: DT_AGX_SRGB` to fit/tone-map to sRGB; `curve_target_display_black_ratio` /
     `curve_target_display_white_ratio` control the fit. Filmic toe/shoulder rolloff — prefer over
     hard-curve contrast modules for natural looks.

All of the above are available as stack entries:
`{operation, params{} | blob_hex, enabled?, multi_priority?, before?, after?}`.
`before`/`after` name another module and place the entry relative to it (never both) —
relative placement instead of opaque `iop_order` numbers. `get_history` reports each
module's `iop_order` so you can read the current arrangement first.

## Reading the user's XMP sidecars (`<RAW>.xmp`)

Reference example: `IMGP3521.PEF.xmp` (shipped alongside this skill). Structure:

- `<darktable:history>` is an `rdf:Seq` of `rdf:li` with attrs: `num`, `operation`, `enabled`,
  `modversion`, `params`, `multi_name`, `multi_priority`, `blendop_params`.
- **`params` is either plain hex OR `gzNN<base64>`** where `NN` is the uncompressed length in hex and
  the payload is **zlib** (0x78 0x9c magic), NOT gzip. Use `zlib.decompress`, not `gzip.decompress`.
  ```python
  import base64, zlib
  if p.startswith('gz'):
      n = int(p[2:4], 16); data = zlib.decompress(base64.b64decode(p[4:]))[:n]
  else:
      data = bytes.fromhex(p)
  ```
  Decode fields against `module_schema` offsets (little-endian C layout).
- **`multi_name` = applied preset** — built-ins worth knowing: atrous `"Sharpen"`, `"Denoise"`,
  `"sharpen-slightly"`; channelmixerrgb/exposure/sigmoid `"_builtin_scene-referred default"`;
  flip `"_builtin_auto"`. Empty-override blobs are fine (e.g. agx with 2B blob = defaults).
- `masks_history` section: `mask_type=2` = drawn/AI object masks (base64+gzip point data),
  `mask_type=4` = groups (AI object groups, "Birds", "group \`contrast equalizer • Sharpen\'").
- Typical real dev order seen: rawprepare → demosaic → colorout → highlights → channelmixerrgb
  (scene-referred) → exposure → flip(auto) → sigmoid → atrous → colorbalancergb → colorin →
  temperature → lens (method=1 LENSFUN, i.e. EXIF DB) → agx.

## Local sharpening on subjects (user's bird technique)

Create AI object masks (e.g. "Left Bird", "Right Bird"), group them ("Birds"), then apply atrous
with the `Sharpen` preset scoped to that mask group (mask_manager groups named
group \`contrast equalizer • Sharpen\'), optionally plus a `Denoise` atrous for the background.
With MCP, reproduce as multiple `atrous` entries with `multi_priority` to simulate masked
instances; use `before`/`after` to keep them in the right pipeline position.

## XMP sidecar handling

- **Scratch `input.path`** reads the sidecar during the ad-hoc import, so a
  quick `render`/`image_stats`/`export_images` on a raw with a `.xmp` develops it
  through the full committed history — and leaves no trace in the catalog or on disk.
  This is the fastest way to preview or re-export an already-edited raw:
  ```
  export_images(input: {path: "/path/to/IMG.PEF"}, out_path: "/path/out.jpg", format: "jpeg", quality: 92, width: 1920, height: 1281)
  ```
- **`import_images` + `input.imgid`** is the route where work sticks: the sidecar is read
  on import, and every subsequent stack-based render commits back to the image and
  rewrites the `.xmp` (per the library's `write_sidecar_files`).

## darktable-cli as an alternative

When the MCP server isn't running or for batch processing, `darktable-cli` handles XMP
sidecars natively:
```
darktable-cli --import "--core --library <catalog>" --module "export" \
  --format "png" --export <width>x<height> <raw> <output_dir>
```
This reads the XMP, applies the full history, and exports. Use MCP for interactive
tweaking, `darktable-cli` for one-shot or batch exports.

## Workflow

1. **Check for an XMP sidecar first** (`ls <RAW>.xmp`). If it exists and you just need an
   output file, scratch `export_images {input:{path}, ...}` develops through the committed
   history — no import, no stack, nothing persists.
2. To actually work on the image: `import_images` it, then use `input.imgid` everywhere.
   Read `get_metadata` for lens/EXIF values and `get_history` for the current stack.
3. **Explore params with scratch `input.path`** (`image_stats`/`render`) so failed
   variants don't land in the image's history; commit the good variant once with a
   stack on the `imgid` (it persists — no undo).
4. **Render a quick preview first** (`render` with `width` ~1600; bounding box, aspect
   preserved, defaults to 1024 when omitted) to see the base look before tuning.
5. **Check every field name against `module_schema`** before passing `params`. Field
   names are not what you'd guess (e.g. exposure has no `highlight`).
6. Iterate with small `render` previews; use `image_stats` (defaults 512) to measure
   mean/p99/clip counts when judging exposure or clipping objectively.
7. Finalize with `export_images` — **omit `width`/`height` for full resolution** (the old
   1024-default no longer applies to export). Batch: `imgids[]` + `out_dir`; the reply
   lists the written `paths` and any `skipped_paths`.

## Pitfalls

- **A stack on an imgid commits the edit** (history + sidecar, no undo). Explore with
  scratch `path` input, or run the server `--read-only`. `reset_history` clears an image.
- **`history_end` with a stack rewrites history**, dropping entries past it for good.
- **First render of a never-developed imgid materializes the auto-applied workflow
  history** (~12 modules) into the image and writes the sidecar — darktable's own default,
  but it touches the file. `--read-only` takes it back.
- **`input.path` for a cataloged file is refused** — the error names the `imgid`.
- **Non-scalar modules reject `params`/`fields`** (arrays → error "pass a full blob_hex").
  Known non-scalar: `colorbalance`, `channelmixerrgb`, `atrous`, `basecurve`, `tonecurve`,
  `colorzones`. Build the blob yourself from `module_schema`: plain little-endian C layout
  (params_size bytes). Easiest: python3 snippet writing floats/ints at the documented
  offsets, then pass `blob_hex`.
- `encode_params` only works for fully-scalar modules; `decode_params` requires the blob to
  match the module's **current** param size (no legacy conversion — older-version blobs may
  fail). `decode_params` on a `get_history` blob is still the best way to copy a known-good
  atrous preset out of a real library history.
- Enum fields accept symbolic names when passing `params` (e.g. `DT_AGX_SRGB`).
- `export_images` **refuses `stack`/`disable_tone_mappers`** — edit first (render with a
  stack or apply_style), then export. It supports `format` (jpeg/png/tiff/webp/jxl/avif/
  exr/pfm/ppm/j2k — inferred from the out_path extension when omitted, else jpeg),
  `quality` (lossy), `upscale`, `high_quality`. Conflict policy for existing targets is
  `plugins/imageio/storage/disk/overwrite` (default: free `_01` name; 3 = skip, reported
  in `skipped_paths`).
- Base pipeline already includes rawprepare/demosaic/tone-mapper; don't re-add those.
- `render`/`image_stats` take `input.path` (scratch) or `input.imgid` (persistent).
  `disable_tone_mappers` switches off whichever tone mapper `plugins/darkroom/workflow`
  auto-applies so one you add owns the tone curve — and it's written to history like any
  other edit.
- Batch export stops at the first image it cannot write; the error names files already on
  disk and unattempted images.

## Quick "natural" stack (all scalar, verified working)

```
[
  { operation: "exposure",       params: { exposure: 0.15 } },
  { operation: "agx",            params: { curve_contrast_around_pivot: 4, look_slope: 1.25, dynamic_range_scaling: 0.05, base_primaries: "DT_AGX_SRGB" } },
  { operation: "colorbalancergb",params: { saturation_global: 0.08, brilliance_shadows: 0.05, brilliance_highlights: -0.05 } },
  { operation: "sharpen",        params: { amount: 0.6 } }
]
```

Other handy scalar modules: `shadhi`, `temperature`, `highlights`, `denoiseprofile`,
`vignette`, `vibrance`, `velvia` (strength 0–100, sat boost), `basicadj`
(brightness/contrast/saturation/vibrance).

Field names drift between darktable builds — always re-check `module_schema` before use.
