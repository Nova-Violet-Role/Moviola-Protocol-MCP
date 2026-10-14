# SPDX-License-Identifier: AGPL-3.0-or-later OR EUPL-1.2
# Copyright 2026 Saimonokuma.
"""Training backends for machines without an NVIDIA GPU.

One data layer (moviola grey frames), every serious AMD/agnostic
training stack behind it:

- **PyTorch on ROCm** - stock torch speaks HIP through the cuda API;
  the MoviolaFrameDataset needs no change at all. What stock torch
  does *not* ship are AMD-tuned attention and quantized-GEMM
  kernels, which is exactly the gap the next item fills.
- **AITER** (ROCm/aiter, AI Tensor Engine for ROCm) - AMD's operator
  library whose whole purpose is speed-ups stock PyTorch lacks:
  fused attention (`aiter.flash_attn_func`, `aiter.mha_fwd`) and
  a8w8 GEMM (`aiter.gemm_a8w8_CK`, `_bpreshuffle`, `_ASM`, with
  `aiter.pertoken_quant`). Op names here follow upstream
  `op_tests/test_mha.py` and `op_tests/test_gemm_a8w8.py`, read
  2026-10-14. The accelerated_* dispatchers below prefer AITER
  when it is importable and tensors live on a HIP device, and fall
  back to stock torch otherwise - same call site, measured choice.
- **JAX + MaxText** - frames convert to jax arrays (NCHW or NHWC);
  on ROCm, MaxText runs under the Primus JAX backend or the
  `rocm/jax-training:maxtext-*` images, with ROCm/jax-aiter
  bringing the same AITER kernels to JAX.
- **AMD Primus (datacenter)** - AMD-AGI/Primus trains across
  Megatron-LM, TorchTitan and JAX MaxText under one config;
  its diffusion/data side speaks Energon, i.e. WebDataset-style
  tar shards. export_datacenter_shards writes exactly that:
  numbered shards + manifest.json, ready to stream on a cluster.

Honesty clause: this development machine is Windows with an RDNA2
gfx1032 card, where ROCm does not run. Everything torch-free here
is tested; every GPU path is guarded, named, and documented with
its install line, and backend_report() says what this host can
and cannot do instead of implying otherwise.
"""

from __future__ import annotations

import importlib.metadata
import importlib.util
import io
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from .torch_data import GrayFrames, export_image_folder

INSTALL_LINES = {
    "pytorch_rocm": (
        "Linux/ROCm host: pip install torch torchvision "
        "--index-url https://download.pytorch.org/whl/rocm<version> "
        "(or the rocm/pytorch docker image)"
    ),
    "aiter": (
        "ROCm host: pip install amd-aiter  (source: ROCm/aiter; "
        "JAX side: ROCm/jax-aiter)"
    ),
    "jax_rocm": (
        "pip install -U 'jax[rocm]' on a ROCm host, or use the "
        "rocm/jax-training:maxtext-* images from AMD-AGI/Primus"
    ),
    "maxtext": (
        "google/maxtext upstream, or the Primus JAX MaxText backend "
        "(rocm/jax-training:maxtext-v26.8 image)"
    ),
    "primus": (
        'pip install "primus==26.8.0" --no-deps '
        "--extra-index-url https://amd-agi.github.io/Primus/simple/ "
        "(AMD-AGI/Primus; CLI: primus-cli)"
    ),
    "torchtitan": (
        "pytorch/torchtitan from source (Primus TorchTitan backend "
        "on ROCm); consumes the MoviolaFrameDataset and image folders"
    ),
    "megatron_lm": (
        "NVIDIA/Megatron-LM via the Primus Megatron backend on ROCm; "
        "multimodal data streams as Megatron-Energon (WebDataset) shards"
    ),
    "unsloth": (
        "pip install 'moviola-protocol-mcp[unsloth]' (unsloth-ai/unsloth); "
        "vision SFT consumes export_unsloth's train.jsonl + images"
    ),
    "arrayrecord": (
        "pip install 'moviola-protocol-mcp[maxtext]' (jax + array-record, "
        "the Grain input format MaxText reads)"
    ),
}


