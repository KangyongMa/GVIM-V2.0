import json
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from deerflow.config.extensions_config import ExtensionsConfig, get_extensions_config, reload_extensions_config

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["mcp"])


class McpOAuthConfigResponse(BaseModel):
    """OAuth configuration for an MCP server."""

    enabled: bool = Field(default=True, description="Whether OAuth token injection is enabled")
    token_url: str = Field(default="", description="OAuth token endpoint URL")
    grant_type: Literal["client_credentials", "refresh_token"] = Field(default="client_credentials", description="OAuth grant type")
    client_id: str | None = Field(default=None, description="OAuth client ID")
    client_secret: str | None = Field(default=None, description="OAuth client secret")
    refresh_token: str | None = Field(default=None, description="OAuth refresh token")
    scope: str | None = Field(default=None, description="OAuth scope")
    audience: str | None = Field(default=None, description="OAuth audience")
    token_field: str = Field(default="access_token", description="Token response field containing access token")
    token_type_field: str = Field(default="token_type", description="Token response field containing token type")
    expires_in_field: str = Field(default="expires_in", description="Token response field containing expires-in seconds")
    default_token_type: str = Field(default="Bearer", description="Default token type when response omits token_type")
    refresh_skew_seconds: int = Field(default=60, description="Refresh this many seconds before expiry")
    extra_token_params: dict[str, str] = Field(default_factory=dict, description="Additional form params sent to token endpoint")


class McpServerConfigResponse(BaseModel):
    """Response model for MCP server configuration."""

    enabled: bool = Field(default=True, description="Whether this MCP server is enabled")
    type: str = Field(default="stdio", description="Transport type: 'stdio', 'sse', or 'http'")
    command: str | None = Field(default=None, description="Command to execute to start the MCP server (for stdio type)")
    args: list[str] = Field(default_factory=list, description="Arguments to pass to the command (for stdio type)")
    env: dict[str, str] = Field(default_factory=dict, description="Environment variables for the MCP server")
    url: str | None = Field(default=None, description="URL of the MCP server (for sse or http type)")
    headers: dict[str, str] = Field(default_factory=dict, description="HTTP headers to send (for sse or http type)")
    oauth: McpOAuthConfigResponse | None = Field(default=None, description="OAuth configuration for MCP HTTP/SSE servers")
    description: str = Field(default="", description="Human-readable description of what this MCP server provides")


