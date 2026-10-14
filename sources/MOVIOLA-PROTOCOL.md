# The Moviola Protocol

*Standard vision protocol for video files. Image moves, sound dies, evidence stays.*

> In the cutting rooms of the forties they cut monochrome stock, and under the
> stage a chronist spoke the parts the silent film could not carry. This protocol
> does the same: silent crafted evidence above, a measured voice below.

## Doctrine

1. **Visible evidence, inline.** A reader who gets a download link instead of an
   image has lost the only reason to choose GIF at all. The output must render
   inline wherever it will be read (chat, GitHub, docs).
2. **Film the product, never its error states.** What lands in the record is the
   real thing working (or failing), no mocks, no placeholders.
3. **Silent by construction.** GIF carries no audio track. The audio is not
   compressed — it is executed. Every mux report must read `audio:0KiB`.
4. **Budgets are alarms, not advice.** House budget: **2 MB** per GIF
   (GitHub stops rendering inline around 10 MB). A cut over budget fails the rite.
5. **Measure, then believe.** Every dial is cut and read from the mux report in
   under a minute. A null result kills a dial the same day — no lore without numbers.
6. **The chronist speaks below.** Every cut is logged with its full parameters
   and mux report. Silence about a miss is a failed cut.

## Pipeline

```
source  ->  fps  ->  range  ->  gray  ->  border  ->  palette (2-pass)  ->  loop 0
```

| Stage | House setting | Notes |
|---|---|---|
| `fps` | `10` (motion) | 15 only if smoothness is evidence. 10→15 costs little on UI footage. |
| range | NTSC-J seating: `scale=in_range=limited:out_range=full` | Seats black at true 0. Only matters when the source carries pedestal blacks; on PC captures expect a null result. |
| gray | `format=gray` | The monochrome tongue. Color is decoration until proven evidence. |
| border | `greyedge` (relief, readable) or `morpho=gradient` (outlines, smallest) | greyedge keeps light on letters; gradient keeps boundaries only. `morpho` needs a twin input: `split[m][s];[m][s]morpho=mode=gradient`. |
| palette | two-pass: `palettegen=max_colors=N` + `paletteuse=dither=none` | `N=16` default, `N=8` only with black seated at 0, `N=64` when color is evidence. Dither off, always — dither is noise wearing a costume. |
| audio | dropped by format | Verify `audio:0KiB` in every mux report. |
| grain | **forbidden by default** | Temporal sand multiplies frame diffs (~9x measured). A look, never a saving. |

## Reference ladder (5 s UI tape, 706x264, measured 2026-10-12)

| Cut | Size | Standing |
|---|---|---|
| 8 colors, NTSC-J seated, greyedge | 166 KB | **floor — canonical Moviola** |
| morphological gradient, 16 colors | 299 KB | smallest outlines; text is fill, outlines are not text |
| greyedge, 16 colors | 328 KB | relief reads truer; +30 KB over gradient buys legibility |
| direct, 16 colors | 347 KB | honest pixels, no border stage |
| HEVC-routed then GIF | 650 KB | lighter via generation loss; colors may drift (ffmpeg warns) — a courier, not evidence |
| house 64 colors | 746 KB | safe general purpose |
| 15 fps, house discipline | 852 KB | fps is garnish, palette is the meal |
| black & white | 986 KB | gray gradients compress worse flat than dithered small color |
| full 255 palette | 1620 KB | what no-discipline looks like |
| HEVC-AMF mp4 (not GIF) | 556 KB | smallest bytes, but a download link — outside the rite |

## Toolchain

- `ffmpeg` full build (9.x verified). No hardware encoder exists for GIF —
  AMF (AV1/H.264/HEVC, present on RDNA2) only enters when leaving GIF behind,
  which leaves the rite with it.
- Intermediate `.tape` scripts (Charm VHS format) stay the single source where
  terminal sessions are rendered; the `.tape` is script, the GIF is print.

## Anti-rules (learned at the bench)

- Never trust a preset without cutting it (B&W lost; grain lost 9x).
- Never let a stage go unlogged (a quiet cut is a broken cut).
- Never spend slots on pedestal mud (seat black first, then count colors).
- Never invent what the chronist must say (selections are never auto-picked;
  a missing pick is logged, not fabricated) — *carried over from the Mutable
  harness, where the same law governs facts.*
