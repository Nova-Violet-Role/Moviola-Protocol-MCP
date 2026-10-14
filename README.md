# Moviola Protocol MCP

An MCP server and CLI that convert video and images to any other
video/image format through the **Moviola Protocol**: the grey rendering
of the 1940s telecinema cutting room, measured at the bench. Colour is
discarded, black is seated at true 0 (NTSC-J), borders and subtitles
are kept legible by edge relief, and the palette is cut to as few as
two levels. Files shrink by one to two orders of magnitude on
screen/text content, and every conversion is written to an
always-seeable SQLite index (`moviola.db`) so the dimension change
between intertwined files can be evaluated at any time.

## Presets

| Preset | Rendering | Doctor clip* | Bench tape** |
|---|---|---|---|
| `standard` (A) | NTSC-J seated 8-bit grey, greyedge, 8-colour palette, 10 fps (10-15 accepted) | 189,882 B | 154,362 B |
| `intersect` (B) | 1-bit: grey overcalculated around mid-grey so borders/subtitles/contours reproduce as black, thresholded to 2 levels | 29,968 B | 49,159 B |
| `torch` (C) | Intersect at 5 fps, resized to 360p (480p choosable, never upscales) | 14,920 B (360p) / 20,234 B (480p) | 32,653 B |
| `passthrough` | No Moviola filter; plain format conversion | container-dependent | container-dependent |

\* Doctor clip: 1100x640, 29.6 s, 230,093 B mp4 of animated screen
content. Byte rates: A 6,415 B/s, B 1,012 B/s, C 504 B/s. At those
rates a 1 h 50 m video lands near 42 MB (A), 6.7 MB (B) or 3.3 MB
(C) — the often-quoted sub-5 MB / sub-3 MB figures need near-static
content (slides, talking-head stills, terminal recordings) and
Preset C; per-frame cost on static frames measured ~100 B.
\** Bench tape: 706x264, 5 s, 569,469 B HEVC mp4 (the MOVIOLA-PROTOCOL
reference ladder tape; Standard reproduces its 166 KB canonical floor
within generation loss). Byte rates always depend on content: the
index records your own rates — believe those.

## Run it (UVX)

```bash
uvx moviola-protocol-mcp            # MCP server on stdio
uvx --from moviola-protocol-mcp moviola convert in.mp4 out.gif --preset torch
```

No install needed beyond `uv`. You also need ffmpeg: the server looks
in `MOVIOLA_FFMPEG_DIR`, then `FFMPEG_PATH`, then `C:\Hybrid\64bit`
(the house install), then `PATH`.

## MCP tools

- `convert_media` — any video/image to any video/image format, one preset
- `slideshow_from_images` — PNG/JPG set to a gif/mp4/webp slideshow
- `probe_media` — ffprobe facts: size, dimensions, fps, duration, codec
- `list_presets` — the preset table with exact filter chains
- `doctor` — where the ffmpeg/ffprobe/ffplay trio was found, versions
- `index_history` / `index_stats` / `index_chains` — read `moviola.db`:
  recent conversions, per-preset totals, and files intertwined by the
  protocol (an output that later became a source)
- `install_opencode_plugin` — copy the bundled gif-as-mp4 plugin into
  an OpenCode config so models receive GIFs as video

## CLI

```bash
moviola convert lecture.mp4 lecture.gif --preset standard --fps 12
moviola convert lecture.mp4 lecture-torch.gif --preset torch --height 480
moviola convert frames.gif frames.mp4 --preset passthrough
moviola slideshow slide1.png slide2.png deck.gif --preset torch --seconds 0.2
moviola probe lecture.mp4
moviola presets
moviola doctor
moviola history
moviola stats
moviola chains
moviola install-plugin --target ~/.config/opencode
```

Every command accepts `--db PATH` (default `./moviola.db` or
`MOVIOLA_DB`) and `--ffmpeg-dir PATH`.

## The OpenCode plugin

`src/moviola_protocol_mcp/plugin_data/` ships the gif-as-video plugin
in TypeScript and ECMAScript (`.mjs`) forms, plus the portable `read`
tool. Installed into OpenCode, GIF bytes ride to the model labeled
`video/mp4` (servers validate the mime allowlist but sniff content),
so motion survives on endpoints that refuse `image/gif`. Set
`OPENCODE_GIF_AS_VIDEO=0` to opt out. The `.mjs` form also works with
local models and any OpenCode version that loads plugins from
`.opencode/plugins/` or `~/.config/opencode/plugins/`.

## Register in an MCP client

```json
{
  "mcpServers": {
    "moviola": {
      "command": "uvx",
      "args": ["moviola-protocol-mcp"],
      "env": { "MOVIOLA_FFMPEG_DIR": "C:\\Hybrid\\64bit" }
    }
  }
}
```

## License

AGPL-3.0-or-later OR EUPL-1.2.