class McpConfigResponse(BaseModel):
    """Response model for MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        default_factory=dict,
        description="Map of MCP server name to configuration",
    )


class McpConfigUpdateRequest(BaseModel):
    """Request model for updating MCP configuration."""

    mcp_servers: dict[str, McpServerConfigResponse] = Field(
        ...,
        description="Map of MCP server name to configuration",
    )


class McpToolResponse(BaseModel):
    """Response model for an enabled MCP tool."""

    name: str = Field(description="Prefixed DeerFlow tool name")
    description: str = Field(default="", description="Tool description")
    args_schema: dict[str, Any] | None = Field(default=None, description="JSON schema for tool arguments")
    metadata: dict[str, Any] | None = Field(default=None, description="Tool metadata")


class McpToolsResponse(BaseModel):
    """Response model for enabled MCP tools."""

    tools: list[McpToolResponse]


class McpServerOverview(BaseModel):
    """Response model for one configured MCP server and its discovered tools."""

    name: str = Field(description="MCP server name")
    config: McpServerConfigResponse = Field(description="Masked MCP server configuration")
    status: str = Field(description="disabled, loaded, error, or unknown")
    tool_count: int = Field(default=0, description="Number of tools discovered from this MCP server")
    error: str | None = Field(default=None, description="Last discovery error for this MCP server")
    tools: list[McpToolResponse] = Field(default_factory=list, description="Tools discovered from this MCP server")


class McpOverviewResponse(BaseModel):
    """Response model for configured MCP servers plus native discovery diagnostics."""

    servers: list[McpServerOverview]
    total_tools: int = Field(default=0, description="Total number of loaded MCP tools")


class McpToolCallRequest(BaseModel):
    """Request model for invoking an enabled MCP tool through DeerFlow."""

    arguments: dict[str, Any] = Field(default_factory=dict)


_MASKED_VALUE = "***"


def _mask_server_config(server: McpServerConfigResponse) -> McpServerConfigResponse:
    """Return a copy of server config with sensitive fields masked.

    Masks env values, header values, and removes OAuth secrets so they
    are not exposed through the GET API endpoint.
    """
    masked_env = {k: _MASKED_VALUE for k in server.env}
    masked_headers = {k: _MASKED_VALUE for k in server.headers}
    masked_oauth = None
    if server.oauth is not None:
        masked_oauth = server.oauth.model_copy(
            update={
                "client_secret": None,
                "refresh_token": None,
            }
        )
    return server.model_copy(
        update={
            "env": masked_env,
            "headers": masked_headers,
            "oauth": masked_oauth,
        }
    )


def _merge_preserving_secrets(
    incoming: McpServerConfigResponse,
    existing: McpServerConfigResponse,
) -> McpServerConfigResponse:
    """Merge incoming config with existing, preserving secrets masked by GET.

    When the frontend toggles ``enabled`` it round-trips the full config:
    GET (masked) → modify enabled → PUT (masked values sent back).
    This function ensures masked values (``***``) are replaced with the
    real secrets from the current on-disk config.

    ``***`` is only accepted for keys that already exist in *existing*.
    New keys must provide a real value.

    For OAuth secrets, ``None`` means "preserve the existing stored value"
    so masked GET responses can be safely round-tripped. To explicitly clear
    a stored secret, clients may send an empty string, which is converted
    to ``None`` before persisting.
    """
    merged_env = {}
    for k, v in incoming.env.items():
        if v == _MASKED_VALUE:
            if k in existing.env:
                merged_env[k] = existing.env[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set env key '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_env[k] = v

    merged_headers = {}
    for k, v in incoming.headers.items():
        if v == _MASKED_VALUE:
            if k in existing.headers:
                merged_headers[k] = existing.headers[k]
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot set header '{k}' to masked value '***'; provide a real value.",
                )
        else:
            merged_headers[k] = v

    merged_oauth = incoming.oauth
    if incoming.oauth is not None and existing.oauth is not None:
        # None = preserve (masked round-trip), "" = explicitly clear, else = new value
        merged_client_secret = existing.oauth.client_secret if incoming.oauth.client_secret is None else (None if incoming.oauth.client_secret == "" else incoming.oauth.client_secret)
        merged_refresh_token = existing.oauth.refresh_token if incoming.oauth.refresh_token is None else (None if incoming.oauth.refresh_token == "" else incoming.oauth.refresh_token)
        merged_oauth = incoming.oauth.model_copy(
            update={
                "client_secret": merged_client_secret,
                "refresh_token": merged_refresh_token,
            }
        )
    return incoming.model_copy(
        update={
            "env": merged_env,
            "headers": merged_headers,
            "oauth": merged_oauth,
        }
    )


def _tool_schema(tool: Any) -> dict[str, Any] | None:
    schema = getattr(tool, "args_schema", None)
    if schema is None:
        return None
    if isinstance(schema, dict):
        return schema
    if hasattr(schema, "model_json_schema"):
        return schema.model_json_schema()
    if hasattr(schema, "schema"):
        return schema.schema()
    return None


def _tool_response(tool: Any) -> McpToolResponse:
    return McpToolResponse(
        name=tool.name,
        description=getattr(tool, "description", "") or "",
        args_schema=_tool_schema(tool),
        metadata=getattr(tool, "metadata", None),
    )


def _tool_server_name(tool_name: str, server_names: list[str]) -> str | None:
    for server_name in sorted(server_names, key=len, reverse=True):
        if tool_name.startswith(f"{server_name}_"):
            return server_name
    return None


def _normalise_tool_payload(response: Any) -> Any:
    """Convert LangChain MCP tool responses to JSON-safe payloads."""
    if isinstance(response, tuple) and response:
        response = response[0]
    if isinstance(response, list):
        text_parts: list[str] = []
        other_parts: list[Any] = []
        for item in response:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(str(item.get("text") or ""))
            elif hasattr(item, "text"):
                text_parts.append(str(item.text))
            else:
                other_parts.append(item)
        text = "\n".join(part for part in text_parts if part).strip()
        if text:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"success": True, "text": text, "content": other_parts}
        return {"success": True, "content": other_parts}
    return response


def _get_cached_mcp_tools() -> list[Any]:
    try:
        from deerflow.mcp.cache import get_cached_mcp_tools
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="MCP support is not installed") from exc
    return get_cached_mcp_tools()


def _get_cached_mcp_diagnostics() -> dict[str, dict]:
    try:
        from deerflow.mcp.cache import get_cached_mcp_diagnostics
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="MCP support is not installed") from exc
    return get_cached_mcp_diagnostics()


@router.get(
    "/mcp/overview",
    response_model=McpOverviewResponse,
    summary="Get MCP Server Overview",
    description="List configured MCP servers with native tool discovery status and grouped tools.",
)
async def get_mcp_overview() -> McpOverviewResponse:
    config = get_extensions_config()
    tools = _get_cached_mcp_tools()
    diagnostics = _get_cached_mcp_diagnostics()

    server_names = list(config.mcp_servers)
    tools_by_server: dict[str, list[Any]] = {name: [] for name in server_names}
    for tool in tools:
        server_name = _tool_server_name(tool.name, server_names)
        if server_name is not None:
            tools_by_server.setdefault(server_name, []).append(tool)

    servers: list[McpServerOverview] = []
    for name, server in config.mcp_servers.items():
        masked_config = _mask_server_config(McpServerConfigResponse(**server.model_dump()))
        server_tools = tools_by_server.get(name, [])
        diagnostic = diagnostics.get(name, {})

        if not server.enabled:
            status = "disabled"
            tool_count = 0
            error = None
            server_tools = []
        else:
            status = str(diagnostic.get("status") or "unknown")
            tool_count = int(diagnostic.get("tool_count", len(server_tools)) or 0)
            error = diagnostic.get("error")

        servers.append(
            McpServerOverview(
                name=name,
                config=masked_config,
                status=status,
                tool_count=tool_count,
                error=error,
                tools=[_tool_response(tool) for tool in server_tools],
            )
        )

    return McpOverviewResponse(servers=servers, total_tools=len(tools))


@router.get(
    "/mcp/tools",
    response_model=McpToolsResponse,
    summary="List Enabled MCP Tools",
    description="List tool schemas currently loaded from enabled MCP servers.",
)
async def list_mcp_tools() -> McpToolsResponse:
    tools = _get_cached_mcp_tools()
    return McpToolsResponse(tools=[_tool_response(tool) for tool in tools])


@router.post(
    "/mcp/tools/{tool_name}/call",
    summary="Invoke Enabled MCP Tool",
    description="Invoke one already-loaded MCP tool through DeerFlow's native MCP cache.",
)
async def call_mcp_tool(tool_name: str, request: McpToolCallRequest) -> dict[str, Any]:
    tools = _get_cached_mcp_tools()
    tool = next((item for item in tools if item.name == tool_name), None)
    if tool is None:
        raise HTTPException(
            status_code=404,
            detail={
                "message": f"MCP tool '{tool_name}' is not loaded",
                "available_tools": [item.name for item in tools],
            },
        )

    try:
        if getattr(tool, "coroutine", None) is not None:
            payload = await tool.coroutine(**request.arguments)
        elif getattr(tool, "func", None) is not None:
            payload = tool.func(**request.arguments)
        else:
            raise RuntimeError(f"Tool '{tool_name}' is not invocable")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"MCP tool '{tool_name}' failed: {exc}") from exc

    normalised = _normalise_tool_payload(payload)
    if isinstance(normalised, dict):
        return normalised
    return {"success": True, "result": normalised}


@router.get(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Get MCP Configuration",
    description="Retrieve the current Model Context Protocol (MCP) server configurations.",
)
async def get_mcp_configuration() -> McpConfigResponse:
    """Get the current MCP configuration.

    Returns:
        The current MCP configuration with all servers.

    Example:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "***"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    config = get_extensions_config()

    servers = {name: _mask_server_config(McpServerConfigResponse(**server.model_dump())) for name, server in config.mcp_servers.items()}
    return McpConfigResponse(mcp_servers=servers)


