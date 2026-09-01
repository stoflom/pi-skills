---
name: darktable
description: Develop raw images (CR3/PEF/RAW/...) with darktable via MCP tools — user's standard 7-step pipeline (WB, lens, orientation, color calibration, contrast equalizer, color balance rgb, AGX), measure tonal stats, and export finished files. Use when asked to develop, process, grade, or export a raw photo.
---

# darktable via MCP

Tools: `mcp_darktable_list_modules`, `module_schema`, `decode_params`, `encode_params`,
`render`, `image_stats`, `export`, plus library tools (`list_images`, `get_history`, styles).

## Reference pipeline (user's standard workflow — in this order)

1. **White balance — camera reference** → `temperature` (scalar)
   - Leave `red`/`green`/`blue` at 0 (camera WB from the raw), `preset` for camera ref.
2. **Lens correction — per EXIF** → `lens` (scalar)
   - `method: DT_IOP_LENS_METHOD_LENSFUN` (value 1 — camera/lens DB matched from EXIF; this is
     what the user's own XMPs use) or `DT_IOP_LENS_METHOD_EMBEDDED_METADATA` (value 0).
   - `modify_flags: DT_IOP_LENS_MODFLAG_ALL`; set `focal`, `aperture`, `distance` from EXIF.
   - Get EXIF first: `exiftool -FocalLength -FNumber -LensModel <raw>`.
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
`{operation, params{} | blob_hex, enabled?}`.

## Reading the user's XMP sidecars (`<RAW>.xmp`)

Reference example: `~/scratch/IMGP3521.PEF.xmp`. Structure:

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
With MCP, reproduce as multiple `atrous` entries with `multi_priority` to simulate masked instances.

## Workflow

1. Read EXIF first (`exiftool <raw>`) for lens/WB/orientation values.
2. **Render a quick preview first** (`render` with `width` ~1600) to see the base look before tuning.
3. **Check every field name against `module_schema`** before passing `params`. Field names are not
   what you'd guess (e.g. exposure has no `highlight`).
4. Iterate with small `render` previews; use `image_stats` to measure mean/p99/clip counts when
   judging exposure or clipping objectively.
5. Finalize with `export` at **native resolution** — always pass explicit `width`/`height`
   (check native size via `exiftool -ImageSize`), or you silently get a 1024px preview.

## Pitfalls

- **Non-scalar modules reject `params`/`fields`** (arrays → error "pass a full blob_hex"). Known
  non-scalar: `colorbalance`, `channelmixerrgb`, `atrous`, `basecurve`, `tonecurve`, `colorzones`.
  Build the blob yourself from `module_schema`: plain little-endian C layout (params_size bytes).
  Easiest: python3 snippet writing floats/ints at the documented offsets, then pass `blob_hex`.
- `encode_params` only works for fully-scalar modules.
- `decode_params` inspects a blob (e.g. from `get_history` of a library image — useful for copying
  a known-good atrous preset blob out of a real library history).
- Enum fields accept symbolic names when passing `params` (e.g. `DT_AGX_SRGB`).
- **`export` always writes PNG** regardless of `out_path` extension. For jpg/tiff, export PNG then
  convert (PIL `Image.convert('RGB').save(jpg, quality=92)`).
- Base pipeline already includes rawprepare/demosaic/tone-mapper; don't re-add those.
- `render`/`export` take `input.path` (file) or `input.imgid` (library image).
  `disable_tone_mappers` strips filmicrgb for raw-linear measurement.

## Quick "natural" stack (all scalar, verified working)

```
[
  { operation: "exposure",       params: { exposure: 0.15 } },
  { operation: "agx",            params: { curve_contrast_around_pivot: 4, look_slope: 1.25, dynamic_range_scaling: 0.05, base_primaries: "DT_AGX_SRGB" } },
  { operation: "colorbalancergb",params: { saturation_global: 0.08, brilliance_shadows: 0.05, brilliance_highlights: -0.05 } },
  { operation: "sharpen",        params: { amount: 0.6 } }
]
```

Other handy scalar modules: `shadhi`, `temperature`, `highlights`, `denoiseprofile`, `vignette`,
`vibrance`, `velvia` (strength 0–100, sat boost), `basicadj` (brightness/contrast/saturation/vibrance).

Field names drift between darktable builds — always re-check `module_schema` before use.
