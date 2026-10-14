"""TorchPy bridge: ladder-compatible frames for PyTorch training."""

from __future__ import annotations

import importlib.util
import subprocess
import tarfile
from pathlib import Path

import pytest

from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.ffmpeg_tools import locate_trio, probe_media
from moviola_protocol_mcp.torch_data import (
    LADDER_STAGES,
    collect_media_files,
    export_image_folder,
    export_webdataset,
    extract_gray_frames,
    sources_from_index,
    unpack_collage,
)


@pytest.fixture(scope="module")
def trio():
    found = locate_trio()
    if found.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    return found


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory, trio) -> Path:
    dest = tmp_path_factory.mktemp("torchfx") / "clip.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=640x360:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(dest),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    return dest


def test_extracted_frames_match_the_probed_file(clip: Path, tmp_path: Path) -> None:
    gif = tmp_path / "intersect.gif"
    convert_media(
        str(clip), str(gif), preset="intersect", db_path=str(tmp_path / "m.db")
    )
    facts = probe_media(str(gif), locate_trio().ffprobe)
    frames = extract_gray_frames(str(gif))
    assert frames.width == facts["width"]
    assert frames.height == facts["height"]
    assert frames.frames == facts["frames"]
    assert len(frames.data) == frames.frames * frames.width * frames.height
    assert len(set(frames.data)) <= 4  # one-bit output: at most a few levels


def test_extraction_is_ladder_and_dpi_compatible(clip: Path, tmp_path: Path) -> None:
    gif = tmp_path / "std.gif"
    convert_media(
        str(clip), str(gif), preset="standard", db_path=str(tmp_path / "m.db")
    )
    at_stage = extract_gray_frames(str(gif), height=240)
    assert at_stage.height == 240
    assert 240 in LADDER_STAGES and 1080 in LADDER_STAGES and 120 in LADDER_STAGES
    by_dpi = extract_gray_frames(str(gif), dpi=32)  # 320 px wide over 10 in
    assert by_dpi.width == 320 and by_dpi.height == 180


def test_unpack_collage_reads_cells_in_time_order() -> None:
    # 8x8 frame, 2x2 cells of constant value 0..15 row-major (4x4 net of 2px cells)
    frame = bytearray()
    for row in range(8):
        for col in range(8):
            frame.append((row // 2) * 4 + (col // 2))
    cells = unpack_collage(bytes(frame), 8, 8, grid=4)
    assert len(cells) == 16
    assert [cell[0] for cell in cells] == list(range(16))
    assert all(len(cell) == 4 for cell in cells)


def test_index_sourcing_filters_by_any_of_the_five_renderings(
    clip: Path, tmp_path: Path
) -> None:
    db = str(tmp_path / "m.db")
    for preset, name in (
        ("standard", "a.gif"),
        ("intersect", "b.gif"),
        ("torch", "c.gif"),
        ("canine", "d.gif"),
    ):
        convert_media(str(clip), str(tmp_path / name), preset=preset, db_path=db)
    convert_media(
        str(tmp_path / "b.gif"),
        str(tmp_path / "e.mp4"),
        preset="passthrough",
        db_path=db,
    )
    assert [Path(p).name for p in sources_from_index(db, preset="intersect")] == [
        "b.gif"
    ]
    assert [Path(p).name for p in sources_from_index(db, preset="canine")] == ["d.gif"]
    assert len(sources_from_index(db)) == 5


def test_collect_media_files_covers_training_filetypes(tmp_path: Path) -> None:
    for name in ("a.gif", "b.mp4", "c.png", "d.jpg", "e.webm", "f.webp", "notes.txt"):
        (tmp_path / name).write_bytes(b"x")
    found = [Path(p).name for p in collect_media_files(str(tmp_path))]
    assert found == ["a.gif", "b.mp4", "c.png", "d.jpg", "e.webm", "f.webp"]


def test_exports_write_pytorch_ready_layouts(clip: Path, tmp_path: Path) -> None:
    gif = tmp_path / "torch.gif"
    convert_media(str(clip), str(gif), preset="torch", db_path=str(tmp_path / "m.db"))
    frames = probe_media(str(gif), locate_trio().ffprobe)["frames"]

    folder = export_image_folder([str(gif)], str(tmp_path / "folder"))
    assert folder["written"] == frames
    assert len(list((tmp_path / "folder").rglob("*.png"))) == frames

    tar_path = tmp_path / "shard.tar"
    shard = export_webdataset([str(gif)], str(tar_path))
    assert shard["samples"] == frames
    with tarfile.open(tar_path) as tar:
        names = tar.getnames()
    assert sum(n.endswith(".png") for n in names) == frames
    assert sum(n.endswith(".json") for n in names) == frames


def test_extraction_never_duplicates_frames_at_fractional_fps(
    clip: Path, tmp_path: Path
) -> None:
    # Canine collages carry a fractional rate (100/17); a vsync
    # resample on decode would duplicate instances into the dataset.
    gif = tmp_path / "canine.gif"
    convert_media(str(clip), str(gif), preset="canine", db_path=str(tmp_path / "m.db"))
    facts = probe_media(str(gif), locate_trio().ffprobe)
    frames = extract_gray_frames(str(gif))
    assert frames.frames == facts["frames"]

    doctor = (
        Path(__file__).resolve().parents[1] / "docs" / "presets" / "doctor-canine.gif"
    )
    if doctor.exists():
        probed = probe_media(str(doctor), locate_trio().ffprobe)
        extracted = extract_gray_frames(str(doctor))
        assert probed["frames"] == 167
        assert extracted.frames == probed["frames"]


def test_dataset_requires_torch_or_yields_real_tensors(
    clip: Path, tmp_path: Path
) -> None:
    from moviola_protocol_mcp.torch_data import MoviolaFrameDataset

    gif = tmp_path / "ds.gif"
    convert_media(
        str(clip), str(gif), preset="intersect", db_path=str(tmp_path / "m.db")
    )
    if importlib.util.find_spec("torch") is None:
        with pytest.raises(RuntimeError, match="torch is not installed"):
            MoviolaFrameDataset([str(gif)])
    else:  # pragma: no cover - torch present
        dataset = MoviolaFrameDataset([str(gif)], ladder_stage=240)
        assert len(dataset) > 0
        sample = dataset[0]
        assert tuple(sample.shape) == (1, 240, dataset[0].shape[2])
        assert float(sample.max()) <= 1.0
