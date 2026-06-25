"use client";

import { 
  Copy as CopyIcon, 
  RefreshCw as RefreshCwIcon, 
  Send as SendIcon,
  HelpCircle as HelpCircleIcon,
  ChevronDown as ChevronDownIcon,
  ChevronUp as ChevronUpIcon,
  ExternalLink as ExternalLinkIcon,
  Link2 as Link2Icon,
  Server as ServerIcon,
  Activity as ActivityIcon,
  Check as CheckIcon
} from "lucide-react";
import type { ReactNode } from "react";
import { useEffect, useId, useMemo, useState } from "react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Item,
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
import {
  useChannelInboundActivity,
  useChannelWebhooks,
  useChannels,
  useRestartChannel,
  useTestChannel,
  useUpdateChannels,
} from "@/core/channels";
import type {
  ChannelInboundSession,
  ChannelName,
  ChannelState,
  ChannelsConfig,
} from "@/core/channels/types";
import { useI18n } from "@/core/i18n/hooks";
import { env } from "@/env";
import { cn } from "@/lib/utils";

import { SettingsSection } from "./settings-section";

const TEST_TEXT = "GVIM AI channel test";
const CHANNELS: Array<{
  name: ChannelName;
  label: string;
  note: string;
}> = [
  { name: "telegram", label: "Telegram", note: "Bot API long polling" },
  { name: "feishu", label: "Feishu / Lark", note: "Events, cards, and files" },
  { name: "wechat", label: "WeChat", note: "iLink polling and QR login" },
  { name: "wecom", label: "WeCom", note: "AI Bot WebSocket" },
  { name: "dingtalk", label: "DingTalk", note: "Stream chatbot" },
  { name: "slack", label: "Slack", note: "Socket Mode" },
  { name: "discord", label: "Discord", note: "Bot gateway" },
];

