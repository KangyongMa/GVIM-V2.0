import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type { MCPConfig, MCPOverviewResponse, MCPToolsResponse } from "./types";

export async function loadMCPConfig() {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`);
  return response.json() as Promise<MCPConfig>;
}

export async function updateMCPConfig(config: MCPConfig) {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/config`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  return response.json();
}

export async function loadMCPTools() {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/tools`);
  return response.json() as Promise<MCPToolsResponse>;
}

export async function loadMCPOverview() {
  const response = await fetch(`${getBackendBaseURL()}/api/mcp/overview`);
  return response.json() as Promise<MCPOverviewResponse>;
}

export async function callMCPTool(
  toolName: string,
  argumentsPayload: Record<string, unknown>,
) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/mcp/tools/${encodeURIComponent(toolName)}/call`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ arguments: argumentsPayload }),
    },
  );

  if (!response.ok) {
    let detail = `MCP tool call failed with status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") {
        detail = payload.detail;
      } else if (payload.detail) {
        detail = JSON.stringify(payload.detail);
      }
    } catch {
      // Keep the default detail.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<Record<string, unknown>>;
}
