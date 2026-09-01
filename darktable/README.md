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
darktable-mcp [--core <darktable core options...>]
```

Everything after `--core` is forwarded verbatim to `dt_init` (`--configdir`,
`--cachedir`, `--library`, `--conf k=v`, `-d <domain>`, ...). Injected defaults:

- `--library :memory:` — throwaway catalog; loose files imported ad-hoc by path.
- `--conf write_sidecar_files=never` — never touches `.xmp` sidecars.
- stdout carries only JSON-RPC (darktable logging goes to stderr).

**Catalog mode** — `--core --library /path/to/library.db` enables the library
tools (`list_images`, `get_history`, styles). darktable takes a PID lock on
`library.db`/`data.db`, so the GUI must **not** have that library open (or point
at a copy).

### Tools

| Group | Tools |
|---|---|
| Introspection | `list_modules`, `module_schema` (field name/type/offset/min/max/enum values + `doc_url`), `decode_params`, `encode_params` |
| Develop | `render` (→ PNG preview), `image_stats` (per-channel min/max/mean/p1/p50/p99/clip counts); both take `{input:{path\|imgid}, width?, height?, stack?, disable_tone_mappers?}` |
| Library | `list_images`, `get_history`, `list_styles`, `apply_style`, `save_style`, `import_style` |
| Export | `export` — **PNG only** (convert to jpg/tiff afterward) |

A `stack` entry: `{operation, params{} | blob_hex, multi_priority?, enabled?}` on
top of the base pipeline; renders happen on a throwaway duplicate (source never
modified). `disable_tone_mappers:true` switches off sigmoid/filmicrgb/basecurve so
an added tone mapper (e.g. `agx`) owns the tone curve.

### Limitations (from the upstream README)

- `export` writes PNG only for now.
- `decode_params` requires the blob to match the module's **current** param size
  (no legacy-param conversion yet) — blobs from older darktable versions may not decode.
- First render is slow (seconds) — keep the client timeout generous.
- Headless export uses an in-memory format module + plain cairo, not
  `dt_imageio_preview`.
- Cannot drive a live/open darktable GUI; it's a background worker.

Tool descriptions/schemas are editable at runtime in
`share/darktable/mcp-tools.json` (restart the server to apply; no rebuild).

## 4. Sources

- pi-mcp-extension package page: <https://pi.dev/packages/pi-mcp-extension> (install, mcp.json schema, /mcp commands)
- This machine's live config: `~/.pi/agent/mcp.json`
- darktable-mcp server docs: `src/mcp/README.md` in a darktable checkout (building, `--core` options, tool reference, limitations); upstream <https://github.com/darktable/darktable/blob/master/src/mcp/README.md>

## 5. Sanity check

```sh
/mcp                  # in a pi session: darktable should be configured
```

then ask: *"using darktable, render ~/scratch/IMGP3521.PEF and show it"* —
`mcp_darktable_render` should return a PNG. Development workflow and pitfalls
live in [SKILL.md](./SKILL.md).
