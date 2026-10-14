"""moviola: the plain CLI over the same core the MCP server exposes."""

from __future__ import annotations

import argparse
import json
import sys

from .convert import convert_media, slideshow_from_images
from .ffmpeg_tools import ConversionError, ffmpeg_version, locate_trio, probe_media
from .flash import flash_report
from .index_db import conversion_chains, index_stats, list_conversions
from .plugin_install import install_opencode_plugin
from .presets import list_presets


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", dest="db_path", default=None, help="index db path")
    parser.add_argument(
        "--ffmpeg-dir", default=None, help="directory holding ffmpeg/ffprobe/ffplay"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="moviola",
        description="Moviola Protocol: grey-preset media conversion with an indexed ledger.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    convert = sub.add_parser("convert", help="convert one video/image file")
    convert.add_argument("source")
    convert.add_argument("output")
    convert.add_argument(
        "--preset",
        default="standard",
        help="standard (A), intersect (B), torch (C), passthrough",
    )
    convert.add_argument("--fps", type=int, default=None)
    convert.add_argument(
        "--height", type=int, default=None, help="360 or 480 for torch"
    )
    convert.add_argument("--crf", type=int, default=23)
    convert.add_argument("--timeout", type=int, default=7200)
    _add_common(convert)

    slideshow = sub.add_parser("slideshow", help="images to a slideshow gif/mp4/webp")
    slideshow.add_argument("images", nargs="+")
    slideshow.add_argument("output")
    slideshow.add_argument("--preset", default="torch")
    slideshow.add_argument("--seconds", type=float, default=1.0, help="per image")
    slideshow.add_argument("--fps", type=int, default=None)
    slideshow.add_argument("--height", type=int, default=None)
    slideshow.add_argument("--timeout", type=int, default=7200)
    _add_common(slideshow)

    probe = sub.add_parser("probe", help="ffprobe facts for one file")
    probe.add_argument("path")
    _add_common(probe)

    sub.add_parser("presets", help="list presets with filter chains")

    doctor = sub.add_parser("doctor", help="locate the ffmpeg trio")
    _add_common(doctor)

    history = sub.add_parser("history", help="recent conversions from moviola.db")
    history.add_argument("--limit", type=int, default=50)
    history.add_argument("--preset", default=None)
    _add_common(history)

    stats = sub.add_parser("stats", help="per-preset totals from moviola.db")
    _add_common(stats)

    chains = sub.add_parser("chains", help="intertwined files (output became source)")
    _add_common(chains)

    plugin = sub.add_parser("install-plugin", help="install the OpenCode gif plugin")
    plugin.add_argument("--target", default=None, help="opencode config dir")
    plugin.add_argument("--format", choices=["mjs", "ts"], default="mjs")
    plugin.add_argument("--no-read-tool", action="store_true")
    plugin.add_argument("--force", action="store_true")

    flash = sub.add_parser("flash", help="flash on the presets (easter egg)")
    _add_common(flash)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "convert":
            _print(
                convert_media(
                    source=args.source,
                    output=args.output,
                    preset=args.preset,
                    fps=args.fps,
                    height=args.height,
                    crf=args.crf,
                    db_path=args.db_path,
                    ffmpeg_dir=args.ffmpeg_dir,
                    timeout_seconds=args.timeout,
                )
            )
        elif args.command == "slideshow":
            _print(
                slideshow_from_images(
                    images=args.images,
                    output=args.output,
                    preset=args.preset,
                    seconds_per_image=args.seconds,
                    fps=args.fps,
                    height=args.height,
                    db_path=args.db_path,
                    ffmpeg_dir=args.ffmpeg_dir,
                    timeout_seconds=args.timeout,
                )
            )
        elif args.command == "probe":
            trio = locate_trio(args.ffmpeg_dir)
            _print(probe_media(args.path, trio.ffprobe))
        elif args.command == "presets":
            _print(list_presets())
        elif args.command == "doctor":
            trio = locate_trio(args.ffmpeg_dir)
            facts = trio.describe()
            facts["ffmpeg_version"] = (
                ffmpeg_version(trio.ffmpeg) if trio.ffmpeg else None
            )
            _print(facts)
        elif args.command == "history":
            _print(
                list_conversions(
                    db_path=args.db_path, limit=args.limit, preset=args.preset
                )
            )
        elif args.command == "stats":
            _print(index_stats(db_path=args.db_path))
        elif args.command == "chains":
            _print(conversion_chains(db_path=args.db_path))
        elif args.command == "flash":
            print(flash_report(db_path=args.db_path))
        elif args.command == "install-plugin":
            _print(
                install_opencode_plugin(
                    target_dir=args.target,
                    plugin_format=args.format,
                    include_read_tool=not args.no_read_tool,
                    force=args.force,
                )
            )
    except (ConversionError, ValueError, FileNotFoundError) as err:
        print(f"moviola: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
