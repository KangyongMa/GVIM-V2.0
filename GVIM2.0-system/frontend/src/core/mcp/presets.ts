import type { MCPServerConfig } from "./types";

export type MCPServerPreset = {
  id: string;
  name: string;
  description: string;
  config: MCPServerConfig;
};

export const BUILT_IN_MCP_SERVER_PRESETS: MCPServerPreset[] = [
  {
    id: "github",
    name: "github",
    description: "GitHub repository operations through the standard MCP server.",
    config: {
      enabled: false,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-github"],
      env: {
        GITHUB_TOKEN: "$GITHUB_TOKEN",
      },
      description:
        "GitHub MCP server for repository operations. Requires GITHUB_TOKEN.",
    },
  },
  {
    id: "postgres",
    name: "postgres",
    description: "PostgreSQL database access through a MCP server.",
    config: {
      enabled: false,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-postgres", "$POSTGRES_URL"],
      env: {},
      description:
        "PostgreSQL MCP server. Requires POSTGRES_URL, for example postgresql://localhost/mydb.",
    },
  },
  {
    id: "chrome-devtools",
    name: "chrome-devtools",
    description: "Inspect, debug, screenshot, and automate Chrome through DevTools.",
    config: {
      enabled: false,
      type: "stdio",
      command: "npx",
      args: ["-y", "chrome-devtools-mcp@latest"],
      env: {
        CHROME_DEVTOOLS_MCP_NO_USAGE_STATISTICS: "1",
        CHROME_DEVTOOLS_MCP_NO_UPDATE_CHECKS: "1",
      },
      description:
        "Chrome DevTools MCP server for local browser inspection and automation. Enable only when browser access is needed.",
    },
  },
  {
    id: "filesystem",
    name: "filesystem",
    description: "Filesystem access scoped to the Gateway working directory.",
    config: {
      enabled: false,
      type: "stdio",
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-filesystem", "."],
      env: {},
      description:
        "Filesystem MCP server scoped to the GVIM Gateway working directory.",
    },
  },
];

export function cloneMCPServerConfig(config: MCPServerConfig): MCPServerConfig {
  return {
    ...config,
    args: [...(config.args ?? [])],
    env: { ...(config.env ?? {}) },
    headers: { ...(config.headers ?? {}) },
    oauth: config.oauth ? { ...config.oauth } : config.oauth,
  };
}
