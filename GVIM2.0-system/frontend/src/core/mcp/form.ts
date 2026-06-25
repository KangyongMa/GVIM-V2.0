import type { MCPServerConfig, MCPTransportType } from "./types";

export type MCPServerFormValues = {
  name: string;
  enabled: boolean;
  type: MCPTransportType;
  description: string;
  command: string;
  argsText: string;
  envText: string;
  url: string;
  headersText: string;
};

export function normaliseMCPServerName(value: string) {
  return value
    .trim()
    .replace(/\s+/g, "-")
    .replace(/[^A-Za-z0-9_.-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function formatLines(values?: string[] | null) {
  return (values ?? []).join("\n");
}

export function parseLines(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function formatKeyValues(values?: Record<string, string> | null) {
  return Object.entries(values ?? {})
    .map(([key, itemValue]) => `${key}=${itemValue}`)
    .join("\n");
}

export function parseKeyValues(value: string, fieldLabel: string) {
  const result: Record<string, string> = {};
  for (const rawLine of value.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const separatorIndex = line.indexOf("=");
    if (separatorIndex <= 0) {
      throw new Error(`${fieldLabel}: "${line}" must use KEY=VALUE format`);
    }
    const key = line.slice(0, separatorIndex).trim();
    const itemValue = line.slice(separatorIndex + 1).trim();
    if (!key) {
      throw new Error(`${fieldLabel}: key cannot be empty`);
    }
    result[key] = itemValue;
  }
  return result;
}

export function formValuesFromServer(
  name: string,
  config: MCPServerConfig,
): MCPServerFormValues {
  const type =
    config.type === "sse" || config.type === "http" ? config.type : "stdio";
  return {
    name,
    enabled: config.enabled,
    type,
    description: config.description ?? "",
    command: config.command ?? "",
    argsText: formatLines(config.args),
    envText: formatKeyValues(config.env),
    url: config.url ?? "",
    headersText: formatKeyValues(config.headers),
  };
}

export function serverFromFormValues(
  values: MCPServerFormValues,
): MCPServerConfig {
  const base = {
    enabled: values.enabled,
    type: values.type,
    description: values.description.trim(),
  };
  if (values.type === "stdio") {
    return {
      ...base,
      command: values.command.trim(),
      args: parseLines(values.argsText),
      env: parseKeyValues(values.envText, "Environment"),
      url: null,
      headers: {},
    };
  }
  return {
    ...base,
    command: null,
    args: [],
    env: {},
    url: values.url.trim(),
    headers: parseKeyValues(values.headersText, "Headers"),
  };
}

