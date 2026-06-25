export type MCPTransportType = "stdio" | "sse" | "http";

export interface MCPOAuthConfig extends Record<string, unknown> {
  enabled?: boolean;
  token_url?: string;
  grant_type?: "client_credentials" | "refresh_token";
  client_id?: string | null;
  client_secret?: string | null;
  refresh_token?: string | null;
  scope?: string | null;
  audience?: string | null;
}

export interface MCPServerConfig extends Record<string, unknown> {
  enabled: boolean;
  type?: MCPTransportType | string;
  command?: string | null;
  args?: string[];
  env?: Record<string, string>;
  url?: string | null;
  headers?: Record<string, string>;
  oauth?: MCPOAuthConfig | null;
  description: string;
}

export interface MCPConfig {
  mcp_servers: Record<string, MCPServerConfig>;
}

export interface MCPTool {
  name: string;
  description: string;
  args_schema?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}

export interface MCPToolsResponse {
  tools: MCPTool[];
}

export interface MCPServerOverview {
  name: string;
  config: MCPServerConfig;
  status: string;
  tool_count: number;
  error?: string | null;
  tools: MCPTool[];
}

export interface MCPOverviewResponse {
  servers: MCPServerOverview[];
  total_tools: number;
}
