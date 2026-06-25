export type ChannelName =
  | "telegram"
  | "feishu"
  | "slack"
  | "discord"
  | "dingtalk"
  | "wechat"
  | "wecom";

export interface ChannelBaseConfig {
  enabled: boolean;
  allow_agent_send: boolean;
  default_target_id?: string | null;
  session?: Record<string, unknown> | null;
}

export interface TelegramChannelConfig extends ChannelBaseConfig {
  bot_token?: string | null;
  default_chat_id?: string | null;
  allowed_users: string[];
}

export interface FeishuChannelConfig extends ChannelBaseConfig {
  app_id?: string | null;
  app_secret?: string | null;
  verification_token?: string | null;
  domain: string;
  default_receive_id?: string | null;
  default_receive_id_type: "chat_id" | "open_id" | "user_id" | "email";
}

export interface SlackChannelConfig extends ChannelBaseConfig {
  bot_token?: string | null;
  app_token?: string | null;
  default_channel_id?: string | null;
  allowed_users: string[];
}

export interface DiscordChannelConfig extends ChannelBaseConfig {
  bot_token?: string | null;
  default_channel_id?: string | null;
  allowed_guilds: string[];
  mention_only: boolean;
  allowed_channels: string[];
  thread_mode: boolean;
}

export interface DingTalkChannelConfig extends ChannelBaseConfig {
  client_id?: string | null;
  client_secret?: string | null;
  default_conversation_id?: string | null;
  allowed_users: string[];
  card_template_id?: string | null;
}

export interface WechatChannelConfig extends ChannelBaseConfig {
  bot_token?: string | null;
  ilink_bot_id?: string | null;
  default_chat_id?: string | null;
  qrcode_login_enabled: boolean;
  ilink_app_id: string;
  route_tag: string;
  allowed_users: string[];
  polling_timeout: number;
  qrcode_poll_interval: number;
  qrcode_poll_timeout: number;
  state_dir: string;
  max_inbound_image_bytes: number;
  max_outbound_image_bytes: number;
  max_inbound_file_bytes: number;
  max_outbound_file_bytes: number;
  allowed_file_extensions: string[];
}

export interface WeComChannelConfig extends ChannelBaseConfig {
  bot_id?: string | null;
  bot_secret?: string | null;
  default_chat_id?: string | null;
  working_message: string;
}

export interface ChannelsConfig {
  langgraph_url?: string | null;
  gateway_url?: string | null;
  session?: Record<string, unknown> | null;
  telegram: TelegramChannelConfig;
  feishu: FeishuChannelConfig;
  slack: SlackChannelConfig;
  discord: DiscordChannelConfig;
  dingtalk: DingTalkChannelConfig;
  wechat: WechatChannelConfig;
  wecom: WeComChannelConfig;
}

export interface ChannelState {
  enabled: boolean;
  configured: boolean;
  allow_agent_send: boolean;
  running: boolean;
}

export interface ChannelsResponse {
  config: ChannelsConfig;
  channels: Record<ChannelName, ChannelState>;
  service_running: boolean;
}

export interface ChannelTestRequest {
  text: string;
  target_id?: string | null;
  target_type?: string | null;
}

export interface ChannelTestResponse {
  ok: boolean;
  message: string;
  channel: string;
  target_id?: string | null;
}

export interface ChannelRestartResponse {
  success: boolean;
  message: string;
}

export interface ChannelWebhookEndpoints {
  telegram: string;
  feishu: string;
}

export interface ChannelInboundSession {
  channel_name: string;
  chat_id: string;
  topic_id?: string | null;
  thread_id: string;
  user_id?: string | null;
  created_at: number;
  updated_at: number;
}

export interface ChannelInboundMessage {
  id?: string | null;
  direction: string;
  channel_name: string;
  chat_id: string;
  thread_id?: string | null;
  text: string;
  created_at: number;
  user_id?: string | null;
  message_type?: string | null;
  in_reply_to?: string | null;
  is_final?: boolean | null;
}

export interface ChannelInboundResponse {
  sessions: ChannelInboundSession[];
  messages: ChannelInboundMessage[];
}
