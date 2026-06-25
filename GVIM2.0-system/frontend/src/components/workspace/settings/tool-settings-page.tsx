"use client";

import {
  CopyPlusIcon,
  PencilIcon,
  PlusIcon,
  RefreshCwIcon,
  Trash2Icon,
} from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import {
  Item,
  ItemActions,
  ItemContent,
  ItemDescription,
  ItemTitle,
} from "@/components/ui/item";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { useI18n } from "@/core/i18n/hooks";
import {
  formValuesFromServer,
  normaliseMCPServerName,
  serverFromFormValues,
  type MCPServerFormValues,
} from "@/core/mcp/form";
import {
  useMCPConfig,
  useMCPOverview,
  useUpdateMCPConfig,
} from "@/core/mcp/hooks";
import {
  BUILT_IN_MCP_SERVER_PRESETS,
  cloneMCPServerConfig,
  type MCPServerPreset,
} from "@/core/mcp/presets";
import type {
  MCPServerConfig,
  MCPServerOverview,
  MCPTransportType,
} from "@/core/mcp/types";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import { SettingsSection } from "./settings-section";

const EMPTY_FORM_VALUES: MCPServerFormValues = {
  name: "",
  enabled: false,
  type: "stdio",
  description: "",
  command: "",
  argsText: "",
  envText: "",
  url: "",
  headersText: "",
};

type EditingServer =
  | {
      mode: "create";
      originalName?: undefined;
      values: MCPServerFormValues;
    }
  | {
      mode: "edit";
      originalName: string;
      values: MCPServerFormValues;
    };

