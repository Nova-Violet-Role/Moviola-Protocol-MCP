"""The three Moviola presets as ffmpeg filter chains.

Every number here is measured, not typed from the vision prose:

- Standard chain is the canonical bench pipeline (MOVIOLA-PROTOCOL.md):
  fps, NTSC-J range seating, 8-bit grey, greyedge relief, two-pass
  palette with dither off. Eight colours is the measured floor when
  black is seated at true 0 by the NTSC-J step.
- Intersect adds the overcalc curve (luma stretched around mid-grey so
  faint borders, subtitles and contours cross the threshold) and a
  one-bit threshold. On the reference clip the two surviving levels
  measure {0, 192}: grey ink on black.
- Torch is Intersect at 5 fps with a 360p/480p resize.
"""

from __future__ import annotations

from dataclasses import dataclass

NTSC_J_SEAT = "in_range=limited:out_range=full"
OVERCALC_CURVE = "0/0 0.30/0.02 0.5/0.5 0.70/0.98 1/1"
ONE_BIT_THRESHOLD = "if(gt(val,128),255,0)"


def _scale(height: int | None) -> str:
    if height:
        # Never upscale: a 264-line tape stays 264 under Torch.
        return f"scale=-2:'min({height},ih)':{NTSC_J_SEAT}"
    return f"scale={NTSC_J_SEAT}"


@dataclass(frozen=True)
class Preset:
    """One named Moviola rendering: a filter chain plus palette discipline."""

    name: str
    title: str
    summary: str
    default_fps: int
    palette_colors: int | None
    default_height: int | None
    one_bit: bool
    collage: bool = False

    def filter_chain(
        self,
        fps: int | None = None,
        height: int | None = None,
        include_fps: bool = True,
    ) -> str:
        """Return the pre-palette filter chain for this preset."""
        if self.name == "passthrough":
            return ""
        chosen_fps = fps or self.default_fps
        chosen_height = height or self.default_height
        stages: list[str] = []
        if include_fps:
            stages.append(f"fps={chosen_fps}")
        stages.append(_scale(chosen_height))
        stages.append("format=gray")
        stages.append("greyedge")
        if self.one_bit:
            stages.append("format=gray")
            stages.append(f"curves=all='{OVERCALC_CURVE}'")
            stages.append(f"lut=y='{ONE_BIT_THRESHOLD}'")
            stages.append("format=gray")
        if self.collage:
            stages.append("tile=4x4")
        return ",".join(stages)

    def describe(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "summary": self.summary,
            "default_fps": self.default_fps,
            "palette_colors": self.palette_colors,
            "default_height": self.default_height,
            "one_bit": self.one_bit,
            "collage": self.collage,
            "filter_chain": self.filter_chain(),
        }


PRESETS: dict[str, Preset] = {
    "standard": Preset(
        name="standard",
        title="Standard Moviola (NTSC-J, 8-bit grey)",
        summary=(
            "Preset A. NTSC-J seated 8-bit greyscale, greyedge relief, "
            "8-colour two-pass palette, dither off. 10 fps default, "
            "10-15 fps accepted."
        ),
        default_fps=10,
        palette_colors=8,
        default_height=None,
        one_bit=False,
    ),
    "intersect": Preset(
        name="intersect",
        title="Moviola Intersect Protocol (1-bit overcalc grey)",
        summary=(
            "Preset B. One-bit: greyedge relief, luma overcalculated "
            "around mid-grey so borders, subtitles and contours cross "
            "into black, then thresholded to two levels (measured "
            "{0, 192} on the reference clip: grey ink on black)."
        ),
        default_fps=10,
        palette_colors=2,
        default_height=None,
        one_bit=True,
    ),
    "torch": Preset(
        name="torch",
        title="Moviola Intersect Torch (1-bit, 5 fps, 360p-480p)",
        summary=(
            "Preset C. Intersect at 5 fps resized to 360p by default "
            "(480p choosable). For pre-training slideshows, documentaries "
            "and image sets rich in text or code."
        ),
        default_fps=5,
        palette_colors=2,
        default_height=360,
        one_bit=True,
    ),
    "canine": Preset(
        name="canine",
        title="Canine Logic Moviola Tessersect (90 fps, 120p cells, 4x4 collage)",
        summary=(
            "Preset D. The Tessersect: tesseract net x Chuck's Intersect. "
            "The stream is sampled at 90 fps in the canine flicker band "
            "(the paper's +90fps kinetic frequency), each instant is cut "
            "to a 120-line one-bit Grey-Ink cell (Intersect overcalc plus "
            "threshold), and sixteen consecutive cells are collaged into "
            "one 4x4 frame, oldest top-left to newest bottom-right - "
            "sixteen informational contents per frame, flashing past for "
            "absorption during training. Measured on the reference clip: "
            "65,525 B, 167 collages, 824x480. Cells hold state between "
            "source frames on sub-90fps sources, like a 1-bit sensor "
            "watching a slower world."
        ),
        default_fps=90,
        palette_colors=2,
        default_height=120,
        one_bit=True,
        collage=True,
    ),
    "passthrough": Preset(
        name="passthrough",
        title="Passthrough (format conversion, no Moviola grey)",
        summary=(
            "No Moviola filter. Plain format conversion; gif to mp4 "
            "uses the OpenCode plugin settings (libx264, crf 23, "
            "yuv420p, faststart, silent)."
        ),
        default_fps=10,
        palette_colors=256,
        default_height=None,
        one_bit=False,
    ),
}

ALIASES = {
    "a": "standard",
    "b": "intersect",
    "c": "torch",
    "d": "canine",
    "standard-moviola": "standard",
    "moviola": "standard",
    "intersect-torch": "torch",
    "tessersect": "canine",
    "tesseract": "canine",
    "canine-logic": "canine",
    "canine-tessersect": "canine",
    "none": "passthrough",
    "off": "passthrough",
}


def get_preset(name: str) -> Preset:
    """Resolve a preset name or alias; refuse unknown names by name."""
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in PRESETS:
        known = ", ".join(sorted(PRESETS) + sorted(ALIASES))
        raise ValueError(f"unknown preset {name!r}; known presets: {known}")
    return PRESETS[key]


def list_presets() -> list[dict]:
    return [preset.describe() for preset in PRESETS.values()]