def _spec(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def _version(dist: str) -> str | None:
    try:
        return importlib.metadata.version(dist)
    except Exception:
        return None


def first_available_op(module: Any, names: list[str]):
    """First callable attribute present on a module, else None.

    AITER renames and grows ops between releases; dispatch probes
    the installed surface instead of assuming one spelling.
    """
    for name in names:
        op = getattr(module, name, None)
        if callable(op):
            return op
    return None


def _import_aiter():
    if not _spec("aiter"):
        raise RuntimeError(
            "aiter is not installed; on a ROCm host: " + INSTALL_LINES["aiter"]
        )
    import aiter

    return aiter


def _import_torch():
    if not _spec("torch"):
        raise RuntimeError(
            "torch is not installed; install the training extra: "
            "pip install 'moviola-protocol-mcp[torch]', or for AMD: "
            + INSTALL_LINES["pytorch_rocm"]
        )
    import torch

    return torch


def backend_report() -> dict:
    """What training stacks exist here, and what this host can run."""
    on_windows = sys.platform.startswith("win")
    torch_info: dict[str, Any] = {"installed": _spec("torch")}
    if torch_info["installed"]:
        torch = _import_torch()
        torch_info.update(
            version=getattr(torch, "__version__", None),
            hip_version=getattr(torch.version, "hip", None),
            cuda_version=getattr(torch.version, "cuda", None),
            cuda_available=bool(torch.cuda.is_available()),
            device_count=int(torch.cuda.device_count())
            if torch.cuda.is_available()
            else 0,
        )
    jax_info: dict[str, Any] = {"installed": _spec("jax")}
    if jax_info["installed"]:
        jax_info["version"] = _version("jax")
        try:
            import jax

            jax_info["devices"] = [str(d) for d in jax.devices()]
        except Exception as err:  # a broken jax install is a named fact
            jax_info["devices_error"] = str(err)
    return {
        "platform": sys.platform,
        "rocm_expected_here": not on_windows,
        "rocm_note": (
            "Windows host: ROCm/HIP does not run here (RDNA2 gfx1032 "
            "included); ROCm paths in this module target Linux/ROCm "
            "hosts and AMD Instinct datacenter parts."
            if on_windows
            else "Non-Windows host: ROCm may run if the stack is installed."
        ),
        "torch": torch_info,
        "jax": jax_info,
        "aiter": {"installed": _spec("aiter"), "version": _version("amd-aiter")},
        "jax_aiter": {"installed": _spec("jax_aiter") or _spec("jax-aiter")},
        "primus": {
            "installed": _spec("primus"),
            "cli": shutil.which("primus-cli"),
            "version": _version("primus"),
        },
        "maxtext": {
            "installed": _spec("MaxText") or _spec("maxtext"),
        },
        "frameworks": {
            "primus": {
                "installed": _spec("primus"),
                "cli": shutil.which("primus-cli"),
                "moviola_interop": (
                    "datacenter WebDataset/Energon shards "
                    "(export_datacenter_shards); backends below run under it"
                ),
            },
            "torchtitan": {
                "installed": _spec("torchtitan"),
                "moviola_interop": (
                    "MoviolaFrameDataset is a plain torch Dataset; "
                    "image-folder export for file-based pipelines"
                ),
            },
            "megatron_lm": {
                "installed": _spec("megatron"),
                "moviola_interop": (
                    "Megatron-Energon streams WebDataset tar shards - "
                    "export_webdataset / export_datacenter_shards output"
                ),
            },
            "maxtext": {
                "installed": _spec("MaxText") or _spec("maxtext"),
                "moviola_interop": (
                    "JAX arrays via to_jax_array; Grain reads export_arrayrecord shards"
                ),
            },
            "unsloth": {
                "installed": _spec("unsloth"),
                "moviola_interop": (
                    "export_unsloth writes vision-SFT train.jsonl "
                    "(messages + images) over Moviola frames"
                ),
            },
        },
        "moviola_formats": {
            "dataset": "MoviolaFrameDataset (torch, ROCm-transparent)",
            "arrays": "to_torch_batch / to_jax_array from GrayFrames",
            "image_folder": "torchvision ImageFolder layout",
            "webdataset": "tar shards (Energon/WebDataset-style interop)",
            "datacenter": "export_datacenter_shards + manifest.json",
            "arrayrecord": "export_arrayrecord (MaxText/Grain)",
            "unsloth": "export_unsloth (vision SFT JSONL + images)",
        },
        "install_lines": INSTALL_LINES,
    }


def to_torch_batch(frames: GrayFrames):
    """Stack all frames as one float tensor [N, 1, H, W] in 0..1."""
    torch = _import_torch()
    flat = torch.frombuffer(bytearray(frames.data), dtype=torch.uint8)
    batch = flat.reshape(frames.frames, 1, frames.height, frames.width)
    return batch.float() / 255.0


def to_jax_array(frames: GrayFrames, layout: str = "NCHW"):
    """All frames as one jax array, float32 in 0..1.

    layout NCHW mirrors the torch bridge; NHWC suits Flax/MaxText
    vision stacks. numpy arrives with jax wherever jax is installed.
    """
    if not _spec("jax"):
        raise RuntimeError(
            "jax is not installed; "
            + INSTALL_LINES["jax_rocm"]
            + " (CPU-only: pip install 'moviola-protocol-mcp[jax]')"
        )
    import jax.numpy as jnp
    import numpy as np

    array = np.frombuffer(frames.data, dtype=np.uint8).reshape(
        frames.frames, frames.height, frames.width, 1
    )
    out = jnp.asarray(array, dtype=jnp.float32) / 255.0
    if layout == "NCHW":
        out = jnp.transpose(out, (0, 3, 1, 2))
    elif layout != "NHWC":
        raise ValueError(f"layout must be NCHW or NHWC, got {layout!r}")
    return out


def _on_hip(tensor: Any) -> bool:
    device = getattr(tensor, "device", None)
    return device is not None and getattr(device, "type", "") == "cuda"


def accelerated_attention(q, k, v, causal: bool = False, backend: str = "auto"):
    """Attention with AITER kernels when present, stock torch otherwise.

    AITER path: aiter.flash_attn_func (upstream op_tests spelling),
    which returns (out, lse, ...); only out is returned here.
    Stock path: torch.nn.functional.scaled_dot_product_attention -
    correct everywhere, and the baseline AITER exists to beat.
    backend="aiter" refuses by name when AITER is absent instead
    of silently slowing down.
    """
    if backend not in {"auto", "aiter", "torch"}:
        raise ValueError(f"backend must be auto, aiter or torch, got {backend!r}")
    if backend == "aiter" or (backend == "auto" and _spec("aiter")):
        aiter = _import_aiter()
        if backend == "auto" and not _on_hip(q):
            pass  # CPU tensors: stock path below is the honest one
        else:
            op = first_available_op(aiter, ["flash_attn_func", "mha_fwd"])
            if op is None:
                raise RuntimeError(
                    "aiter is installed but exposes neither flash_attn_func "
                    "nor mha_fwd; check the aiter version against ROCm/aiter"
                )
            out = op(q, k, v, dropout_p=0.0, causal=causal)
            return out[0] if isinstance(out, (tuple, list)) else out
    torch = _import_torch()
    return torch.nn.functional.scaled_dot_product_attention(q, k, v, is_causal=causal)


def accelerated_gemm_int8(x, weight, bias=None, backend: str = "auto"):
    """a8w8 GEMM via AITER when present; float matmul otherwise.

    AITER path quantizes per-token (aiter.pertoken_quant) and runs
    the first available of gemm_a8w8_CK / _bpreshuffle / _ASM -
    the quantized kernels stock PyTorch does not ship for ROCm.
    The torch fallback is an unquantized reference matmul: same
    shapes in and out, deliberately not the fast path.
    """
    if backend not in {"auto", "aiter", "torch"}:
        raise ValueError(f"backend must be auto, aiter or torch, got {backend!r}")
    if backend == "aiter" or (backend == "auto" and _spec("aiter")):
        aiter = _import_aiter()
        if backend == "auto" and not _on_hip(x):
            pass
        else:
            op = first_available_op(
                aiter, ["gemm_a8w8_CK", "gemm_a8w8_bpreshuffle", "gemm_a8w8_ASM"]
            )
            quant = first_available_op(aiter, ["pertoken_quant", "per_tensor_quant"])
            if op is None or quant is None:
                raise RuntimeError(
                    "aiter is installed but the a8w8 GEMM surface "
                    "(gemm_a8w8_* / pertoken_quant) was not found; "
                    "check the aiter version against ROCm/aiter op_tests"
                )
            x_q, x_scale = quant(x)
            w_q, w_scale = quant(weight)
            return op(x_q, w_q, x_scale, w_scale, bias, x.dtype)
    torch = _import_torch()
    out = torch.matmul(x, weight.t() if weight.dim() == 2 else weight)
    if bias is not None:
        out = out + bias
    return out


def export_datacenter_shards(
    sources: "str | list[str]",
    out_dir: str,
    max_samples_per_shard: int = 1000,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """WebDataset/Energon-style shards + manifest, Primus-datacenter shape.

    Writes shard-NNNNNN.tar files (NNNNNNNNN.png + .json per
    sample) capped at max_samples_per_shard, plus manifest.json
    naming every shard, its samples and bytes - the layout Primus
    diffusion/Energon and WebDataset loaders stream on clusters,
    and that plain tarfile reads anywhere for verification.
    """
    if max_samples_per_shard <= 0:
        raise ValueError("max_samples_per_shard must be positive")
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    shards: list[dict] = []
    total = 0
    shard_index = 0
    tar: tarfile.TarFile | None = None
    in_shard = 0

    def open_shard() -> tarfile.TarFile:
        name = f"shard-{shard_index:06d}.tar"
        return tarfile.open(out_root / name, "w")

    with tempfile.TemporaryDirectory(prefix="moviola-dcshards-") as tmp:
        # Reuse the image-folder export per source, then pack in order.
        from .torch_data import _resolve_sources

        for source in _resolve_sources(sources):  # one decode pass per file
            export_image_folder(
                [source],
                tmp,
                image_format="png",
                height=height,
                dpi=dpi,
                reference_width_inches=reference_width_inches,
                ffmpeg_dir=ffmpeg_dir,
                timeout_seconds=timeout_seconds,
            )
            stem = Path(source).stem
            pngs = sorted((Path(tmp) / stem).glob("*.png"))
            for frame_index, png in enumerate(pngs):
                if tar is None:
                    tar = open_shard()
                    in_shard = 0
                key = f"{total:09d}"
                tar.add(png, arcname=f"{key}.png")
                meta = json.dumps(
                    {
                        "source": source,
                        "frame": frame_index,
                        "height": height,
                        "dpi": dpi,
                        "reference_width_inches": reference_width_inches,
                        "shard": shard_index,
                    }
                ).encode("utf-8")
                info = tarfile.TarInfo(f"{key}.json")
                info.size = len(meta)
                tar.addfile(info, io.BytesIO(meta))
                total += 1
                in_shard += 1
                if in_shard >= max_samples_per_shard:
                    tar.close()
                    path = out_root / f"shard-{shard_index:06d}.tar"
                    shards.append(
                        {
                            "file": path.name,
                            "samples": in_shard,
                            "bytes": path.stat().st_size,
                        }
                    )
                    shard_index += 1
                    tar = None
            # The next source reuses the temp class dir name only if
            # stems collide; frames were packed already, clear them.
            for png in pngs:
                png.unlink(missing_ok=True)
    if tar is not None:
        tar.close()
        path = out_root / f"shard-{shard_index:06d}.tar"
        shards.append(
            {"file": path.name, "samples": in_shard, "bytes": path.stat().st_size}
        )
    manifest = {
        "format": "webdataset-energon-style tar shards (png + json per sample)",
        "total_samples": total,
        "max_samples_per_shard": max_samples_per_shard,
        "height": height,
        "dpi": dpi,
        "reference_width_inches": reference_width_inches,
        "shards": shards,
        "consumers": [
            "AMD Primus (Energon/WebDataset loaders)",
            "webdataset (Python) streaming DataLoader",
            "plain tarfile, for verification anywhere",
        ],
    }
    (out_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def _frame_pngs(
    sources: "str | list[str]",
    tmp: str,
    height: int | None,
    dpi: float | None,
    reference_width_inches: float,
    ffmpeg_dir: str | None,
    timeout_seconds: int,
) -> list[tuple[str, int, Path]]:
    """(source, frame_index, png_path) for every frame, via one decode each."""
    from .torch_data import _resolve_sources

    found: list[tuple[str, int, Path]] = []
    for source in _resolve_sources(sources):
        stem = Path(source).stem
        class_dir = Path(tmp) / stem
        before = set(class_dir.glob("*.png")) if class_dir.exists() else set()
        export_image_folder(
            [source],
            tmp,
            image_format="png",
            height=height,
            dpi=dpi,
            reference_width_inches=reference_width_inches,
            ffmpeg_dir=ffmpeg_dir,
            timeout_seconds=timeout_seconds,
        )
        new_pngs = sorted(set(class_dir.glob("*.png")) - before)
        found.extend((source, i, png) for i, png in enumerate(new_pngs))
    return found


def export_arrayrecord(
    sources: "str | list[str]",
    out_path: str,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Export frames as an ArrayRecord file for MaxText/Grain pipelines.

    One record per frame (PNG bytes); a sidecar
    <out_path>.manifest.json lists source and frame per record so
    the shard stays falsifiable against the index it came from.
    """
    if not _spec("array_record"):
        raise RuntimeError(
            "array_record is not installed; install the MaxText extra: "
            "pip install 'moviola-protocol-mcp[maxtext]'"
        )
    from array_record.python.array_record_module import ArrayRecordWriter

    records: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="moviola-arrayrecord-") as tmp:
        pngs = _frame_pngs(
            sources,
            tmp,
            height,
            dpi,
            reference_width_inches,
            ffmpeg_dir,
            timeout_seconds,
        )
        writer = ArrayRecordWriter(out_path, "group_size:1")
        for source, frame_index, png in pngs:
            writer.write(png.read_bytes())
            records.append({"source": source, "frame": frame_index})
        writer.close()
    manifest = {
        "format": "arrayrecord (one PNG-bytes record per frame)",
        "samples": len(records),
        "height": height,
        "dpi": dpi,
        "reference_width_inches": reference_width_inches,
        "records": records,
        "consumers": ["MaxText Grain input pipeline", "grain ArrayRecordDataSource"],
    }
    Path(out_path + ".manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return {
        "samples": len(records),
        "out_path": out_path,
        "bytes": Path(out_path).stat().st_size,
    }


def export_unsloth(
    sources: "str | list[str]",
    out_dir: str,
    instruction: str = "Describe this Moviola grey frame.",
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """Export an Unsloth vision-SFT dataset: images + train.jsonl.

    Row shape follows the Unsloth/TRL vision convention: an
    "images" list of relative paths and "messages" with an image
    part, the instruction, and a deterministic assistant caption
    derived from the frame's own metadata (source, frame, stage) -
    a starting dataset that fine-tunes as-is and improves the
    moment real captions replace the derived ones.
    """
    out_root = Path(out_dir)
    images_root = out_root / "images"
    rows: list[str] = []
    with tempfile.TemporaryDirectory(prefix="moviola-unsloth-") as tmp:
        pngs = _frame_pngs(
            sources,
            tmp,
            height,
            dpi,
            reference_width_inches,
            ffmpeg_dir,
            timeout_seconds,
        )
        for n, (source, frame_index, png) in enumerate(pngs):
            dest = images_root / f"{n:06d}.png"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(png.read_bytes())
            rel = f"images/{dest.name}"
            stage = f"{height}p" if height else "native"
            caption = (
                f"Moviola frame {frame_index} of {Path(source).stem} "
                f"at {stage} grey rendering."
            )
            row = {
                "images": [rel],
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image"},
                            {"type": "text", "text": instruction},
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": [{"type": "text", "text": caption}],
                    },
                ],
                "source": source,
                "frame": frame_index,
            }
            rows.append(json.dumps(row, ensure_ascii=False))
    (out_root / "train.jsonl").write_text(
        "\n".join(rows) + ("\n" if rows else ""), encoding="utf-8", newline="\n"
    )
    return {
        "samples": len(rows),
        "out_dir": str(out_root),
        "jsonl": str(out_root / "train.jsonl"),
        "note": (
            "Load with Unsloth FastVisionModel + SFTTrainer, or any "
            "TRL vision SFT stack; replace derived captions for real tasks."
        ),
    }


TRAINING_FORMATS = (
    "image-folder",
    "webdataset",
    "datacenter-shards",
    "arrayrecord",
    "unsloth",
)


def export_training_data(
    sources: "str | list[str]",
    out: str,
    format: str = "webdataset",
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    max_samples_per_shard: int = 1000,
    instruction: str = "Describe this Moviola grey frame.",
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
) -> dict:
    """One dispatch for every training layout the backends consume.

    image-folder (TorchTitan/torchvision), webdataset (single tar),
    datacenter-shards (Primus/Energon, Megatron-LM multimodal),
    arrayrecord (MaxText/Grain), unsloth (vision SFT JSONL).
    """
    from .torch_data import export_image_folder as _folder
    from .torch_data import export_webdataset as _wds

    common: dict[str, Any] = dict(
        height=height,
        dpi=dpi,
        reference_width_inches=reference_width_inches,
        ffmpeg_dir=ffmpeg_dir,
        timeout_seconds=timeout_seconds,
    )
    if format == "image-folder":
        return {"format": format, **_folder(sources, out, **common)}
    if format == "webdataset":
        return {"format": format, **_wds(sources, out, **common)}
    if format == "datacenter-shards":
        return {
            "format": format,
            **export_datacenter_shards(
                sources, out, max_samples_per_shard=max_samples_per_shard, **common
            ),
        }
    if format == "arrayrecord":
        return {"format": format, **export_arrayrecord(sources, out, **common)}
    if format == "unsloth":
        return {
            "format": format,
            **export_unsloth(sources, out, instruction=instruction, **common),
        }
    raise ValueError(
        f"unknown training format {format!r}; known: {', '.join(TRAINING_FORMATS)}"
    )
