import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  loadMCPConfig,
  loadMCPOverview,
  loadMCPTools,
  updateMCPConfig,
} from "./api";

export function useMCPConfig() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["mcpConfig"],
    queryFn: () => loadMCPConfig(),
  });
  return { config: data, isLoading, error };
}

export function useUpdateMCPConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateMCPConfig,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcpConfig"] });
      void queryClient.invalidateQueries({ queryKey: ["mcpOverview"] });
      void queryClient.invalidateQueries({ queryKey: ["mcpTools"] });
    },
  });
}

export function useMCPTools(enabled = true) {
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["mcpTools"],
    queryFn: () => loadMCPTools(),
    enabled,
  });
  return { tools: data?.tools ?? [], isFetching, error, refetch };
}

export function useMCPOverview(enabled = true) {
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["mcpOverview"],
    queryFn: () => loadMCPOverview(),
    enabled,
  });
  return { overview: data, isFetching, error, refetch };
}

export function useEnableMCPServer() {
  const queryClient = useQueryClient();
  const { config } = useMCPConfig();
  return useMutation({
    mutationFn: async ({
      serverName,
      enabled,
    }: {
      serverName: string;
      enabled: boolean;
    }) => {
      if (!config) {
        throw new Error("MCP config not found");
      }
      if (!config.mcp_servers[serverName]) {
        throw new Error(`MCP server ${serverName} not found`);
      }
      await updateMCPConfig({
        mcp_servers: {
          ...config.mcp_servers,
          [serverName]: {
            ...config.mcp_servers[serverName],
            enabled,
          },
        },
      });
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["mcpConfig"] });
      void queryClient.invalidateQueries({ queryKey: ["mcpOverview"] });
      void queryClient.invalidateQueries({ queryKey: ["mcpTools"] });
    },
  });
}
