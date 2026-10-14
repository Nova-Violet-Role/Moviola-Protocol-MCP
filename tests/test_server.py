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
