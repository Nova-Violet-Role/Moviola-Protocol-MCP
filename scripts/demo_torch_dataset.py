# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""Demonstrate the TorchPy bridge over the ladder and the five renderings.

Torch-free path (always runs): per rendering and per ladder stage,
extract grey frames and print counts/shapes; unpack one Tessersect
collage into its 16 cells; export a small WebDataset shard and an
image folder to a temp directory and count what landed.

With torch installed (pip install moviola-protocol-mcp[torch]) the
same sources become a MoviolaFrameDataset and one DataLoader batch
shape is printed per rendering.

Run:  uv run python scripts/demo_torch_dataset.py [moviola.db]
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.torch_data import (
    LADDER_STAGES,
    export_image_folder,
    export_webdataset,
    extract_gray_frames,
    sources_from_index,
    unpack_collage,
)

RENDERINGS = ["standard", "intersect", "torch", "canine", "passthrough"]


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    tmp = Path(tempfile.mkdtemp(prefix="moviola-torchdemo-"))
    db = sys.argv[1] if len(sys.argv) > 1 else None

    demos: dict[str, Path] = {
        "standard": repo / "docs" / "presets" / "doctor-standard.gif",
        "intersect": repo / "docs" / "presets" / "doctor-intersect.gif",
        "torch": repo / "docs" / "presets" / "doctor-torch.gif",
        "canine": repo / "docs" / "presets" / "doctor-canine.gif",
    }
    # The fifth rendering, made on the spot: gif back to mp4, plugin parity.
    back = tmp / "doctor-passthrough.mp4"
    convert_media(
        str(demos["intersect"]),
        str(back),
        preset="passthrough",
        db_path=str(tmp / "demo.db"),
    )
    demos["passthrough"] = back

    print("== five renderings as training instances (ladder stage 240p) ==")
    for name in RENDERINGS:
        frames = extract_gray_frames(str(demos[name]), height=240)
        print(
            f"{name:12} {frames.frames:4} frames at {frames.width}x{frames.height}"
            f"  unique_levels={len(set(frames.data))}"
        )

    print("\n== ladder stages from one Torch file (DPI at 10in in brackets) ==")
    for stage in LADDER_STAGES:
        frames = extract_gray_frames(str(demos["torch"]), height=stage)
        dpi = frames.width / 10.0
        print(
            f"{stage:5}p -> {frames.frames:4} frames at "
            f"{frames.width}x{frames.height}  ({dpi:.0f} DPI at 10in)"
        )

    print("\n== Tessersect unpack: one collage becomes 16 instances ==")
    collage = extract_gray_frames(str(demos["canine"]))
    cells = unpack_collage(collage.frame(0), collage.width, collage.height)
    print(
        f"collage {collage.width}x{collage.height} -> {len(cells)} cells of "
        f"{collage.width // 4}x{collage.height // 4}; "
        f"{collage.frames} collages = {collage.frames * 16} instants"
    )

    print("\n== exports (PyTorch-ready layouts) ==")
    folder = export_image_folder(
        [str(demos["torch"])], str(tmp / "imagefolder"), height=240
    )
    print(f"image folder: {folder['written']} png under {folder['out_dir']}")
    shard = export_webdataset([str(demos["torch"])], str(tmp / "shard.tar"), height=240)
    print(f"webdataset: {shard['samples']} samples, {shard['bytes']} B tar")

    if db:
        print("\n== sources per rendering from the index ==")
        for name in RENDERINGS:
            print(f"{name:12} {len(sources_from_index(db, preset=name))} file(s)")

    if importlib.util.find_spec("torch") is not None:
        from torch.utils.data import DataLoader

        from moviola_protocol_mcp.torch_data import MoviolaFrameDataset

        print("\n== torch DataLoader batches ==")
        for name in RENDERINGS:
            dataset = MoviolaFrameDataset(
                [str(demos[name])],
                ladder_stage=240,
                unpack_collage=(name == "canine"),
            )
            batch = next(iter(DataLoader(dataset, batch_size=8)))
            print(f"{name:12} len={len(dataset):5} batch={tuple(batch.shape)}")
    else:
        print(
            "\ntorch not installed: pip install 'moviola-protocol-mcp[torch]'"
            " to run the DataLoader half of this demo."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
