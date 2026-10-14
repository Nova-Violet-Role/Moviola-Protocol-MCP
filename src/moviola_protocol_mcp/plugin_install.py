"""Install the bundled OpenCode gif-as-mp4 plugin from the wheel.

The wheel carries the plugin in ECMAScript (.mjs) and TypeScript
(.ts) forms plus the portable read tool, so a Python-only user can
install the OpenCode side without npm:

    moviola install-plugin                      # ~/.config/opencode
    moviola install-plugin --target .opencode   # project-local
    moviola install-plugin --format ts          # TypeScript form

An existing tools/read.ts with different content is never overwritten
unless force=True; the skipped file is named in the result.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def plugin_data_dir() -> Path:
    return Path(str(files("moviola_protocol_mcp") / "plugin_data"))


def default_opencode_config_dir() -> Path:
    return Path.home() / ".config" / "opencode"


def install_opencode_plugin(
    target_dir: str | None = None,
    plugin_format: str = "mjs",
    include_read_tool: bool = True,
    force: bool = False,
) -> dict:
    if plugin_format not in {"mjs", "ts"}:
        raise ValueError(f"plugin_format must be 'mjs' or 'ts', got {plugin_format!r}")
    target = Path(target_dir) if target_dir else default_opencode_config_dir()
    data = plugin_data_dir()
    written: list[str] = []
    skipped: list[str] = []

    plugin_name = f"moviola-gif-as-mp4.{plugin_format}"
    plugins_dir = target / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    plugin_dest = plugins_dir / plugin_name
    plugin_dest.write_bytes((data / plugin_name).read_bytes())
    written.append(str(plugin_dest))

    if include_read_tool:
        tools_dir = target / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)
        read_src = (data / "read.ts").read_bytes()
        read_dest = tools_dir / "read.ts"
        if read_dest.exists() and read_dest.read_bytes() != read_src and not force:
            skipped.append(
                f"{read_dest} (a different read tool exists; pass force to replace)"
            )
        else:
            read_dest.write_bytes(read_src)
            written.append(str(read_dest))

    return {
        "target_dir": str(target),
        "plugin_format": plugin_format,
        "written": written,
        "skipped": skipped,
        "npm_package_json": str(data / "package.json"),
        "note": (
            "Restart OpenCode to load the plugin. The same files "
            "publish to npm from plugin_data (package.json included), "
            "after which: npx moviola-protocol-mcp-opencode-plugin"
        ),
    }
