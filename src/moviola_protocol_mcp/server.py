"""MCP server: the Moviola Protocol as eleven flat tools on stdio.

Architecture: traditional pattern. The operation surface is fixed
(convert, slideshow, probe, presets, doctor, three index reads,
plugin install, training backends, training export), so each
operation is its own tool with a declared schema instead of an
on-demand discovery layer. All conversion logic lives in
convert.py and the training bridges; this module adapts arguments.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from mcp.server.fastmcp import Context, FastMCP

from .convert import convert_media as _convert_media
from .convert import slideshow_from_images as _slideshow_from_images
from .ffmpeg_tools import ffmpeg_version, locate_trio, probe_media as _probe_media
from .index_db import conversion_chains, index_stats, list_conversions
from .plugin_install import install_opencode_plugin as _install_opencode_plugin
from .presets import list_presets as _list_presets
from .training_backends import backend_report as _backend_report
from .training_backends import export_training_data as _export_training_data

mcp = FastMCP("moviola-protocol-mcp")


async def _run_with_heartbeat(
    ctx: Context | None,
    label: str,
    func: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Run a long synchronous core call while narrating it.

    A conversion that stays silent for minutes looks dead to any
    client with a ceiling, and the client reports failure for work
    that succeeded (measured: a 2-second encode timed out client-side
    after minutes of silence). The heartbeat reports staged progress
    every few seconds so the call stays visibly alive; it never
    changes what the core computes. Progress reporting failures are
    swallowed - a mute client must never break a conversion.
    """
    if ctx is None:
        return func(*args, **kwargs)
    worker = asyncio.to_thread(func, *args, **kwargs)
    worker_task = asyncio.ensure_future(worker)
    ticks = 0
    try:
        await ctx.info(f"{label}: started")
        try:
            await ctx.report_progress(0.0, 1.0, f"{label}: started")
        except Exception:
            pass
        while not worker_task.done():
            try:
                await asyncio.wait_for(asyncio.shield(worker_task), timeout=5.0)
            except asyncio.TimeoutError:
                ticks += 1
                fraction = min(0.05 + 0.1 * ticks, 0.9)
                try:
                    await ctx.report_progress(fraction, 1.0, f"{label}: still working")
                except Exception:
                    pass
        result = await worker_task
        try:
            await ctx.report_progress(1.0, 1.0, f"{label}: done")
            await ctx.info(f"{label}: done")
        except Exception:
            pass
        return result
    finally:
        if not worker_task.done():
            worker_task.cancel()


@mcp.tool()
async def convert_media(
    source: str,
    output: str,
    preset: str = "standard",
    fps: int | None = None,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    crf: int = 23,
    db_path: str | None = None,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
    verbose: bool = False,
    ctx: Context | None = None,
) -> dict:
    """Convert any video/image file to the output path's format.

    The preset shapes the pixels (standard = NTSC-J 8-bit grey 8
    colours, intersect = 1-bit overcalc grey, torch = intersect at
    5 fps and 360p/480p, canine = Canine Logic Moviola Tessersect
    90 fps 120p-cell 4x4 collage, passthrough = no Moviola filter,
    which for gif to mp4 reproduces the OpenCode plugin transcode).
    The output extension chooses the container: gif, mp4, webm, webp,
    png, jpg and anything else ffmpeg muxes. Resolution may be chosen
    in lines (height, the p metric) or in DPI at a named reference
    width (pixels = dpi * inches), never both. Every conversion is
    recorded in moviola.db; the result carries before/after bytes
    and the ratio.
    """
    return await _run_with_heartbeat(
        ctx,
        f"convert {preset}",
        _convert_media,
        source=source,
        output=output,
        preset=preset,
        fps=fps,
        height=height,
        dpi=dpi,
        reference_width_inches=reference_width_inches,
        crf=crf,
        db_path=db_path,
        ffmpeg_dir=ffmpeg_dir,
        timeout_seconds=timeout_seconds,
        verbose=verbose,
    )


