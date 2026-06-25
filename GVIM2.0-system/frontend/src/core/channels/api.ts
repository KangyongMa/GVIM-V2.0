import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type {
  ChannelInboundResponse,
  ChannelName,
  ChannelRestartResponse,
  ChannelTestRequest,
  ChannelTestResponse,
  ChannelWebhookEndpoints,
  ChannelsConfig,
  ChannelsResponse,
} from "./types";

export async function loadChannels() {
  const response = await fetch(`${getBackendBaseURL()}/api/channels`);
  if (!response.ok) {
    throw new Error(`Failed to load channels: ${response.status}`);
  }
  return response.json() as Promise<ChannelsResponse>;
}

export async function updateChannels(config: ChannelsConfig) {
  const response = await fetch(`${getBackendBaseURL()}/api/channels`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    throw new Error(`Failed to update channels: ${response.status}`);
  }
  return response.json() as Promise<ChannelsResponse>;
}

export async function testChannel(
  channel: ChannelName,
  request: ChannelTestRequest,
) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/channels/${channel}/test`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    },
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(error?.detail ?? `Failed to test ${channel}`);
  }
  return response.json() as Promise<ChannelTestResponse>;
}

export async function restartChannel(channel: ChannelName) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/channels/${channel}/restart`,
    {
      method: "POST",
    },
  );
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      detail?: string;
    } | null;
    throw new Error(error?.detail ?? `Failed to restart ${channel}`);
  }
  return response.json() as Promise<ChannelRestartResponse>;
}

export async function loadChannelWebhooks() {
  const response = await fetch(`${getBackendBaseURL()}/api/channels/webhooks`);
  if (!response.ok) {
    throw new Error(`Failed to load channel webhooks: ${response.status}`);
  }
  return response.json() as Promise<ChannelWebhookEndpoints>;
}

export async function loadChannelInboundActivity(limit = 20) {
  const response = await fetch(
    `${getBackendBaseURL()}/api/channels/inbound?limit=${encodeURIComponent(limit)}`,
  );
  if (!response.ok) {
    throw new Error(
      `Failed to load inbound channel activity: ${response.status}`,
    );
  }
  return response.json() as Promise<ChannelInboundResponse>;
}
