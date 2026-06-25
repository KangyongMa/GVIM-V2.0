import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  loadChannelInboundActivity,
  loadChannelWebhooks,
  loadChannels,
  restartChannel,
  testChannel,
  updateChannels,
} from "./api";
import type { ChannelName, ChannelTestRequest, ChannelsConfig } from "./types";

export function useChannels() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["channels"],
    queryFn: () => loadChannels(),
  });
  return { channels: data, isLoading, error };
}

export function useUpdateChannels() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: ChannelsConfig) => updateChannels(config),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}

export function useTestChannel() {
  return useMutation({
    mutationFn: ({
      channel,
      request,
    }: {
      channel: ChannelName;
      request: ChannelTestRequest;
    }) => testChannel(channel, request),
  });
}

export function useRestartChannel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (channel: ChannelName) => restartChannel(channel),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["channels"] });
    },
  });
}

export function useChannelWebhooks() {
  return useQuery({
    queryKey: ["channels", "webhooks"],
    queryFn: () => loadChannelWebhooks(),
  });
}

export function useChannelInboundActivity() {
  return useQuery({
    queryKey: ["channels", "inbound"],
    queryFn: () => loadChannelInboundActivity(20),
    refetchInterval: 10000,
  });
}
