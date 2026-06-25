"""Load MCP tools using langchain-mcp-adapters with persistent sessions."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.config import get_config

from deerflow.config.extensions_config import ExtensionsConfig
from deerflow.mcp.client import build_servers_config
from deerflow.mcp.oauth import build_oauth_tool_interceptor, get_initial_oauth_headers
from deerflow.mcp.session_pool import get_session_pool
from deerflow.reflection import resolve_variable
from deerflow.tools.sync import make_sync_tool_wrapper
from deerflow.tools.types import Runtime

logger = logging.getLogger(__name__)

MCPDiagnostics = dict[str, dict[str, Any]]


def _extract_thread_id(runtime: Runtime | None) -> str:
    """Extract thread_id from the injected tool runtime or LangGraph config."""
    if runtime is not None:
        tid = runtime.context.get("thread_id") if runtime.context else None
        if tid is not None:
            return str(tid)
        config = runtime.config or {}
        tid = config.get("configurable", {}).get("thread_id")
        if tid is not None:
            return str(tid)

    try:
        tid = get_config().get("configurable", {}).get("thread_id")
        return str(tid) if tid is not None else "default"
    except RuntimeError:
        return "default"


def _convert_call_tool_result(call_tool_result: Any) -> Any:
    """Convert an MCP CallToolResult to the LangChain content/artifact format."""
    from langchain_core.messages import ToolMessage
    from langchain_core.messages.content import create_file_block, create_image_block, create_text_block
    from langchain_core.tools import ToolException
    from mcp.types import EmbeddedResource, ImageContent, ResourceLink, TextContent, TextResourceContents

    if isinstance(call_tool_result, ToolMessage):
        return call_tool_result, None

    try:
        from langgraph.types import Command

        if isinstance(call_tool_result, Command):
            return call_tool_result, None
    except ImportError:
        pass

    lc_content = []
    for item in call_tool_result.content:
        if isinstance(item, TextContent):
            lc_content.append(create_text_block(text=item.text))
        elif isinstance(item, ImageContent):
            lc_content.append(create_image_block(base64=item.data, mime_type=item.mimeType))
        elif isinstance(item, ResourceLink):
            mime = item.mimeType or None
            if mime and mime.startswith("image/"):
                lc_content.append(create_image_block(url=str(item.uri), mime_type=mime))
            else:
                lc_content.append(create_file_block(url=str(item.uri), mime_type=mime))
        elif isinstance(item, EmbeddedResource):
            from mcp.types import BlobResourceContents

            res = item.resource
            if isinstance(res, TextResourceContents):
                lc_content.append(create_text_block(text=res.text))
            elif isinstance(res, BlobResourceContents):
                mime = res.mimeType or None
                if mime and mime.startswith("image/"):
                    lc_content.append(create_image_block(base64=res.blob, mime_type=mime))
                else:
                    lc_content.append(create_file_block(base64=res.blob, mime_type=mime))
            else:
                lc_content.append(create_text_block(text=str(res)))
        else:
            lc_content.append(create_text_block(text=str(item)))

    if call_tool_result.isError:
        error_parts = [item["text"] for item in lc_content if isinstance(item, dict) and item.get("type") == "text"]
        raise ToolException("\n".join(error_parts) if error_parts else str(lc_content))

    artifact = None
    if call_tool_result.structuredContent is not None:
        artifact = {"structured_content": call_tool_result.structuredContent}

    return lc_content, artifact


def _make_session_pool_tool(
    tool: BaseTool,
    server_name: str,
    connection: dict[str, Any],
    tool_interceptors: list[Any] | None = None,
) -> BaseTool:
    """Wrap an MCP tool so it reuses a persistent session from the pool."""
    original_name = tool.name
    prefix = f"{server_name}_"
    if original_name.startswith(prefix):
        original_name = original_name[len(prefix) :]

    pool = get_session_pool()

    async def call_with_persistent_session(
        runtime: Runtime | None = None,
        **arguments: Any,
    ) -> Any:
        thread_id = _extract_thread_id(runtime)
        session = await pool.get_session(server_name, thread_id, connection)

        if tool_interceptors:
            from langchain_mcp_adapters.interceptors import MCPToolCallRequest

            async def base_handler(request: MCPToolCallRequest) -> Any:
                return await session.call_tool(request.name, request.args)

            handler = base_handler
            for interceptor in reversed(tool_interceptors):
                outer = handler

                async def wrapped(req: Any, _i: Any = interceptor, _h: Any = outer) -> Any:
                    return await _i(req, _h)

                handler = wrapped

            request = MCPToolCallRequest(
                name=original_name,
                args=arguments,
                server_name=server_name,
                runtime=runtime,
            )
            call_tool_result = await handler(request)
        else:
            call_tool_result = await session.call_tool(original_name, arguments)

        return _convert_call_tool_result(call_tool_result)

    return StructuredTool(
        name=tool.name,
        description=tool.description,
        args_schema=tool.args_schema,
        coroutine=call_with_persistent_session,
        response_format="content_and_artifact",
        metadata=tool.metadata,
    )


def _patch_sync_invocation(tools: list[BaseTool]) -> None:
    """Attach sync wrappers to async-only tools in-place."""
    for tool in tools:
        if getattr(tool, "func", None) is None and getattr(tool, "coroutine", None) is not None:
            tool.func = make_sync_tool_wrapper(tool.coroutine, tool.name)


def _find_tool_server(tool_name: str, server_names: list[str]) -> str | None:
    """Find the owning MCP server for a prefixed DeerFlow tool name."""
    for server_name in sorted(server_names, key=len, reverse=True):
        if tool_name.startswith(f"{server_name}_"):
            return server_name
    return None


def _format_exception(exc: Exception) -> str:
    message = str(exc).strip()
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _build_tool_interceptors(extensions_config: ExtensionsConfig) -> list[Any]:
    tool_interceptors: list[Any] = []
    oauth_interceptor = build_oauth_tool_interceptor(extensions_config)
    if oauth_interceptor is not None:
        tool_interceptors.append(oauth_interceptor)

    raw_interceptor_paths = (extensions_config.model_extra or {}).get("mcpInterceptors")
    if isinstance(raw_interceptor_paths, str):
        raw_interceptor_paths = [raw_interceptor_paths]
    elif not isinstance(raw_interceptor_paths, list):
        if raw_interceptor_paths is not None:
            logger.warning(f"mcpInterceptors must be a list of strings, got {type(raw_interceptor_paths).__name__}; skipping")
        raw_interceptor_paths = []

    for interceptor_path in raw_interceptor_paths:
        try:
            builder = resolve_variable(interceptor_path)
            interceptor = builder()
            if callable(interceptor):
                tool_interceptors.append(interceptor)
                logger.info(f"Loaded MCP interceptor: {interceptor_path}")
            elif interceptor is not None:
                logger.warning(f"Builder {interceptor_path} returned non-callable {type(interceptor).__name__}; skipping")
        except Exception as e:
            logger.warning(
                f"Failed to load MCP interceptor {interceptor_path}: {e}",
                exc_info=True,
            )

    return tool_interceptors


async def _connection_with_initial_oauth_header(
    extensions_config: ExtensionsConfig,
    server_name: str,
    connection: dict[str, Any],
) -> dict[str, Any]:
    """Return one server connection with initial OAuth headers injected when needed."""
    if connection.get("transport") not in ("sse", "http"):
        return connection

    enabled_servers = extensions_config.get_enabled_mcp_servers()
    server_config = enabled_servers.get(server_name)
    if server_config is None or server_config.oauth is None or not server_config.oauth.enabled:
        return connection

    scoped_config = ExtensionsConfig(
        mcp_servers={server_name: server_config},
        skills={},
    )
    initial_oauth_headers = await get_initial_oauth_headers(scoped_config)
    auth_header = initial_oauth_headers.get(server_name)
    if not auth_header:
        return connection

    connection = dict(connection)
    existing_headers = dict(connection.get("headers", {}))
    existing_headers["Authorization"] = auth_header
    connection["headers"] = existing_headers
    return connection


async def get_mcp_tools_with_diagnostics() -> tuple[list[BaseTool], MCPDiagnostics]:
    """Get MCP tools and per-server load diagnostics from enabled MCP servers."""
    try:
        from langchain_mcp_adapters.client import MultiServerMCPClient
    except ImportError:
        logger.warning("langchain-mcp-adapters not installed. Install it to enable MCP tools: pip install langchain-mcp-adapters")
        extensions_config = ExtensionsConfig.from_file()
        return [], {
            name: {
                "status": "error",
                "tool_count": 0,
                "error": "langchain-mcp-adapters is not installed",
            }
            for name in extensions_config.get_enabled_mcp_servers()
        }

    extensions_config = ExtensionsConfig.from_file()
    enabled_server_names = list(extensions_config.get_enabled_mcp_servers())
    diagnostics: MCPDiagnostics = {}

    try:
        servers_config = build_servers_config(extensions_config)
    except Exception as e:
        logger.error(f"Failed to build MCP server config: {e}", exc_info=True)
        return [], {
            name: {
                "status": "error",
                "tool_count": 0,
                "error": _format_exception(e),
            }
            for name in enabled_server_names
        }

    if not servers_config:
        logger.info("No enabled MCP servers configured")
        for server_name in enabled_server_names:
            diagnostics[server_name] = {
                "status": "error",
                "tool_count": 0,
                "error": "Server is enabled but its MCP connection config could not be built",
            }
        return [], diagnostics

    try:
        tool_interceptors = _build_tool_interceptors(extensions_config)
    except Exception as e:
        logger.warning(f"Failed to build MCP tool interceptors: {e}", exc_info=True)
        tool_interceptors = []

    logger.info(f"Initializing MCP tools from {len(servers_config)} server(s)")
    all_tools: list[BaseTool] = []

    for server_name, base_connection in servers_config.items():
        try:
            connection = await _connection_with_initial_oauth_header(extensions_config, server_name, base_connection)
            client = MultiServerMCPClient(
                {server_name: connection},
                tool_interceptors=tool_interceptors,
                tool_name_prefix=True,
            )
            tools = await client.get_tools()
        except Exception as e:
            logger.error(f"Failed to load MCP server '{server_name}': {e}", exc_info=True)
            diagnostics[server_name] = {
                "status": "error",
                "tool_count": 0,
                "error": _format_exception(e),
            }
            continue

        wrapped_tools: list[BaseTool] = []
        for tool in tools:
            if _find_tool_server(tool.name, [server_name]):
                wrapped_tools.append(_make_session_pool_tool(tool, server_name, connection, tool_interceptors))
            else:
                wrapped_tools.append(tool)

        _patch_sync_invocation(wrapped_tools)

        all_tools.extend(wrapped_tools)
        diagnostics[server_name] = {
            "status": "loaded",
            "tool_count": len(wrapped_tools),
            "error": None,
        }
        logger.info(f"Loaded {len(wrapped_tools)} MCP tool(s) from server '{server_name}'")

    for server_name in enabled_server_names:
        if server_name not in diagnostics and server_name not in servers_config:
            diagnostics[server_name] = {
                "status": "error",
                "tool_count": 0,
                "error": "Server is enabled but its MCP connection config could not be built",
            }

    logger.info(f"Successfully loaded {len(all_tools)} tool(s) from MCP servers")
    return all_tools, diagnostics


async def get_mcp_tools() -> list[BaseTool]:
    """Get all tools from enabled MCP servers."""
    tools, _diagnostics = await get_mcp_tools_with_diagnostics()
    return tools