@router.put(
    "/mcp/config",
    response_model=McpConfigResponse,
    summary="Update MCP Configuration",
    description="Update Model Context Protocol (MCP) server configurations and save to file.",
)
async def update_mcp_configuration(request: McpConfigUpdateRequest) -> McpConfigResponse:
    """Update the MCP configuration.

    This will:
    1. Save the new configuration to the mcp_config.json file
    2. Reload the configuration cache
    3. Reset MCP tools cache to trigger reinitialization

    Args:
        request: The new MCP configuration to save.

    Returns:
        The updated MCP configuration.

    Raises:
        HTTPException: 500 if the configuration file cannot be written.

    Example Request:
        ```json
        {
            "mcp_servers": {
                "github": {
                    "enabled": true,
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-github"],
                    "env": {"GITHUB_TOKEN": "$GITHUB_TOKEN"},
                    "description": "GitHub MCP server for repository operations"
                }
            }
        }
        ```
    """
    try:
        # Get the current config path (or determine where to save it)
        config_path = ExtensionsConfig.resolve_config_path()

        # If no config file exists, create one in the parent directory (project root)
        if config_path is None:
            config_path = Path.cwd().parent / "extensions_config.json"
            logger.info(f"No existing extensions config found. Creating new config at: {config_path}")

        # Load current config to preserve skills
        current_config = get_extensions_config()

        # Load raw (un-resolved) JSON from disk to use as the merge source.
        # This preserves $VAR placeholders in env values and top-level keys
        # like mcpInterceptors that would otherwise be lost.
        raw_servers: dict[str, dict] = {}
        raw_other_keys: dict = {}
        if config_path is not None and config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw_data = json.load(f)
            raw_servers = raw_data.get("mcpServers", {})
            # Preserve any top-level keys beyond mcpServers/skills
            for key, value in raw_data.items():
                if key not in ("mcpServers", "skills"):
                    raw_other_keys[key] = value

        # Merge incoming server configs with raw on-disk secrets
        merged_servers: dict[str, McpServerConfigResponse] = {}
        for name, incoming in request.mcp_servers.items():
            raw_server = raw_servers.get(name)
            if raw_server is not None:
                merged_servers[name] = _merge_preserving_secrets(
                    incoming,
                    McpServerConfigResponse(**raw_server),
                )
            else:
                merged_servers[name] = incoming

        # Build config data preserving all top-level keys from the original file
        config_data = dict(raw_other_keys)
        config_data["mcpServers"] = {name: server.model_dump() for name, server in merged_servers.items()}
        config_data["skills"] = {name: {"enabled": skill.enabled} for name, skill in current_config.skills.items()}

        # Write the configuration to file
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"MCP configuration updated and saved to: {config_path}")

        # Reload the configuration and reset the native MCP cache so the
        # settings overview reflects the new server list immediately.
        reloaded_config = reload_extensions_config()
        try:
            from deerflow.mcp.cache import reset_mcp_tools_cache

            reset_mcp_tools_cache()
        except ImportError:
            logger.debug("MCP cache reset skipped because MCP support is not installed")

        servers = {name: _mask_server_config(McpServerConfigResponse(**server.model_dump())) for name, server in reloaded_config.mcp_servers.items()}
        return McpConfigResponse(mcp_servers=servers)

    except Exception as e:
        logger.error(f"Failed to update MCP configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update MCP configuration: {str(e)}")
