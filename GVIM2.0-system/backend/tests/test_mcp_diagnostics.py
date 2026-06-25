import asyncio
from unittest.mock import patch

from langchain_core.tools import StructuredTool

from deerflow.config.extensions_config import ExtensionsConfig, McpServerConfig
from deerflow.mcp.tools import get_mcp_tools_with_diagnostics


async def _noop_tool() -> str:
    return "ok"


def test_mcp_discovery_isolated_by_server_failure():
    """A broken MCP server should not prevent other servers from loading."""

    class FakeClient:
        def __init__(self, servers_config, **_kwargs):
            self.server_name = next(iter(servers_config))

        async def get_tools(self):
            if self.server_name == "broken":
                raise RuntimeError("server exploded")
            return [
                StructuredTool(
                    name=f"{self.server_name}_noop",
                    description="noop",
                    args_schema=None,
                    coroutine=_noop_tool,
                )
            ]

    config = ExtensionsConfig(
        mcp_servers={
            "healthy": McpServerConfig(enabled=True, type="stdio", command="echo"),
            "broken": McpServerConfig(enabled=True, type="stdio", command="echo"),
        },
        skills={},
    )

    with (
        patch("langchain_mcp_adapters.client.MultiServerMCPClient", FakeClient),
        patch("deerflow.config.extensions_config.ExtensionsConfig.from_file", return_value=config),
        patch(
            "deerflow.mcp.tools.build_servers_config",
            return_value={
                "healthy": {"transport": "stdio", "command": "echo", "args": []},
                "broken": {"transport": "stdio", "command": "echo", "args": []},
            },
        ),
        patch("deerflow.mcp.tools.build_oauth_tool_interceptor", return_value=None),
    ):
        tools, diagnostics = asyncio.run(get_mcp_tools_with_diagnostics())

    assert [tool.name for tool in tools] == ["healthy_noop"]
    assert diagnostics["healthy"]["status"] == "loaded"
    assert diagnostics["healthy"]["tool_count"] == 1
    assert diagnostics["broken"]["status"] == "error"
    assert diagnostics["broken"]["tool_count"] == 0
    assert "server exploded" in diagnostics["broken"]["error"]
