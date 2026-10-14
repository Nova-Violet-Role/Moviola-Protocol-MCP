"""Training backends: ROCm/jax/AITER/Primus detection and datacenter shards."""

from __future__ import annotations

import importlib.util
import subprocess
import tarfile
from pathlib import Path

import pytest

from moviola_protocol_mcp.convert import convert_media
from moviola_protocol_mcp.ffmpeg_tools import locate_trio
from moviola_protocol_mcp.torch_data import extract_gray_frames
from moviola_protocol_mcp.training_backends import (
    accelerated_attention,
    accelerated_gemm_int8,
    backend_report,
    export_arrayrecord,
    export_datacenter_shards,
    export_training_data,
    export_unsloth,
    first_available_op,
    to_jax_array,
    to_torch_batch,
)


def test_backend_report_names_every_backend_and_this_machines_limits() -> None:
    report = backend_report()
    for key in ("torch", "jax", "aiter", "jax_aiter", "primus", "maxtext"):
        assert key in report, key
        assert "installed" in report[key]
    frameworks = report["frameworks"]
    for key in ("primus", "torchtitan", "megatron_lm", "maxtext", "unsloth"):
        assert key in frameworks, key
        assert "installed" in frameworks[key]
        assert frameworks[key]["moviola_interop"]
    # Measured on this machine: none of the training stacks are installed,
    # and Windows + RDNA2 gfx1032 cannot run ROCm here - said plainly.
    assert report["torch"]["installed"] is False
    assert report["jax"]["installed"] is False
    assert report["rocm_expected_here"] is False
    assert "Windows" in report["rocm_note"]
    lines = report["install_lines"]
    assert "amd-agi.github.io/Primus" in lines["primus"]
    assert "aiter" in lines["aiter"]
    assert "maxtext" in lines["maxtext"].lower()
    assert "unsloth" in lines["unsloth"].lower()
    assert "torchtitan" in lines["torchtitan"].lower()
    assert "megatron" in lines["megatron_lm"].lower()


def test_backend_arrays_refuse_by_name_when_the_stack_is_absent(
    tmp_path: Path,
) -> None:
    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    clip = tmp_path / "c.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=1:size=320x240:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    frames = extract_gray_frames(str(clip))

    if importlib.util.find_spec("torch") is None:
        with pytest.raises(RuntimeError, match="torch is not installed"):
            to_torch_batch(frames)
    if importlib.util.find_spec("jax") is None:
        with pytest.raises(RuntimeError, match="jax is not installed"):
            to_jax_array(frames)


def test_aiter_dispatch_picks_the_first_real_op_and_refuses_cleanly() -> None:
    class FakeAiter:
        gemm_a8w8_bpreshuffle = staticmethod(lambda *a: "bpreshuffle")
        flash_attn_func = staticmethod(lambda *a, **k: "flash")

    op = first_available_op(FakeAiter, ["gemm_a8w8_CK", "gemm_a8w8_bpreshuffle"])
    assert op() == "bpreshuffle"
    assert first_available_op(FakeAiter, ["nope"]) is None

    if importlib.util.find_spec("aiter") is None:
        with pytest.raises(RuntimeError, match="aiter is not installed"):
            accelerated_attention(None, None, None, backend="aiter")
        with pytest.raises(RuntimeError, match="aiter is not installed"):
            accelerated_gemm_int8(None, None, backend="aiter")


def test_datacenter_shards_split_at_the_sample_ceiling_with_a_manifest(
    tmp_path: Path,
) -> None:
    trio = locate_trio()
    if trio.ffmpeg is None:
        pytest.skip("ffmpeg not found")
    clip = tmp_path / "c.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=320x240:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    gif = tmp_path / "torch.gif"
    convert_media(
        str(clip), str(gif), preset="torch", db_path=str(tmp_path / "m.db")
    )  # 2 s at 5 fps = 10 frames

    out = tmp_path / "shards"
    manifest = export_datacenter_shards(
        [str(gif)], str(out), max_samples_per_shard=4, height=240
    )
    assert manifest["total_samples"] == 10
    assert [s["samples"] for s in manifest["shards"]] == [4, 4, 2]
    assert (out / "manifest.json").exists()
    first = out / manifest["shards"][0]["file"]
    with tarfile.open(first) as tar:
        names = tar.getnames()
    assert sum(n.endswith(".png") for n in names) == 4
    assert sum(n.endswith(".json") for n in names) == 4


def _small_gif(tmp_path: Path) -> Path:
    trio = locate_trio()
    clip = tmp_path / "u.mp4"
    run = subprocess.run(
        [
            str(trio.ffmpeg),
            "-y",
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=1:size=320x240:rate=10",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(clip),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr
    gif = tmp_path / "u.gif"
    convert_media(str(clip), str(gif), preset="torch", db_path=str(tmp_path / "m.db"))
    return gif


def test_unsloth_export_writes_vision_sft_jsonl_and_images(tmp_path: Path) -> None:
    if locate_trio().ffmpeg is None:
        pytest.skip("ffmpeg not found")
    import json as json_lib

    gif = _small_gif(tmp_path)  # 1 s at 5 fps = 5 frames
    out = tmp_path / "unsloth"
    result = export_unsloth(
        [str(gif)], str(out), instruction="Describe this Moviola frame.", height=240
    )
    assert result["samples"] == 5
    rows = [
        json_lib.loads(line)
        for line in (out / "train.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 5
    first = rows[0]
    assert first["messages"][0]["role"] == "user"
    assert {"type": "image"} in first["messages"][0]["content"]
    assert (out / first["images"][0]).exists()


def test_arrayrecord_and_unified_dispatch_refuse_or_route(tmp_path: Path) -> None:
    if locate_trio().ffmpeg is None:
        pytest.skip("ffmpeg not found")
    gif = _small_gif(tmp_path)
    if importlib.util.find_spec("array_record") is None:
        with pytest.raises(RuntimeError, match="array_record is not installed"):
            export_arrayrecord([str(gif)], str(tmp_path / "data.array_record"))

    routed = export_training_data(
        [str(gif)], str(tmp_path / "routed"), format="unsloth", height=240
    )
    assert routed["samples"] == 5
    with pytest.raises(Exception, match="unknown training format"):
        export_training_data([str(gif)], str(tmp_path / "x"), format="banana")
