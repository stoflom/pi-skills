# darktable MCP — setup

Setup and server reference for the [darktable skill](./SKILL.md), which develops raw
images through darktable's real in-process pixelpipe via MCP tools.

## 1. Install the MCP client extension for Pi

*(source: [pi-mcp-extension package page](https://pi.dev/packages/pi-mcp-extension))*

Pi does not speak MCP natively — install the community extension:

```sh
pi install npm:pi-mcp-extension
```

(try without installing: `pi -e npm:pi-mcp-extension`). Package: `pi-mcp-extension`
on npm (https://pi.dev/packages/pi-mcp-extension). It bridges any MCP server
(stdio / streamable-http / sse) into Pi tools named `<prefix>_<server>_<tool>`.

## 2. Configure `~/.pi/agent/mcp.json`

*(sources: live config at `~/.pi/agent/mcp.json`; field semantics from the [pi-mcp-extension docs](https://pi.dev/packages/pi-mcp-extension))*

Global config (project-level `.pi/mcp.json` overrides per-server). This machine's
working config:

```json
{
  "settings": {
    "toolPrefix": "mcp",
    "requestTimeoutMs": 30000,
    "maxRetries": 5
  },
  "mcpServers": {
    "darktable": {
      "command": "/usr/local/bin/darktable-mcp",
      "transport": "stdio",
      "lifecycle": "lazy",
      "args": [
        "--core",
        "--configdir",  "/home/<user>/.config/darktable-mcp",
        "--cachedir",   "/home/<user>/.config/darktable-mcp/cache"
      ]
    }
  }
}
```

Notes:

- `lifecycle: "lazy"` — server starts on first tool use / `/mcp:start darktable`;
  use `"eager"` to auto-start each session.
- `requestTimeoutMs: 30000` matters: the **first render** of a raw runs demosaic +
  the full pipe and can take several seconds.
- Check with `/mcp` (status), `/mcp darktable` (details + stderr log),
  `/mcp:start darktable`, `/mcp:stop darktable`.
- Tools appear as `mcp_darktable_render`, `mcp_darktable_module_schema`, etc.

The dedicated `--configdir`/`--cachedir` keep the MCP server from contending with
the darktable GUI's `data.db` lock.

## 3. The darktable-mcp server

`darktable-mcp` is a headless MCP server that links `libdarktable` directly (a
sibling binary to `darktable-cli`) — real module introspection, in-process
pixelpipe, native styles/history. Full docs: `src/mcp/README.md` in the darktable
source tree (upstream: <https://github.com/darktable/darktable/blob/master/src/mcp/README.md>).

### Building

Built by default in darktable (CMake option `USE_MCP`, default `ON`; json-glib
is already a dependency):

```sh
cd <darktable source checkout>
./build.sh                                    # full build
# or just the target:
cmake -B build . && cmake --build build --target darktable-mcp -j
# binary: build/bin/darktable-mcp
```

### Running

```sh
darktable-mcp [--read-only] [--core <darktable core options...>]
```

`--read-only` is the server's own flag and goes **before** `--core`. Everything
after `--core` is forwarded verbatim to `dt_init` (`--configdir`,
`--cachedir`, `--library`, `--conf k=v`, `-d <domain>`, ...). When **neither**
`--library` nor `--configdir` is given, two defaults are injected together:

- `--library :memory:` — throwaway catalog; loose files imported ad-hoc by path.
- `--conf write_sidecar_files=never` — never touches `.xmp` sidecars.

Name either and neither is injected: a `--configdir` selects its own
`library.db`, so a config like the one above gives the server a
**persistent catalog of its own** in `~/.config/darktable-mcp/`, and its
darktablerc's `write_sidecar_files=on import` applies — committed edits and
first-render auto-applied history write `.xmp` files next to your raws.

stdout carries only JSON-RPC (darktable logging goes to stderr).

**`--read-only`** refuses every tool that would change the library — stacks,
`reset_history`, `apply_style`, `save_style`, `import_style`, `set_rating`,
`set_color_label`, `import_images` — while leaving reads and plain renders
untouched (it also suppresses the `.xmp` and clears the auto-applied history a
first render would materialize).

**Catalog mode** — `--core --library /path/to/library.db`, or just
`--core --configdir /path/to/dir`, enables the full library tool set
(`import_images`, `list_images`, `get_history`, styles, culling, ...). darktable
takes a PID lock on `library.db`/`data.db`, so a real catalog must run while
the GUI is **not** holding it (or point at a copy).

### Tools

| Group | Tools |
|---|---|
| Introspection | `list_modules`, `module_schema` (field name/type/offset/min/max/enum values + `doc_url`), `decode_params`, `encode_params` |
| Develop | `render` (→ PNG preview, default 1024 bounding box), `image_stats` (per-channel min/max/mean/p1/p50/p99/clip counts, default 512); both take `{input:{path\|imgid}, width?, height?, stack?, disable_tone_mappers?, history_end?}` |
| Library | `import_images`, `list_film_rolls`, `list_images`, `get_metadata` (camera/lens/EXIF), `get_history`, `reset_history`, `set_rating`, `set_color_label` |
| Styles | `list_styles`, `apply_style`, `save_style`, `import_style` |
| Config | `list_conf`, `get_conf` (read-only; restart with `--conf k=v` to change) |
| Export | `export_images` — jpeg/png/tiff/webp/jxl/avif/exr/pfm/ppm/j2k, quality, upscale, single or batch (`imgids[]`/`out_dir`); omit width/height for full resolution |

A `stack` entry: `{operation, params{} | blob_hex, multi_priority?, enabled?, before?, after?}`
on top of the base pipeline. **A stack on an `imgid` is written to the image's
history and its XMP sidecar — that's how an edit is committed; there is no
throwaway duplicate.** `input.path` for a file not in the catalog is a scratch
import (sidecar read, developed, rows removed — nothing persists), and a path
already in the catalog is refused (use the named `imgid`). `history_end` selects
how much existing history applies; combined with a stack it truncates the image's
history. `disable_tone_mappers:true` switches off whichever tone mapper
`plugins/darkroom/workflow` auto-applies so an added one (e.g. `agx`) owns the
tone curve — and is written to history like any other edit.

### Limitations & behaviour notes (from the upstream README)

- **Edits persist for `imgid` input** (stack + sidecar, no undo) — `reset_history`
  clears an image; `--read-only` or an in-memory library prevents writes.
- **First render of a never-developed image materializes the auto-applied
  workflow history** (~12 modules) into the image and syncs the sidecar —
  darktable's own default, but it touches your files; `--read-only` takes it back.
- `export_images` refuses `stack`/`disable_tone_mappers` — edit first, then export.
- `decode_params` requires the blob to match the module's **current** param size
  (no legacy-param conversion yet) — blobs from older darktable versions may not decode.
- First render is slow (seconds) — keep the client timeout generous.
- Headless export uses an in-memory format module + plain cairo, not
  `dt_imageio_preview`.
- A crash mid-request can strand a scratch row (shows up as an unexpected image).
- Cannot drive a live/open darktable GUI; it's a background worker.

Tool descriptions/schemas are editable at runtime in
`share/darktable/mcp_tools.json` (renamed from `mcp-tools.json`; restart the
server to apply; no rebuild).

## 4. Sources

- pi-mcp-extension package page: <https://pi.dev/packages/pi-mcp-extension> (install, mcp.json schema, /mcp commands)
- This machine's live config: `~/.pi/agent/mcp.json`
- darktable-mcp server docs: `src/mcp/README.md` in the darktable source tree (building, `--core` options, tool reference, limitations)

## 5. Sanity check

```sh
/mcp                  # in a pi session: darktable should be configured
```

then ask: *"using darktable, render ~/scratch/IMGP3521.PEF and show it"* —
`mcp_darktable_render` should return a PNG. Development workflow and pitfalls
live in [SKILL.md](./SKILL.md).