export function ToolSettingsPage() {
  const { t } = useI18n();
  const { config, isLoading, error } = useMCPConfig();
  const updateMCPConfig = useUpdateMCPConfig();
  const [overviewEnabled, setOverviewEnabled] = useState(false);
  const {
    overview,
    isFetching: overviewLoading,
    error: overviewError,
    refetch: refetchOverview,
  } = useMCPOverview(overviewEnabled);
  const [editingServer, setEditingServer] = useState<EditingServer | null>(
    null,
  );

  const staticWebsiteOnly = env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true";
  const servers = useMemo(
    () => config?.mcp_servers ?? {},
    [config?.mcp_servers],
  );
  const overviewByServer = useMemo(() => {
    const entries = overview?.servers.map((server) => [server.name, server]);
    return Object.fromEntries(entries ?? []) as Record<
      string,
      MCPServerOverview
    >;
  }, [overview?.servers]);

  const saveServers = async (nextServers: Record<string, MCPServerConfig>) => {
    if (!config) {
      throw new Error("MCP config not loaded");
    }
    await updateMCPConfig.mutateAsync({ mcp_servers: nextServers });
  };

  const handleToggleServer = async (serverName: string, enabled: boolean) => {
    const server = servers[serverName];
    if (!server) return;
    try {
      await saveServers({
        ...servers,
        [serverName]: {
          ...server,
          enabled,
        },
      });
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

  const handleAddPreset = async (preset: MCPServerPreset) => {
    if (servers[preset.name]) return;
    try {
      await saveServers({
        ...servers,
        [preset.name]: cloneMCPServerConfig(preset.config),
      });
      toast.success("MCP preset added");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

  const handleRemoveServer = async (serverName: string) => {
    if (!window.confirm(`Delete MCP server "${serverName}"?`)) return;
    const nextServers = { ...servers };
    delete nextServers[serverName];
    try {
      await saveServers(nextServers);
      toast.success("MCP server removed");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

  const handleSaveServer = async (editing: EditingServer) => {
    const nextName = normaliseMCPServerName(editing.values.name);
    if (!nextName) {
      toast.error("Server name is required");
      return;
    }
    if (
      editing.mode === "create" &&
      Object.prototype.hasOwnProperty.call(servers, nextName)
    ) {
      toast.error(`MCP server "${nextName}" already exists`);
      return;
    }
    if (
      editing.mode === "edit" &&
      editing.originalName !== nextName &&
      Object.prototype.hasOwnProperty.call(servers, nextName)
    ) {
      toast.error(`MCP server "${nextName}" already exists`);
      return;
    }

    let nextServer: MCPServerConfig;
    try {
      nextServer = serverFromFormValues({
        ...editing.values,
        name: nextName,
      });
      if (nextServer.type === "stdio" && !nextServer.command) {
        throw new Error("Command is required for stdio MCP servers");
      }
      if (
        (nextServer.type === "http" || nextServer.type === "sse") &&
        !nextServer.url
      ) {
        throw new Error("URL is required for remote MCP servers");
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
      return;
    }

    const nextServers = { ...servers };
    if (editing.mode === "edit" && editing.originalName !== nextName) {
      delete nextServers[editing.originalName];
    }
    nextServers[nextName] = nextServer;

    try {
      await saveServers(nextServers);
      setEditingServer(null);
      toast.success("MCP server saved");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    }
  };

function McpSetupGuide() {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-6 rounded-lg border border-cyan-500/20 bg-cyan-50/50 dark:bg-cyan-950/10 p-4 shadow-[0_0_15px_-3px_rgba(6,182,212,0.05)] backdrop-blur-xs">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-cyan-500/10 text-cyan-600 dark:text-cyan-400">
            💡
          </span>
          <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">Model Context Protocol (MCP) 通讯服务配置指南</span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setOpen(!open)} className="text-cyan-600 dark:text-cyan-400 hover:text-cyan-700 dark:hover:text-cyan-300 hover:bg-cyan-500/10 h-7 px-2 text-xs">
          {open ? "收起指南" : "展开配置指南"}
        </Button>
      </div>
      {open && (
        <div className="mt-3 space-y-3 text-xs text-zinc-600 dark:text-zinc-400 border-t border-cyan-500/10 pt-3">
          <p className="leading-relaxed">
            Model Context Protocol (MCP) 是由 Anthropic 提出的开放工具标准，允许大语言模型安全地运行本地代码、查询数据库或执行网络检索。
          </p>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5 rounded-md bg-zinc-950 dark:bg-zinc-950/60 p-2.5 border border-zinc-200 dark:border-white/5 shadow-xs">
              <div className="font-semibold text-cyan-600 dark:text-cyan-400">🛠️ Stdio 本地服务示例 (npx / python)</div>
              <p className="leading-normal text-zinc-300 dark:text-zinc-400">通过执行 CLI 命令行暴露本地工具。例如快速配置 PostgreSQL 数据库工具：</p>
              <code className="block rounded bg-black/40 p-1.5 text-[10px] text-zinc-200 select-all font-mono leading-normal">
                Command: npx<br/>
                Args: -y, @modelcontextprotocol/server-postgres, --connection-string, postgresql://localhost/mydb
              </code>
            </div>
            <div className="space-y-1.5 rounded-md bg-zinc-950 dark:bg-zinc-950/60 p-2.5 border border-zinc-200 dark:border-white/5 shadow-xs">
              <div className="font-semibold text-cyan-600 dark:text-cyan-400">🌐 HTTP/SSE 远端连接示例</div>
              <p className="leading-normal text-zinc-300 dark:text-zinc-400">对接部署在云端或局域网内的 SSE 接口。例如对接本地 Docker 沙箱：</p>
              <code className="block rounded bg-black/40 p-1.5 text-[10px] text-zinc-200 select-all font-mono leading-normal">
                Type: sse<br/>
                URL: http://localhost:3010/sse
              </code>
            </div>
          </div>
          <div className="text-cyan-600 dark:text-cyan-400/80 font-medium">💡 提示：使用下方的「内置预设 Presets」可以一键快速添加常用的搜索和浏览器工具！</div>
        </div>
      )}
    </div>
  );
}

  return (
    <div data-tour="mcp-servers-container">
      <SettingsSection
        title={t.settings.tools.title}
        description={t.settings.tools.description}
      >
        <McpSetupGuide />
        {isLoading ? (
          <div className="text-muted-foreground text-sm">{t.common.loading}</div>
        ) : error ? (
          <div>Error: {error.message}</div>
        ) : (
          <div className="flex w-full flex-col gap-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="space-y-1">
                <h3 className="text-sm font-medium">MCP servers</h3>
                <p className="text-muted-foreground text-sm">
                  Saved to GVIM extensions_config.json. Each enabled server can expose many GVIM tools.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={staticWebsiteOnly || overviewLoading}
                  onClick={() => {
                    if (overviewEnabled) {
                      void refetchOverview();
                    } else {
                      setOverviewEnabled(true);
                    }
                  }}
                >
                  <RefreshCwIcon
                    className={cn(
                      "mr-2 size-4",
                      overviewLoading && "animate-spin",
                    )}
                  />
                  Reload status
                </Button>
                <Button
                  type="button"
                  size="sm"
                  disabled={staticWebsiteOnly || updateMCPConfig.isPending}
                  onClick={() =>
                    setEditingServer({
                      mode: "create",
                      values: {
                        ...EMPTY_FORM_VALUES,
                        enabled: true,
                      },
                    })
                  }
                >
                  <PlusIcon className="size-4" />
                  Add server
                </Button>
              </div>
            </div>

            <PresetList
              presets={BUILT_IN_MCP_SERVER_PRESETS}
              servers={servers}
              disabled={staticWebsiteOnly || updateMCPConfig.isPending}
              onAddPreset={handleAddPreset}
            />

            <MCPServerList
              servers={servers}
              disabled={staticWebsiteOnly || updateMCPConfig.isPending}
              overviewByServer={overviewByServer}
              overviewEnabled={overviewEnabled}
              onEditServer={(name, server) =>
                setEditingServer({
                  mode: "edit",
                  originalName: name,
                  values: formValuesFromServer(name, server),
                })
              }
              onRemoveServer={handleRemoveServer}
              onToggleServer={handleToggleServer}
            />
            {overviewError && (
              <div className="text-destructive text-sm">
                MCP discovery failed: {overviewError.message}
              </div>
            )}
          </div>
        )}

        <MCPServerDialog
          disabled={staticWebsiteOnly || updateMCPConfig.isPending}
          editingServer={editingServer}
          onChange={setEditingServer}
          onOpenChange={(open) => {
            if (!open) setEditingServer(null);
          }}
          onSave={handleSaveServer}
        />
      </SettingsSection>
    </div>
  );
}

function PresetList({
  presets,
  servers,
  disabled,
  onAddPreset,
}: {
  presets: MCPServerPreset[];
  servers: Record<string, MCPServerConfig>;
  disabled: boolean;
  onAddPreset: (preset: MCPServerPreset) => void;
}) {
  return (
    <div className="space-y-3">
      <div className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
        Built-in presets
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        {presets.map((preset) => {
          const installed = Boolean(servers[preset.name]);
          return (
            <Item className="items-start" variant="outline" key={preset.id}>
              <ItemContent>
                <ItemTitle className="flex items-center gap-2">
                  <span>{preset.name}</span>
                  {installed && <Badge variant="outline">Added</Badge>}
                </ItemTitle>
                <ItemDescription className="line-clamp-3">
                  {preset.description}
                </ItemDescription>
              </ItemContent>
              <ItemActions>
                <Button
                  type="button"
                  size="icon-sm"
                  variant="outline"
                  disabled={disabled || installed}
                  onClick={() => onAddPreset(preset)}
                  title={`Add ${preset.name}`}
                >
                  <CopyPlusIcon className="size-4" />
                  <span className="sr-only">Add {preset.name}</span>
                </Button>
              </ItemActions>
            </Item>
          );
        })}
      </div>
    </div>
  );
}

function MCPServerList({
  servers,
  disabled,
  overviewByServer,
  overviewEnabled,
  onEditServer,
  onRemoveServer,
  onToggleServer,
}: {
  servers: Record<string, MCPServerConfig>;
  disabled: boolean;
  overviewByServer: Record<string, MCPServerOverview>;
  overviewEnabled: boolean;
  onEditServer: (name: string, config: MCPServerConfig) => void;
  onRemoveServer: (name: string) => void;
  onToggleServer: (name: string, enabled: boolean) => void;
}) {
  const serverEntries = Object.entries(servers);
  if (serverEntries.length === 0) {
    return (
      <div className="border-border/70 text-muted-foreground rounded-md border border-dashed p-4 text-sm">
        No MCP servers configured.
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-4">
      {serverEntries.map(([name, config]) => {
        const overview = overviewByServer[name];
        const status = config.enabled ? overview?.status : "disabled";
        const toolCount = overview?.tool_count ?? 0;
        const tools = overview?.tools ?? [];
        const visibleTools = tools.slice(0, 12);

        return (
          <Item className="w-full items-start" variant="outline" key={name}>
            <ItemContent>
              <ItemTitle>
                <div className="flex flex-wrap items-center gap-2">
                  <div>{name}</div>
                  <Badge variant="outline">{config.type ?? "stdio"}</Badge>
                  {overviewEnabled && config.enabled && (
                    <>
                      <Badge variant={status === "error" ? "destructive" : "secondary"}>
                        {formatMCPStatus(status)}
                      </Badge>
                      <Badge variant="secondary">{toolCount} tools</Badge>
                    </>
                  )}
                  {!config.enabled && <Badge variant="secondary">Disabled</Badge>}
                </div>
              </ItemTitle>
              <ItemDescription className="line-clamp-3">
                {config.description}
              </ItemDescription>
              <div className="text-muted-foreground line-clamp-2 font-mono text-xs">
                {getServerConnectionLabel(config)}
              </div>
              {overviewEnabled && config.enabled && overview && (
                <div className="border-border/70 mt-3 rounded-md border p-3">
                  {overview.error ? (
                    <div className="text-destructive text-xs">
                      {overview.error}
                    </div>
                  ) : visibleTools.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {visibleTools.map((tool) => (
                        <Badge
                          key={tool.name}
                          variant="outline"
                          title={tool.description || tool.name}
                        >
                          {getToolDisplayName(name, tool.name)}
                        </Badge>
                      ))}
                      {tools.length > visibleTools.length && (
                        <Badge variant="secondary">
                          +{tools.length - visibleTools.length} more
                        </Badge>
                      )}
                    </div>
                  ) : (
                    <div className="text-muted-foreground text-xs">
                      No tools discovered.
                    </div>
                  )}
                </div>
              )}
            </ItemContent>
            <ItemActions className="gap-2">
              <Button
                type="button"
                size="icon-sm"
                variant="outline"
                disabled={disabled}
                onClick={() => onEditServer(name, config)}
                title={`Edit ${name}`}
              >
                <PencilIcon className="size-4" />
                <span className="sr-only">Edit {name}</span>
              </Button>
              <Button
                type="button"
                size="icon-sm"
                variant="outline"
                disabled={disabled}
                onClick={() => onRemoveServer(name)}
                title={`Delete ${name}`}
              >
                <Trash2Icon className="size-4" />
                <span className="sr-only">Delete {name}</span>
              </Button>
              <Switch
                checked={config.enabled}
                disabled={disabled}
                onCheckedChange={(checked) => onToggleServer(name, checked)}
              />
            </ItemActions>
          </Item>
        );
      })}
    </div>
  );
}

function MCPServerDialog({
  disabled,
  editingServer,
  onChange,
  onOpenChange,
  onSave,
}: {
  disabled: boolean;
  editingServer: EditingServer | null;
  onChange: (editingServer: EditingServer | null) => void;
  onOpenChange: (open: boolean) => void;
  onSave: (editingServer: EditingServer) => void;
}) {
  const values = editingServer?.values;
  const inputPrefix =
    editingServer?.mode === "edit"
      ? `mcp-edit-${editingServer.originalName}`
      : "mcp-create";

  const updateValues = (nextValues: Partial<MCPServerFormValues>) => {
    if (!editingServer) return;
    onChange({
      ...editingServer,
      values: {
        ...editingServer.values,
        ...nextValues,
      },
    });
  };

  return (
    <Dialog open={editingServer !== null} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {editingServer?.mode === "edit" ? "Edit MCP server" : "Add MCP server"}
          </DialogTitle>
          <DialogDescription>
            GVIM supports stdio, HTTP, and SSE MCP transports.
          </DialogDescription>
        </DialogHeader>
        {editingServer && values && (
          <form
            className="grid gap-4"
            onSubmit={(event) => {
              event.preventDefault();
              onSave(editingServer);
            }}
          >
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Name" htmlFor={`${inputPrefix}-name`}>
                <Input
                  id={`${inputPrefix}-name`}
                  value={values.name}
                  disabled={disabled}
                  onChange={(event) =>
                    updateValues({ name: event.target.value })
                  }
                />
              </FormField>

              <FormField label="Transport" htmlFor={`${inputPrefix}-type`}>
                <Select
                  value={values.type}
                  disabled={disabled}
                  onValueChange={(value) =>
                    updateValues({ type: value as MCPTransportType })
                  }
                >
                  <SelectTrigger id={`${inputPrefix}-type`} className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="stdio">stdio</SelectItem>
                    <SelectItem value="http">http</SelectItem>
                    <SelectItem value="sse">sse</SelectItem>
                  </SelectContent>
                </Select>
              </FormField>
            </div>

            <FormField
              label="Description"
              htmlFor={`${inputPrefix}-description`}
            >
              <Input
                id={`${inputPrefix}-description`}
                value={values.description}
                disabled={disabled}
                onChange={(event) =>
                  updateValues({ description: event.target.value })
                }
              />
            </FormField>

            {values.type === "stdio" ? (
              <>
                <FormField label="Command" htmlFor={`${inputPrefix}-command`}>
                  <Input
                    id={`${inputPrefix}-command`}
                    value={values.command}
                    disabled={disabled}
                    placeholder="npx"
                    onChange={(event) =>
                      updateValues({ command: event.target.value })
                    }
                  />
                </FormField>
                <FormField label="Arguments" htmlFor={`${inputPrefix}-args`}>
                  <Textarea
                    id={`${inputPrefix}-args`}
                    value={values.argsText}
                    disabled={disabled}
                    placeholder="-y&#10;@modelcontextprotocol/server-github"
                    className="min-h-24 font-mono text-xs"
                    onChange={(event) =>
                      updateValues({ argsText: event.target.value })
                    }
                  />
                </FormField>
                <FormField label="Environment" htmlFor={`${inputPrefix}-env`}>
                  <Textarea
                    id={`${inputPrefix}-env`}
                    value={values.envText}
                    disabled={disabled}
                    placeholder="GITHUB_TOKEN=$GITHUB_TOKEN"
                    className="min-h-24 font-mono text-xs"
                    onChange={(event) =>
                      updateValues({ envText: event.target.value })
                    }
                  />
                </FormField>
              </>
            ) : (
              <>
                <FormField label="URL" htmlFor={`${inputPrefix}-url`}>
                  <Input
                    id={`${inputPrefix}-url`}
                    value={values.url}
                    disabled={disabled}
                    placeholder="https://example.com/mcp"
                    onChange={(event) =>
                      updateValues({ url: event.target.value })
                    }
                  />
                </FormField>
                <FormField label="Headers" htmlFor={`${inputPrefix}-headers`}>
                  <Textarea
                    id={`${inputPrefix}-headers`}
                    value={values.headersText}
                    disabled={disabled}
                    placeholder="Authorization=Bearer $MCP_TOKEN"
                    className="min-h-24 font-mono text-xs"
                    onChange={(event) =>
                      updateValues({ headersText: event.target.value })
                    }
                  />
                </FormField>
              </>
            )}

            <div className="flex items-center justify-between rounded-md border px-3 py-2">
              <div className="space-y-0.5">
                <div className="text-sm font-medium">Enabled</div>
                <div className="text-muted-foreground text-xs">
                  Enabled servers are loaded into GVIM agent tools.
                </div>
              </div>
              <Switch
                checked={values.enabled}
                disabled={disabled}
                onCheckedChange={(enabled) => updateValues({ enabled })}
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={disabled}>
                Save
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function FormField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-2">
      <label
        htmlFor={htmlFor}
        className="text-muted-foreground text-xs font-medium"
      >
        {label}
      </label>
      {children}
    </div>
  );
}

function getServerConnectionLabel(config: MCPServerConfig) {
  if (config.type === "http" || config.type === "sse") {
    return config.url ?? "Remote MCP URL not set";
  }
  return [config.command, ...(config.args ?? [])].filter(Boolean).join(" ");
}

function getToolDisplayName(serverName: string, toolName: string) {
  const prefix = `${serverName}_`;
  return toolName.startsWith(prefix) ? toolName.slice(prefix.length) : toolName;
}

function formatMCPStatus(status?: string) {
  if (!status) return "Unknown";
  return status.charAt(0).toUpperCase() + status.slice(1);
}
