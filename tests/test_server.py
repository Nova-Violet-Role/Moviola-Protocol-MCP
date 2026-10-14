"""The MCP server, verified through a real stdio client session."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "convert_media",
    "slideshow_from_images",
    "probe_media",
    "list_presets",
    "doctor",
    "index_history",
    "index_stats",
    "index_chains",
    "install_opencode_plugin",
    "training_backends",
    "export_training_data",
}


async def _session() -> tuple[set[str], list]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "moviola_protocol_mcp.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            presets = await session.call_tool("list_presets", {})
            return names, list(presets.content)


def test_the_mcp_server_lists_eleven_tools_and_answers_list_presets() -> None:
    names, content = asyncio.run(_session())
    assert names == EXPECTED_TOOLS
    assert content, "list_presets returned no content"


async def _progress_session(
    tmp_path: Path,
) -> tuple[list[tuple[float, float | None, str | None]], list]:
    progress_events: list[tuple[float, float | None, str | None]] = []
    logs: list = []

    async def on_progress(
        progress: float, total: float | None, message: str | None = None
    ) -> None:
        progress_events.append((progress, total, message))

    async def on_log(params) -> None:  # noqa: ANN001 - SDK notification object
        logs.append(params)

    source = (
        Path(__file__).resolve().parents[1] / "docs" / "presets" / "doctor-torch.gif"
    )
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "moviola_protocol_mcp.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, logging_callback=on_log) as session:
            await session.initialize()
            result = await session.call_tool(
                "convert_media",
                {
                    "source": str(source),
                    "output": str(tmp_path / "progress-intersect.gif"),
                    "preset": "intersect",
                    "db_path": str(tmp_path / "progress.db"),
                },
                progress_callback=on_progress,
            )
            assert not result.isError, result.content
            assert (tmp_path / "progress-intersect.gif").exists()
    return progress_events, logs


def test_convert_media_reports_progress_during_real_mcp_session(
    tmp_path: Path,
) -> None:
    progress_events, logs = asyncio.run(_progress_session(tmp_path))
    assert progress_events, "convert_media sent no progress notifications"
    assert progress_events[0][0] == 0.0
    assert progress_events[-1][0] == 1.0
    assert logs, "convert_media sent no log notifications"


def test_install_plugin_writes_mjs_plugin_and_read_tool(tmp_path: Path) -> None:
    from moviola_protocol_mcp.plugin_install import install_opencode_plugin

    result = install_opencode_plugin(target_dir=str(tmp_path))
    plugin = tmp_path / "plugins" / "moviola-gif-as-mp4.mjs"
    read_tool = tmp_path / "tools" / "read.ts"
    assert plugin.exists() and read_tool.exists()
    assert str(plugin) in result["written"]
    assert "video/mp4" in plugin.read_text(encoding="utf-8")

    again = install_opencode_plugin(target_dir=str(tmp_path), plugin_format="ts")
    assert (tmp_path / "plugins" / "moviola-gif-as-mp4.ts").exists()
    assert again["skipped"] == []


def test_install_plugin_never_overwrites_a_different_read_tool(tmp_path: Path) -> None:
    from moviola_protocol_mcp.plugin_install import install_opencode_plugin

    tools = tmp_path / "tools"
    tools.mkdir(parents=True)
    (tools / "read.ts").write_text("// someone else's read tool\n", encoding="utf-8")

    result = install_opencode_plugin(target_dir=str(tmp_path))
    assert result["skipped"], "foreign read.ts must be skipped, not replaced"
    assert (tools / "read.ts").read_text(encoding="utf-8").startswith("// someone")
