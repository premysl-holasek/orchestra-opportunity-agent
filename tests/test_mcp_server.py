"""Tests for the MCP server's exposed tools."""
from __future__ import annotations

import asyncio

from app.mcp_server import mcp


def test_mcp_server_registers_expected_tools():
    tools = asyncio.run(mcp.list_tools())

    assert {tool.name for tool in tools} == {
        "search_opportunities",
        "get_opportunity",
        "weekly_report",
    }