export function IntegrationSettingsPage() {
  const { t } = useI18n();
  const { channels, isLoading, error } = useChannels();
  const { data: webhooks } = useChannelWebhooks();
  const { data: inbound } = useChannelInboundActivity();
  const [draft, setDraft] = useState<ChannelsConfig | null>(null);
  const [active, setActive] = useState<ChannelName>("telegram");
  const { mutateAsync: updateChannels, isPending: isSaving } =
    useUpdateChannels();
  const { mutateAsync: testChannel, isPending: isTesting } = useTestChannel();
  const { mutateAsync: restartChannel, isPending: isRestarting } =
    useRestartChannel();

  useEffect(() => {
    if (channels?.config) {
      setDraft(channels.config);
    }
  }, [channels?.config]);

  const disabled =
    env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY === "true" ||
    isSaving ||
    isTesting ||
    isRestarting;

  const activeDefinition = useMemo(
    () => CHANNELS.find((channel) => channel.name === active) ?? CHANNELS[0]!,
    [active],
  );

  const handleSave = async () => {
    if (!draft) return;
    try {
      const next = await updateChannels(draft);
      setDraft(next.config);
      toast.success(t.settings.integrations.saved);
    } catch (err) {
      toast.error(t.settings.integrations.saveFailed, {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const handleTest = async (channel: ChannelName) => {
    if (!draft) return;
    try {
      const next = await updateChannels(draft);
      setDraft(next.config);
      await testChannel({
        channel,
        request: {
          text: TEST_TEXT,
          target_id: getDefaultTarget(next.config, channel),
          target_type:
            channel === "feishu"
              ? next.config.feishu.default_receive_id_type
              : undefined,
        },
      });
      toast.success(t.settings.integrations.testSuccess);
    } catch (err) {
      toast.error(t.settings.integrations.testFailed, {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  const handleRestart = async (channel: ChannelName) => {
    if (!draft) return;
    try {
      const next = await updateChannels(draft);
      setDraft(next.config);
      const result = await restartChannel(channel);
      if (result.success) {
        toast.success(result.message);
      } else {
        toast.error(result.message);
      }
    } catch (err) {
      toast.error(`Failed to restart ${channel}`, {
        description: err instanceof Error ? err.message : undefined,
      });
    }
  };

  return (
    <div data-tour="im-integrations-container" className="space-y-6">
      <SettingsSection
        title={t.settings.integrations.title}
        description={t.settings.integrations.description}
      >
        <IntegrationSetupGuide active={active} />
        {isLoading ? (
          <div className="text-muted-foreground text-sm flex items-center gap-2 py-4">
            <span className="size-2 rounded-full bg-primary animate-pulse" />
            {t.common.loading}
          </div>
        ) : error ? (
          <div className="text-destructive text-sm bg-destructive/10 border border-destructive/20 p-3 rounded-lg">
            {error instanceof Error ? error.message : String(error)}
          </div>
        ) : draft ? (
          <div className="space-y-6">
            <div className="grid gap-4 xl:grid-cols-2">
              <RuntimeCard
                draft={draft}
                disabled={disabled}
                setDraft={setDraft}
                serviceRunning={channels?.service_running ?? false}
              />
              <WebhookCard
                telegramUrl={webhooks?.telegram ?? ""}
                feishuUrl={webhooks?.feishu ?? ""}
              />
            </div>

            <section className="bg-background overflow-hidden rounded-xl border border-border/80 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.04)] dark:shadow-none">
              <div className="grid min-w-0 lg:grid-cols-[240px_minmax(0,1fr)]">
                <ChannelPicker
                  active={active}
                  channelsState={channels?.channels}
                  onActiveChange={setActive}
                />
                <ChannelPanel
                  title={activeDefinition.label}
                  description={activeDefinition.note}
                  state={channels?.channels[active]}
                  enabled={draft[active].enabled}
                  disabled={disabled}
                  onEnabledChange={(enabled) =>
                    updateChannel(draft, setDraft, active, { enabled })
                  }
                  onTest={() => handleTest(active)}
                  onRestart={() => handleRestart(active)}
                  onSave={handleSave}
                  isSaving={isSaving}
                  channelName={active}
                  saveText={t.common.save}
                  savingText={t.settings.integrations.saving}
                >
                  <ChannelFields
                    channel={active}
                    draft={draft}
                    disabled={disabled}
                    setDraft={setDraft}
                  />
                </ChannelPanel>
              </div>
            </section>

            <InboundActivity sessions={inbound?.sessions ?? []} />
          </div>
        ) : null}
      </SettingsSection>
    </div>
  );
}

function RuntimeCard({
  draft,
  disabled,
  setDraft,
  serviceRunning,
}: {
  draft: ChannelsConfig;
  disabled: boolean;
  setDraft: (draft: ChannelsConfig) => void;
  serviceRunning: boolean;
}) {
  return (
    <Item variant="outline" className="items-start relative overflow-hidden bg-muted/10 border-border/80 rounded-xl">
      <div className="absolute top-0 right-0 h-16 w-16 bg-primary/5 rounded-bl-full pointer-events-none" />
      <ItemContent className="gap-4 w-full">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b pb-3 w-full">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <ServerIcon className="size-4" />
            </div>
            <div className="space-y-0.5">
              <ItemTitle className="text-sm font-semibold">Channel Runtime</ItemTitle>
              <ItemDescription className="text-xs">
                Agent and Gateway service endpoints.
              </ItemDescription>
            </div>
          </div>
          <span className="relative flex h-2.5 w-2.5 items-center justify-center">
            {serviceRunning && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
            <Badge 
              variant={serviceRunning ? "default" : "outline"}
              className={cn(
                "text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 border-none",
                serviceRunning 
                  ? "bg-emerald-500 text-white dark:bg-emerald-600" 
                  : "bg-muted text-muted-foreground"
              )}
            >
              {serviceRunning ? "running" : "stopped"}
            </Badge>
          </span>
        </div>
        <div className="grid gap-3 w-full sm:grid-cols-2">
          <Field
            label="LangGraph URL"
            value={draft.langgraph_url ?? ""}
            placeholder="http://127.0.0.1:8001/api"
            disabled={disabled}
            onChange={(langgraph_url) => setDraft({ ...draft, langgraph_url })}
          />
          <Field
            label="Gateway URL"
            value={draft.gateway_url ?? ""}
            placeholder="http://127.0.0.1:8001"
            disabled={disabled}
            onChange={(gateway_url) => setDraft({ ...draft, gateway_url })}
          />
        </div>
      </ItemContent>
    </Item>
  );
}

function ChannelPicker({
  active,
  channelsState,
  onActiveChange,
}: {
  active: ChannelName;
  channelsState?: Record<ChannelName, ChannelState>;
  onActiveChange: (channel: ChannelName) => void;
}) {
  return (
    <aside className="bg-muted/10 border-b p-3 lg:border-r lg:border-b-0 border-border/80 flex flex-col gap-2">
      <div className="text-[10px] font-bold text-muted-foreground uppercase tracking-wider px-2 mb-1">
        Messaging Channels
      </div>
      <div className="grid gap-1.5 sm:grid-cols-2 lg:grid-cols-1">
        {CHANNELS.map((channel) => {
          const state = channelsState?.[channel.name];
          const selected = active === channel.name;
          return (
            <button
              key={channel.name}
              type="button"
              aria-current={selected ? "page" : undefined}
              onClick={() => onActiveChange(channel.name)}
              className={cn(
                "group relative flex w-full items-center gap-3 rounded-xl border p-3 text-left transition-all duration-200 outline-none",
                selected
                  ? "border-primary bg-background shadow-sm ring-1 ring-primary/20"
                  : "border-transparent bg-transparent hover:border-border/60 hover:bg-background/60",
              )}
            >
              {selected && (
                <div className="absolute left-0 top-3 bottom-3 w-1 rounded-r-md bg-primary" />
              )}
              <ChannelLogo name={channel.name} className="size-8 text-sm" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-semibold tracking-tight text-foreground">
                  {channel.label}
                </span>
                <span className="text-muted-foreground block truncate text-[10px] leading-snug">
                  {channel.note}
                </span>
              </span>
              <span className="relative flex h-2 w-2 shrink-0">
                {state?.running && (
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                )}
                <span
                  className={cn(
                    "relative inline-flex h-2 w-2 rounded-full",
                    statusDotClass(state)
                  )}
                />
              </span>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

function ChannelPanel({
  title,
  description,
  state,
  enabled,
  disabled,
  onEnabledChange,
  onTest,
  onRestart,
  onSave,
  isSaving,
  channelName,
  saveText,
  savingText,
  children,
}: {
  title: string;
  description: string;
  state?: ChannelState;
  enabled: boolean;
  disabled?: boolean;
  onEnabledChange: (enabled: boolean) => void;
  onTest: () => void;
  onRestart: () => void;
  onSave: () => void;
  isSaving: boolean;
  channelName: ChannelName;
  saveText: string;
  savingText: string;
  children: ReactNode;
}) {
  return (
    <div className="min-w-0 space-y-5 p-4 lg:p-6 bg-card flex flex-col justify-between">
      <div className="space-y-5">
        <div className="flex flex-wrap items-start justify-between gap-3 border-b pb-4 border-border/60">
          <div className="flex items-start gap-3 min-w-0">
            <ChannelLogo name={channelName} className="size-10 text-base mt-1" />
            <div className="min-w-0 space-y-1">
              <div className="flex min-w-0 flex-wrap items-center gap-1.5">
                <h3 className="truncate text-base font-bold tracking-tight text-foreground">{title}</h3>
                <Badge 
                  variant="outline" 
                  className={cn(
                    "text-[10px] font-semibold border px-1.5 py-0.5",
                    state?.configured 
                      ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20" 
                      : "bg-zinc-500/10 text-zinc-600 dark:text-zinc-400 border-zinc-500/20"
                  )}
                >
                  {state?.configured ? "configured" : "not configured"}
                </Badge>
                <Badge 
                  variant="outline"
                  className={cn(
                    "text-[10px] font-semibold border px-1.5 py-0.5",
                    state?.running 
                      ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" 
                      : "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
                  )}
                >
                  {state?.running ? "running" : "stopped"}
                </Badge>
              </div>
              <p className="text-muted-foreground text-xs">{description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 rounded-lg border border-border/40 shrink-0">
            <span className="text-muted-foreground text-xs font-semibold uppercase tracking-wider text-[10px]">
              Enabled
            </span>
            <Switch
              checked={enabled}
              disabled={disabled}
              onCheckedChange={onEnabledChange}
            />
          </div>
        </div>

        <div className="grid min-w-0 gap-4">{children}</div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4 border-border/60 mt-6">
        <div className="text-xs font-medium text-muted-foreground">
          Status: <span className="text-foreground">{statusText(state)}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={onRestart}
            className="h-8 gap-1.5 text-xs hover:bg-muted/80"
          >
            <RefreshCwIcon className="size-3.5 text-muted-foreground" />
            Restart
          </Button>
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={disabled}
            onClick={onTest}
            className="h-8 gap-1.5 text-xs hover:bg-muted/80"
          >
            <SendIcon className="size-3.5 text-muted-foreground" />
            Test
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={disabled}
            onClick={onSave}
            className="h-8 gap-1.5 text-xs bg-primary hover:bg-primary/90 text-primary-foreground font-semibold shadow-xs"
          >
            {isSaving ? savingText : saveText}
          </Button>
        </div>
      </div>
    </div>
  );
}

function ChannelFields({
  channel,
  draft,
  disabled,
  setDraft,
}: {
  channel: ChannelName;
  draft: ChannelsConfig;
  disabled: boolean;
  setDraft: (draft: ChannelsConfig) => void;
}) {
  switch (channel) {
    case "telegram":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Bot token"
              type="password"
              value={draft.telegram.bot_token ?? ""}
              disabled={disabled}
              onChange={(bot_token) =>
                updateChannel(draft, setDraft, "telegram", { bot_token })
              }
            />
            <Field
              label="Default chat ID"
              value={draft.telegram.default_chat_id ?? ""}
              disabled={disabled}
              onChange={(default_chat_id) =>
                updateChannel(draft, setDraft, "telegram", { default_chat_id })
              }
            />
          </div>
          <ArrayField
            label="Allowed users"
            value={draft.telegram.allowed_users}
            disabled={disabled}
            onChange={(allowed_users) =>
              updateChannel(draft, setDraft, "telegram", { allowed_users })
            }
          />
        </>
      );
    case "feishu":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="App ID"
              value={draft.feishu.app_id ?? ""}
              disabled={disabled}
              onChange={(app_id) =>
                updateChannel(draft, setDraft, "feishu", { app_id })
              }
            />
            <Field
              label="App secret"
              type="password"
              value={draft.feishu.app_secret ?? ""}
              disabled={disabled}
              onChange={(app_secret) =>
                updateChannel(draft, setDraft, "feishu", { app_secret })
              }
            />
          </div>
          <Field
            label="Verification token"
            type="password"
            value={draft.feishu.verification_token ?? ""}
            disabled={disabled}
            onChange={(verification_token) =>
              updateChannel(draft, setDraft, "feishu", {
                verification_token,
              })
            }
          />
          <Field
            label="Domain"
            value={draft.feishu.domain}
            disabled={disabled}
            onChange={(domain) =>
              updateChannel(draft, setDraft, "feishu", { domain })
            }
          />
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_170px]">
            <Field
              label="Default receive ID"
              value={draft.feishu.default_receive_id ?? ""}
              disabled={disabled}
              onChange={(default_receive_id) =>
                updateChannel(draft, setDraft, "feishu", {
                  default_receive_id,
                })
              }
            />
            <SelectField
              label="Receive ID type"
              value={draft.feishu.default_receive_id_type}
              disabled={disabled}
              options={["chat_id", "open_id", "user_id", "email"]}
              onChange={(default_receive_id_type) =>
                updateChannel(draft, setDraft, "feishu", {
                  default_receive_id_type:
                    default_receive_id_type as ChannelsConfig["feishu"]["default_receive_id_type"],
                })
              }
            />
          </div>
        </>
      );
    case "slack":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Bot token"
              type="password"
              value={draft.slack.bot_token ?? ""}
              disabled={disabled}
              onChange={(bot_token) =>
                updateChannel(draft, setDraft, "slack", { bot_token })
              }
            />
            <Field
              label="App token"
              type="password"
              value={draft.slack.app_token ?? ""}
              disabled={disabled}
              onChange={(app_token) =>
                updateChannel(draft, setDraft, "slack", { app_token })
              }
            />
          </div>
          <Field
            label="Default channel ID"
            value={draft.slack.default_channel_id ?? ""}
            disabled={disabled}
            onChange={(default_channel_id) =>
              updateChannel(draft, setDraft, "slack", { default_channel_id })
            }
          />
          <ArrayField
            label="Allowed users"
            value={draft.slack.allowed_users}
            disabled={disabled}
            onChange={(allowed_users) =>
              updateChannel(draft, setDraft, "slack", { allowed_users })
            }
          />
        </>
      );
    case "discord":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Bot token"
              type="password"
              value={draft.discord.bot_token ?? ""}
              disabled={disabled}
              onChange={(bot_token) =>
                updateChannel(draft, setDraft, "discord", { bot_token })
              }
            />
            <Field
              label="Default channel ID"
              value={draft.discord.default_channel_id ?? ""}
              disabled={disabled}
              onChange={(default_channel_id) =>
                updateChannel(draft, setDraft, "discord", { default_channel_id })
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <ArrayField
              label="Allowed guilds"
              value={draft.discord.allowed_guilds}
              disabled={disabled}
              onChange={(allowed_guilds) =>
                updateChannel(draft, setDraft, "discord", { allowed_guilds })
              }
            />
            <ArrayField
              label="Allowed channels"
              value={draft.discord.allowed_channels}
              disabled={disabled}
              onChange={(allowed_channels) =>
                updateChannel(draft, setDraft, "discord", { allowed_channels })
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <SwitchRow
              label="Mention only"
              checked={draft.discord.mention_only}
              disabled={disabled}
              onCheckedChange={(mention_only) =>
                updateChannel(draft, setDraft, "discord", { mention_only })
              }
            />
            <SwitchRow
              label="Thread mode"
              checked={draft.discord.thread_mode}
              disabled={disabled}
              onCheckedChange={(thread_mode) =>
                updateChannel(draft, setDraft, "discord", { thread_mode })
              }
            />
          </div>
        </>
      );
    case "dingtalk":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Client ID"
              value={draft.dingtalk.client_id ?? ""}
              disabled={disabled}
              onChange={(client_id) =>
                updateChannel(draft, setDraft, "dingtalk", { client_id })
              }
            />
            <Field
              label="Client secret"
              type="password"
              value={draft.dingtalk.client_secret ?? ""}
              disabled={disabled}
              onChange={(client_secret) =>
                updateChannel(draft, setDraft, "dingtalk", { client_secret })
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Default conversation ID"
              value={draft.dingtalk.default_conversation_id ?? ""}
              disabled={disabled}
              onChange={(default_conversation_id) =>
                updateChannel(draft, setDraft, "dingtalk", {
                  default_conversation_id,
                })
              }
            />
            <Field
              label="Card template ID"
              value={draft.dingtalk.card_template_id ?? ""}
              disabled={disabled}
              onChange={(card_template_id) =>
                updateChannel(draft, setDraft, "dingtalk", { card_template_id })
              }
            />
          </div>
          <ArrayField
            label="Allowed users"
            value={draft.dingtalk.allowed_users}
            disabled={disabled}
            onChange={(allowed_users) =>
              updateChannel(draft, setDraft, "dingtalk", { allowed_users })
            }
          />
        </>
      );
    case "wechat":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Bot token"
              type="password"
              value={draft.wechat.bot_token ?? ""}
              disabled={disabled}
              onChange={(bot_token) =>
                updateChannel(draft, setDraft, "wechat", { bot_token })
              }
            />
            <Field
              label="iLink bot ID"
              value={draft.wechat.ilink_bot_id ?? ""}
              disabled={disabled}
              onChange={(ilink_bot_id) =>
                updateChannel(draft, setDraft, "wechat", { ilink_bot_id })
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Default chat ID"
              value={draft.wechat.default_chat_id ?? ""}
              disabled={disabled}
              onChange={(default_chat_id) =>
                updateChannel(draft, setDraft, "wechat", { default_chat_id })
              }
            />
            <Field
              label="State directory"
              value={draft.wechat.state_dir}
              disabled={disabled}
              onChange={(state_dir) =>
                updateChannel(draft, setDraft, "wechat", { state_dir })
              }
            />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="iLink app ID"
              value={draft.wechat.ilink_app_id}
              disabled={disabled}
              onChange={(ilink_app_id) =>
                updateChannel(draft, setDraft, "wechat", { ilink_app_id })
              }
            />
            <Field
              label="Route tag"
              value={draft.wechat.route_tag}
              disabled={disabled}
              onChange={(route_tag) =>
                updateChannel(draft, setDraft, "wechat", { route_tag })
              }
            />
          </div>
          <SwitchRow
            label="QR login"
            checked={draft.wechat.qrcode_login_enabled}
            disabled={disabled}
            onCheckedChange={(qrcode_login_enabled) =>
              updateChannel(draft, setDraft, "wechat", {
                qrcode_login_enabled,
              })
            }
          />
          <div className="grid gap-3 md:grid-cols-3">
            <NumberField
              label="Polling timeout"
              value={draft.wechat.polling_timeout}
              disabled={disabled}
              onChange={(polling_timeout) =>
                updateChannel(draft, setDraft, "wechat", { polling_timeout })
              }
            />
            <NumberField
              label="QR poll interval"
              value={draft.wechat.qrcode_poll_interval}
              disabled={disabled}
              onChange={(qrcode_poll_interval) =>
                updateChannel(draft, setDraft, "wechat", {
                  qrcode_poll_interval,
                })
              }
            />
            <NumberField
              label="QR poll timeout"
              value={draft.wechat.qrcode_poll_timeout}
              disabled={disabled}
              onChange={(qrcode_poll_timeout) =>
                updateChannel(draft, setDraft, "wechat", {
                  qrcode_poll_timeout,
                })
              }
            />
          </div>
          <ArrayField
            label="Allowed users"
            value={draft.wechat.allowed_users}
            disabled={disabled}
            onChange={(allowed_users) =>
              updateChannel(draft, setDraft, "wechat", { allowed_users })
            }
          />
          <ArrayField
            label="Allowed file extensions"
            value={draft.wechat.allowed_file_extensions}
            disabled={disabled}
            onChange={(allowed_file_extensions) =>
              updateChannel(draft, setDraft, "wechat", {
                allowed_file_extensions,
              })
            }
          />
        </>
      );
    case "wecom":
      return (
        <>
          <div className="grid gap-4 md:grid-cols-2">
            <Field
              label="Bot ID"
              value={draft.wecom.bot_id ?? ""}
              disabled={disabled}
              onChange={(bot_id) =>
                updateChannel(draft, setDraft, "wecom", { bot_id })
              }
            />
            <Field
              label="Bot secret"
              type="password"
              value={draft.wecom.bot_secret ?? ""}
              disabled={disabled}
              onChange={(bot_secret) =>
                updateChannel(draft, setDraft, "wecom", { bot_secret })
              }
            />
          </div>
          <Field
            label="Default chat ID"
            value={draft.wecom.default_chat_id ?? ""}
            disabled={disabled}
            onChange={(default_chat_id) =>
              updateChannel(draft, setDraft, "wecom", { default_chat_id })
            }
          />
          <Field
            label="Working message"
            value={draft.wecom.working_message}
            disabled={disabled}
            onChange={(working_message) =>
              updateChannel(draft, setDraft, "wecom", { working_message })
            }
          />
        </>
      );
  }
}

function WebhookCard({
  telegramUrl,
  feishuUrl,
}: {
  telegramUrl: string;
  feishuUrl: string;
}) {
  return (
    <Item variant="outline" className="items-start relative overflow-hidden bg-muted/10 border-border/80 rounded-xl">
      <div className="absolute top-0 right-0 h-16 w-16 bg-indigo-500/5 rounded-bl-full pointer-events-none" />
      <ItemContent className="gap-4 w-full">
        <div className="flex items-center gap-2 border-b pb-3 w-full border-border/60">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
            <Link2Icon className="size-4" />
          </div>
          <div className="space-y-0.5">
            <ItemTitle className="text-sm font-semibold">Webhook Endpoints</ItemTitle>
            <ItemDescription className="text-xs">
              Callback URLs for platform webhook mode.
            </ItemDescription>
          </div>
        </div>
        <div className="space-y-3 w-full">
          <WebhookField label="Telegram webhook URL" value={telegramUrl} />
          <WebhookField label="Feishu webhook URL" value={feishuUrl} />
        </div>
      </ItemContent>
    </Item>
  );
}

function WebhookField({ label, value }: { label: string; value: string }) {
  const inputId = useId();
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopied(true);
    toast.success("Webhook URL copied");
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="grid min-w-0 gap-2 sm:grid-cols-[140px_minmax(0,1fr)_auto] sm:items-center">
      <label
        htmlFor={inputId}
        className="text-muted-foreground text-xs font-semibold uppercase tracking-wider text-[10px]"
      >
        {label}
      </label>
      <Input
        id={inputId}
        name={inputId}
        className="min-w-0 h-8 text-xs font-mono bg-background/50 border-border/60"
        value={value}
        readOnly
      />
      <Button 
        type="button" 
        variant="outline" 
        size="icon" 
        onClick={handleCopy}
        className="h-8 w-8 hover:bg-muted/80 shrink-0"
      >
        {copied ? (
          <CheckIcon className="size-3.5 text-emerald-500 animate-in fade-in zoom-in-75 duration-200" />
        ) : (
          <CopyIcon className="size-3.5 text-muted-foreground" />
        )}
      </Button>
    </div>
  );
}

function InboundActivity({ sessions }: { sessions: ChannelInboundSession[] }) {
  if (sessions.length === 0) return null;
  return (
    <Item variant="outline" className="items-start rounded-xl border-border/80 bg-muted/5">
      <ItemContent className="gap-4 w-full">
        <div className="flex items-center gap-2.5 border-b pb-3 w-full border-border/60">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
            <ActivityIcon className="size-4" />
          </div>
          <div className="min-w-0 space-y-0.5">
            <ItemTitle className="text-sm font-semibold">Recent Inbound Sessions</ItemTitle>
            <ItemDescription className="text-xs text-muted-foreground">
              Platform chats mapped to GVIM AI threads. Click IDs to copy.
            </ItemDescription>
          </div>
        </div>
        <div className="grid gap-2 w-full mt-1">
          {sessions.slice(0, 8).map((session) => (
            <div
              key={`${session.channel_name}-${session.chat_id}-${
                session.topic_id ?? ""
              }`}
              className="group/row flex flex-col md:flex-row md:items-center justify-between gap-3 rounded-lg border border-border/60 bg-background/50 hover:bg-muted/30 px-4 py-2.5 text-xs transition-colors duration-200 shadow-2xs"
            >
              <div className="flex items-center gap-2.5 min-w-[130px] shrink-0">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
                </span>
                <ChannelLogo name={session.channel_name.toLowerCase() as ChannelName} className="size-5 text-[10px]" />
                <Badge variant="outline" className="text-[10px] font-semibold tracking-wider uppercase bg-background px-1.5 py-0.5 border-border/80">
                  {session.channel_name}
                </Badge>
              </div>
              <div className="min-w-0 flex-1 grid grid-cols-1 md:grid-cols-2 gap-2 md:gap-4">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide shrink-0">Chat ID:</span>
                  <CopyableText text={session.chat_id} label="Chat ID" />
                </div>
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wide shrink-0">Thread:</span>
                  <CopyableText text={session.thread_id} label="Thread ID" />
                </div>
              </div>
            </div>
          ))}
        </div>
      </ItemContent>
    </Item>
  );
}

function Field({
  label,
  value,
  type = "text",
  disabled,
  placeholder,
  onChange,
}: {
  label: string;
  value: string;
  type?: string;
  disabled?: boolean;
  placeholder?: string;
  onChange: (value: string) => void;
}) {
  const inputId = useId();
  return (
    <div className="min-w-0 space-y-1.5">
      <label
        htmlFor={inputId}
        className="text-muted-foreground text-xs font-semibold uppercase tracking-wider text-[10px]"
      >
        {label}
      </label>
      <Input
        id={inputId}
        name={inputId}
        className="min-w-0 text-xs bg-background/50 border-border/60 focus-visible:ring-1 focus-visible:ring-primary/40 focus-visible:border-primary/50"
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </div>
  );
}

function NumberField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: number;
  disabled?: boolean;
  onChange: (value: number) => void;
}) {
  return (
    <Field
      label={label}
      type="number"
      value={String(value)}
      disabled={disabled}
      onChange={(next) => onChange(Number(next) || 0)}
    />
  );
}

function ArrayField({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: string[];
  disabled?: boolean;
  onChange: (value: string[]) => void;
}) {
  return (
    <div className="space-y-2">
      <Field
        label={label}
        value={value.join(", ")}
        disabled={disabled}
        placeholder="Enter values separated by commas"
        onChange={(next) =>
          onChange(
            next
              .split(",")
              .map((item) => item.trim())
              .filter(Boolean),
          )
        }
      />
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1 border border-dashed border-border/40 p-2 rounded-lg bg-muted/10">
          {value.map((item) => (
            <Badge key={item} variant="secondary" className="px-2 py-0 text-[10px] bg-background/60 text-muted-foreground hover:bg-background/80 border border-border/60 font-mono">
              {item}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}

function SelectField({
  label,
  value,
  options,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const selectId = useId();
  return (
    <div className="min-w-0 space-y-1.5">
      <label
        htmlFor={selectId}
        className="text-muted-foreground text-xs font-semibold uppercase tracking-wider text-[10px]"
      >
        {label}
      </label>
      <Select disabled={disabled} value={value} onValueChange={onChange}>
        <SelectTrigger id={selectId} className="min-w-0 h-9 text-xs bg-background/50 border-border/60">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {options.map((option) => (
            <SelectItem key={option} value={option} className="text-xs">
              {option}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function SwitchRow({
  label,
  checked,
  disabled,
  onCheckedChange,
}: {
  label: string;
  checked: boolean;
  disabled?: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="bg-muted/20 flex min-h-10 items-center justify-between gap-3 rounded-lg border border-border/60 px-4 py-2">
      <span className="text-xs font-semibold text-foreground">{label}</span>
      <Switch
        checked={checked}
        disabled={disabled}
        onCheckedChange={onCheckedChange}
      />
    </div>
  );
}

function updateChannel<K extends ChannelName>(
  draft: ChannelsConfig,
  setDraft: (draft: ChannelsConfig) => void,
  channel: K,
  patch: Partial<ChannelsConfig[K]>,
) {
  setDraft({
    ...draft,
    [channel]: {
      ...draft[channel],
      ...patch,
    },
  });
}

function getDefaultTarget(config: ChannelsConfig, channel: ChannelName) {
  switch (channel) {
    case "telegram":
      return (
        config.telegram.default_chat_id ?? config.telegram.default_target_id
      );
    case "feishu":
      return (
        config.feishu.default_receive_id ?? config.feishu.default_target_id
      );
    case "slack":
      return config.slack.default_channel_id ?? config.slack.default_target_id;
    case "discord":
      return (
        config.discord.default_channel_id ?? config.discord.default_target_id
      );
    case "dingtalk":
      return (
        config.dingtalk.default_conversation_id ??
        config.dingtalk.default_target_id
      );
    case "wechat":
      return config.wechat.default_chat_id ?? config.wechat.default_target_id;
    case "wecom":
      return config.wecom.default_chat_id ?? config.wecom.default_target_id;
  }
}

function statusDotClass(state?: ChannelState) {
  if (state?.running) return "bg-emerald-500";
  if (state?.enabled) return "bg-amber-500";
  if (state?.configured) return "bg-sky-500";
  return "bg-muted-foreground/30";
}

function statusText(state?: ChannelState) {
  if (state?.running) return "Running";
  if (state?.enabled) return "Enabled, not running";
  if (state?.configured) return "Configured, disabled";
  return "Not configured";
}

const ChannelLogo = ({ name, className }: { name: ChannelName; className?: string }) => {
  switch (name) {
    case "telegram":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#229ED9]/10 text-[#229ED9]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69.01-.03.01-.14-.07-.2-.08-.06-.19-.04-.27-.02-.12.02-1.96 1.24-5.54 3.65-.52.36-.99.54-1.41.53-.46-.01-1.35-.26-2.01-.48-.81-.27-1.46-.42-1.4-.88.03-.24.36-.49.99-.75 3.87-1.68 6.45-2.79 7.74-3.32 3.69-1.53 4.45-1.8 4.95-1.81.11 0 .36.03.52.16.13.11.17.26.19.37 0 .07.01.22 0 .24z"/>
          </svg>
        </div>
      );
    case "wechat":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#07C160]/10 text-[#07C160]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M8.2 13.5c-.5 0-1-.3-1.2-.7-.3-.6-.1-1.3.4-1.6.6-.3 1.3-.1 1.6.4.3.6.1 1.3-.4 1.6-.1.1-.3.3-.4.3zm5.7 0c-.5 0-1-.3-1.2-.7-.3-.6-.1-1.3.4-1.6.6-.3 1.3-.1 1.6.4.3.6.1 1.3-.4 1.6-.1.1-.3.3-.4.3zm6.6-4.6c.1-3.6-3.3-6.5-7.5-6.5S5.5 5.3 5.5 8.9c0 2 1.1 3.8 2.8 4.9L7.5 16l2.8-1.4c.8.2 1.6.3 2.4.3 4.2 0 7.6-2.9 7.6-6.5zm-5.4 9.1c.3 0 .7 0 1-.1-.7-.8-1.1-1.9-1.1-3.1 0-3.3 2.7-5.9 6-5.9.1 0 .3 0 .4.1C21 10.3 19 12.7 16.2 13l-2.4 1.3.7-2c-1.3-.8-2-2.1-2-3.6 0-1.8 1.1-3.3 2.8-4.2C13.2 4.1 10.8 4 8.5 4 4.4 4 1 6.6 1 9.9c0 1.8 1 3.5 2.6 4.5L2.8 17l2.8-1.3c.9.2 1.9.3 2.9.3 3.6-.1 6.5-2.2 6.6-4.8z" />
          </svg>
        </div>
      );
    case "feishu":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#3370FF]/10 text-[#3370FF]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M12 2C6.48 2 2 6.48 2 12c0 2.4.84 4.6 2.25 6.33L3 21l3.05-.98c1.69 1.15 3.73 1.83 5.95 1.83 5.52 0 10-4.48 10-10S17.52 2 12 2zm2 12.5h-4v-1h4v1zm0-2h-4v-1h4v1zm0-2h-4v-1h4v1z" />
          </svg>
        </div>
      );
    case "wecom":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#1856B1]/10 text-[#1856B1]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M16.2 12c.1-.4.2-.9.2-1.4 0-3.3-2.7-6-6-6-3.3 0-6 2.7-6 6 0 2.3 1.3 4.3 3.2 5.3l-.9 2.7 2.7-.9c.3.1.7.2 1 .2 3.3 0 6-2.7 6-6zm-6 4c-2.2 0-4-1.8-4-4s1.8-4 4-4 4 1.8 4 4-1.8 4-4 4z" />
          </svg>
        </div>
      );
    case "dingtalk":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#0079FF]/10 text-[#0079FF]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm2.5 12h-5c-.3 0-.5-.2-.5-.5v-3c0-.3.2-.5.5-.5h5c.3 0 .5.2.5.5v3c0 .3-.2.5-.5.5z" />
          </svg>
        </div>
      );
    case "slack":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#E01E5A]/10 text-[#E01E5A]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M5.042 15.165a2.528 2.528 0 0 1-2.52 2.523 2.528 2.528 0 0 1-2.522-2.523 2.528 2.528 0 0 1 2.522-2.52h2.52v2.52zm1.261 0a2.528 2.528 0 0 1-2.52 2.52h5.043a2.528 2.528 0 0 1 2.522 2.52v5.043a2.528 2.528 0 0 1-2.522 2.52H8.823a2.528 2.528 0 0 1-2.52-2.52v-5.043zm2.52-10.122a2.528 2.528 0 0 1-2.52-2.52 2.528 2.528 0 0 1 2.52-2.522 2.528 2.528 0 0 1 2.522 2.522v2.52h-2.522zm0 1.261a2.528 2.528 0 0 1 2.522 2.52v5.043a2.528 2.528 0 0 1-2.522 2.52H3.78a2.528 2.528 0 0 1-2.522-2.52V8.824a2.528 2.528 0 0 1 2.522-2.52h5.043zm10.135 3.781a2.528 2.528 0 0 1 2.522-2.52 2.528 2.528 0 0 1 2.52 2.52 2.528 2.528 0 0 1-2.52 2.52h-2.522v-2.52zm-1.261 0a2.528 2.528 0 0 1-2.52 2.52H10.13a2.528 2.528 0 0 1-2.52-2.52V3.78a2.528 2.528 0 0 1 2.52-2.522h5.044a2.528 2.528 0 0 1 2.52 2.522v5.044zm-3.781 10.133a2.528 2.528 0 0 1 2.52-2.52 2.528 2.528 0 0 1 2.522 2.52 2.528 2.528 0 0 1-2.522 2.522h-2.52v-2.52zm0-1.261a2.528 2.528 0 0 1-2.52-2.52v-5.043a2.528 2.528 0 0 1 2.52-2.52h5.043a2.528 2.528 0 0 1 2.522 2.52v5.043a2.528 2.528 0 0 1-2.522 2.52h-5.043z" />
          </svg>
        </div>
      );
    case "discord":
      return (
        <div className={cn("flex size-6 shrink-0 items-center justify-center rounded-full bg-[#5865F2]/10 text-[#5865F2]", className)}>
          <svg viewBox="0 0 24 24" className="size-[55%] fill-current">
            <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994.021-.041.001-.09-.041-.106a13.094 13.094 0 0 1-1.873-.894.077.077 0 0 1-.008-.128c.126-.093.252-.19.372-.287a.075.075 0 0 1 .077-.011c3.92 1.793 8.18 1.793 12.061 0a.073.073 0 0 1 .078.009c.12.099.246.195.373.289a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.894.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03z" />
          </svg>
        </div>
      );
    default:
      return null;
  }
};

const GuideStep = ({ number, children }: { number: number; children: React.ReactNode }) => (
  <div className="flex items-start gap-2.5 text-xs text-zinc-600 dark:text-zinc-400">
    <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-indigo-500/15 font-mono text-[10px] font-bold text-indigo-600 dark:bg-indigo-400/10 dark:text-indigo-400">
      {number}
    </span>
    <span className="leading-relaxed pt-0.5">{children}</span>
  </div>
);

const CopyableText = ({ text, label }: { text: string; label?: string }) => {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    toast.success(label ? `${label} copied` : "Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1.5 hover:text-foreground text-muted-foreground transition-colors max-w-full text-left font-mono"
    >
      <span className="truncate">{text}</span>
      {copied ? (
        <CheckIcon className="size-3.5 shrink-0 text-emerald-500 animate-in fade-in zoom-in-75 duration-200" />
      ) : (
        <CopyIcon className="size-3.5 shrink-0 opacity-0 group-hover/row:opacity-100 transition-opacity" />
      )}
    </button>
  );
};

function IntegrationSetupGuide({ active }: { active: ChannelName }) {
  const [open, setOpen] = useState(false);

  const guideContent = useMemo(() => {
    switch (active) {
      case "telegram":
        return (
          <div className="space-y-3">
            <div className="font-semibold text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5 mb-2">
              <span className="size-1.5 rounded-full bg-indigo-500 animate-pulse" />
              🤖 Telegram Bot 极速接入步骤：
            </div>
            <div className="space-y-2.5">
              <GuideStep number={1}>
                在 Telegram 中搜索并私聊官方机器人{" "}
                <a
                  href="https://t.me/BotFather"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold inline-flex items-center gap-0.5"
                >
                  @BotFather <ExternalLinkIcon className="size-3" />
                </a>
                。
              </GuideStep>
              <GuideStep number={2}>
                发送命令{" "}
                <code className="rounded bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 text-indigo-600 dark:text-indigo-400 font-mono text-[11px] font-semibold">
                  /newbot
                </code>
                ，按照提示为您的 AI 助理起名并创建。
              </GuideStep>
              <GuideStep number={3}>
                创建成功后，复制其生成的唯一{" "}
                <code className="rounded bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 text-indigo-600 dark:text-indigo-400 font-mono text-[11px] font-semibold">
                  Bot Token
                </code>{" "}
                (格式如{" "}
                <code className="text-muted-foreground font-mono text-[10px]">
                  123456:ABC-DEF...
                </code>
                )。
              </GuideStep>
              <GuideStep number={4}>
                私聊机器人{" "}
                <a
                  href="https://t.me/userinfobot"
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 dark:text-indigo-400 hover:underline font-semibold inline-flex items-center gap-0.5"
                >
                  @userinfobot <ExternalLinkIcon className="size-3" />
                </a>{" "}
                以获取您个人的{" "}
                <code className="rounded bg-indigo-500/10 border border-indigo-500/20 px-1.5 py-0.5 text-indigo-600 dark:text-indigo-400 font-mono text-[11px] font-semibold">
                  Chat ID
                </code>
                。
              </GuideStep>
              <GuideStep number={5}>
                在下方配置面板填入这两个核心凭证，开启右侧 “Enabled” 开关，保存后点击右下角 “Test” 即可收到测试推送！
              </GuideStep>
            </div>
          </div>
        );
      case "wechat":
        return (
          <div className="space-y-3">
            <div className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5 mb-2">
              <span className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
              🟢 微信 (WeChat) 接入步骤：
            </div>
            <div className="space-y-2.5">
              <GuideStep number={1}>
                本系统支持通过 <b>腾讯小微 (iLink) 开放平台</b> 接入微信个人/群组助手。
              </GuideStep>
              <GuideStep number={2}>
                登录并访问{" "}
                <a
                  href="https://ilink.qq.com/"
                  target="_blank"
                  rel="noreferrer"
                  className="text-emerald-600 dark:text-emerald-400 hover:underline font-semibold inline-flex items-center gap-0.5"
                >
                  腾讯小微开放平台官网 <ExternalLinkIcon className="size-3" />
                </a>
                ，注册并创建一个全新的智能硬件/设备实例。
              </GuideStep>
              <GuideStep number={3}>
                在小微后台获取您的唯一的{" "}
                <code className="rounded bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 text-emerald-600 dark:text-emerald-400 font-mono text-[11px] font-semibold">
                  iLink Bot ID
                </code>{" "}
                与{" "}
                <code className="rounded bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 text-emerald-600 dark:text-emerald-400 font-mono text-[11px] font-semibold">
                  App ID
                </code>
                。
              </GuideStep>
              <GuideStep number={4}>
                在下方的微信表单中填入上述凭证，开启右侧的 “Enabled” 运行状态开关。
              </GuideStep>
              <GuideStep number={5}>
                或者，您可以直接开启下方的 <b>QRCode Login (扫码登录)</b>，保存后根据后台日志提示直接扫码登录个人微信。
              </GuideStep>
            </div>
          </div>
        );
      case "feishu":
        return (
          <div className="space-y-3">
            <div className="font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-1.5 mb-2">
              <span className="size-1.5 rounded-full bg-blue-500 animate-pulse" />
              🔵 飞书 (Feishu) 接入步骤：
            </div>
            <div className="space-y-2.5">
              <GuideStep number={1}>
                登录飞书开放平台，创建一个全新的“企业自建应用”。
              </GuideStep>
              <GuideStep number={2}>
                在“凭证与基础信息”页面获取该应用的{" "}
                <code className="rounded bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 text-blue-600 dark:text-blue-400 font-mono text-[11px] font-semibold">
                  App ID
                </code>{" "}
                和{" "}
                <code className="rounded bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 text-blue-600 dark:text-blue-400 font-mono text-[11px] font-semibold">
                  App Secret
                </code>
                。
              </GuideStep>
              <GuideStep number={3}>
                在下方配置区填入对应值，并将上方显示的【飞书 Webhook 接收地址】复制粘贴到飞书开放平台后台的“事件订阅”中。
              </GuideStep>
              <GuideStep number={4}>
                在飞书后台开启机器人的“对话”与“获取单聊/群聊消息”相关事件权限，发布并启用应用即可。
              </GuideStep>
            </div>
          </div>
        );
      default:
        return (
          <div className="space-y-1.5 text-zinc-700 dark:text-zinc-300">
            <p>
              本科研工作台内置了极为丰富的第三方 IM 原生接入协议。请在下方选择所需的社交平台，填入对应的授权 Token 或 Webhook 地址，开启即可让 GVIM AI 助理直接进入您的手机或团队讨论群组，实时接收指令并执行化学计算！
            </p>
          </div>
        );
    }
  }, [active]);

  const activeColorClasses = useMemo(() => {
    switch (active) {
      case "telegram":
        return {
          border: "border-indigo-500/20",
          bg: "bg-indigo-50/50 dark:bg-indigo-950/5",
          text: "text-indigo-600 dark:text-indigo-400",
          iconBg: "bg-indigo-500/10",
        };
      case "wechat":
        return {
          border: "border-emerald-500/20",
          bg: "bg-emerald-50/30 dark:bg-emerald-950/5",
          text: "text-emerald-600 dark:text-emerald-400",
          iconBg: "bg-emerald-500/10",
        };
      case "feishu":
        return {
          border: "border-blue-500/20",
          bg: "bg-blue-50/40 dark:bg-blue-950/5",
          text: "text-blue-600 dark:text-blue-400",
          iconBg: "bg-blue-500/10",
        };
      default:
        return {
          border: "border-zinc-500/20",
          bg: "bg-zinc-50/50 dark:bg-zinc-900/10",
          text: "text-zinc-600 dark:text-zinc-400",
          iconBg: "bg-zinc-500/10",
        };
    }
  }, [active]);

  return (
    <div 
      className={cn(
        "mb-5 rounded-xl border p-4 shadow-[0_0_15px_-3px_rgba(0,0,0,0.02)] backdrop-blur-xs transition-all duration-300",
        activeColorClasses.border,
        activeColorClasses.bg
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <span 
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg transition-colors duration-300",
              activeColorClasses.iconBg,
              activeColorClasses.text
            )}
          >
            <HelpCircleIcon className="size-4.5" />
          </span>
          <span className="text-sm font-semibold text-foreground">
            {active.toUpperCase()} 原生数据接入通道配置指南
          </span>
        </div>
        <Button 
          variant="ghost" 
          size="sm" 
          onClick={() => setOpen(!open)} 
          className={cn(
            "hover:bg-muted/60 h-8 px-2.5 text-xs font-semibold gap-1 rounded-lg transition-colors",
            activeColorClasses.text
          )}
        >
          <span>{open ? "收起指南" : "展开配置指南"}</span>
          {open ? (
            <ChevronUpIcon className="size-3.5" />
          ) : (
            <ChevronDownIcon className="size-3.5" />
          )}
        </Button>
      </div>
      {open && (
        <div className="mt-3.5 text-xs border-t border-border/40 pt-3.5 leading-relaxed">
          {guideContent}
        </div>
      )}
    </div>
  );
}