@mcp.tool()
async def slideshow_from_images(
    images: list[str],
    output: str,
    preset: str = "torch",
    seconds_per_image: float = 1.0,
    fps: int | None = None,
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    db_path: str | None = None,
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
    verbose: bool = False,
    ctx: Context | None = None,
) -> dict:
    """Build a slideshow (gif/mp4/webp) from PNG/JPG images, in order.

    With preset torch and seconds_per_image 0.2 the output is the
    pre-training form: five 1-bit grey frames per second, legible
    for text- and code-rich images at a few hundred bytes a frame.
    """
    return await _run_with_heartbeat(
        ctx,
        f"slideshow {preset}",
        _slideshow_from_images,
        images=images,
        output=output,
        preset=preset,
        seconds_per_image=seconds_per_image,
        fps=fps,
        height=height,
        dpi=dpi,
        reference_width_inches=reference_width_inches,
        db_path=db_path,
        ffmpeg_dir=ffmpeg_dir,
        timeout_seconds=timeout_seconds,
        verbose=verbose,
    )


@mcp.tool()
def probe_media(path: str, ffmpeg_dir: str | None = None) -> dict:
    """Probe one media file: bytes, dimensions, fps, duration, codec."""
    trio = locate_trio(ffmpeg_dir)
    return _probe_media(path, trio.ffprobe)


@mcp.tool()
def list_presets() -> list[dict]:
    """List the Moviola presets with their exact ffmpeg filter chains."""
    return _list_presets()


@mcp.tool()
def doctor(ffmpeg_dir: str | None = None) -> dict:
    """Report where the ffmpeg/ffprobe/ffplay trio was found + version."""
    trio = locate_trio(ffmpeg_dir)
    facts = trio.describe()
    facts["ffmpeg_version"] = ffmpeg_version(trio.ffmpeg) if trio.ffmpeg else None
    return facts


@mcp.tool()
def index_history(
    limit: int = 50,
    preset: str | None = None,
    db_path: str | None = None,
) -> list[dict]:
    """Recent conversions from moviola.db, newest first, sizes included."""
    return list_conversions(db_path=db_path, limit=limit, preset=preset)


@mcp.tool(name="index_stats")
def index_stats_tool(db_path: str | None = None) -> dict:
    """Per-preset totals from moviola.db: counts, bytes in/out, mean ratio."""
    return index_stats(db_path=db_path)


@mcp.tool()
def index_chains(db_path: str | None = None) -> list[dict]:
    """Files intertwined by the protocol: an output that became a source."""
    return conversion_chains(db_path=db_path)


@mcp.tool()
def install_opencode_plugin(
    target_dir: str | None = None,
    plugin_format: str = "mjs",
    include_read_tool: bool = True,
    force: bool = False,
) -> dict:
    """Install the bundled gif-as-mp4 OpenCode plugin (.mjs or .ts).

    Copies the plugin into <target>/plugins and, unless disabled,
    the portable read tool into <target>/tools/read.ts, so GIFs
    ride to models labeled video/mp4 and motion survives.
    """
    return _install_opencode_plugin(
        target_dir=target_dir,
        plugin_format=plugin_format,
        include_read_tool=include_read_tool,
        force=force,
    )


@mcp.tool()
def training_backends() -> dict:
    """Which training stacks exist here: torch/ROCm, AITER, JAX, Primus,
    TorchTitan, Megatron-LM, MaxText, Unsloth - installed or not, with
    install lines, and what this host honestly cannot run (ROCm on
    Windows/RDNA2). Detection only; nothing is downloaded."""
    return _backend_report()


@mcp.tool()
async def export_training_data(
    sources: list[str],
    out: str,
    format: str = "webdataset",
    height: int | None = None,
    dpi: float | None = None,
    reference_width_inches: float = 10.0,
    max_samples_per_shard: int = 1000,
    instruction: str = "Describe this Moviola grey frame.",
    ffmpeg_dir: str | None = None,
    timeout_seconds: int = 7200,
    ctx: Context | None = None,
) -> dict:
    """Export Moviola frames as a training dataset in one of five layouts.

    image-folder (TorchTitan/torchvision), webdataset (single tar),
    datacenter-shards (AMD Primus / Megatron-Energon style shards +
    manifest), arrayrecord (JAX MaxText/Grain), unsloth (vision SFT
    train.jsonl + images). Sources are any media files or folders;
    height chooses a ladder stage in lines, dpi in pixels-per-inch
    at the reference width.
    """
    return await _run_with_heartbeat(
        ctx,
        f"export {format}",
        _export_training_data,
        sources=sources,
        out=out,
        format=format,
        height=height,
        dpi=dpi,
        reference_width_inches=reference_width_inches,
        max_samples_per_shard=max_samples_per_shard,
        instruction=instruction,
        ffmpeg_dir=ffmpeg_dir,
        timeout_seconds=timeout_seconds,
    )


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
