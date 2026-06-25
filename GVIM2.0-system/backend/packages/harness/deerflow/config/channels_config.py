from __future__ import annotations

import copy
import json
import os
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from deerflow.config.paths import get_paths

SECRET_MASK = "********"

ChannelName = Literal[
    "telegram",
    "feishu",
    "slack",
    "discord",
    "dingtalk",
    "wechat",
    "wecom",
]


class ChannelBaseConfig(BaseModel):
    enabled: bool = False
    allow_agent_send: bool = False
    default_target_id: str | None = None
    session: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class TelegramChannelConfig(ChannelBaseConfig):
    bot_token: str | None = None
    default_chat_id: str | None = None
    allowed_users: list[str] = Field(default_factory=list)


class FeishuChannelConfig(ChannelBaseConfig):
    app_id: str | None = None
    app_secret: str | None = None
    verification_token: str | None = None
    domain: str = "https://open.feishu.cn"
    default_receive_id: str | None = None
    default_receive_id_type: Literal["chat_id", "open_id", "user_id", "email"] = "chat_id"


class SlackChannelConfig(ChannelBaseConfig):
    bot_token: str | None = None
    app_token: str | None = None
    default_channel_id: str | None = None
    allowed_users: list[str] = Field(default_factory=list)


class DiscordChannelConfig(ChannelBaseConfig):
    bot_token: str | None = None
    default_channel_id: str | None = None
    allowed_guilds: list[str] = Field(default_factory=list)
    mention_only: bool = False
    allowed_channels: list[str] = Field(default_factory=list)
    thread_mode: bool = False


class DingTalkChannelConfig(ChannelBaseConfig):
    client_id: str | None = None
    client_secret: str | None = None
    default_conversation_id: str | None = None
    allowed_users: list[str] = Field(default_factory=list)
    card_template_id: str | None = None


class WechatChannelConfig(ChannelBaseConfig):
    bot_token: str | None = None
    ilink_bot_id: str | None = None
    default_chat_id: str | None = None
    qrcode_login_enabled: bool = True
    ilink_app_id: str = ""
    route_tag: str = ""
    allowed_users: list[str] = Field(default_factory=list)
    polling_timeout: int = 35
    qrcode_poll_interval: int = 2
    qrcode_poll_timeout: int = 180
    state_dir: str = "./.deer-flow/wechat/state"
    max_inbound_image_bytes: int = 20 * 1024 * 1024
    max_outbound_image_bytes: int = 20 * 1024 * 1024
    max_inbound_file_bytes: int = 50 * 1024 * 1024
    max_outbound_file_bytes: int = 50 * 1024 * 1024
    allowed_file_extensions: list[str] = Field(
        default_factory=lambda: [
            ".txt",
            ".md",
            ".pdf",
            ".csv",
            ".json",
            ".yaml",
            ".yml",
            ".xml",
            ".html",
            ".log",
            ".zip",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".rtf",
            ".py",
            ".js",
            ".ts",
            ".tsx",
        ]
    )


class WeComChannelConfig(ChannelBaseConfig):
    bot_id: str | None = None
    bot_secret: str | None = None
    default_chat_id: str | None = None
    working_message: str = "Working on it..."


class ChannelsConfig(BaseModel):
    langgraph_url: str | None = None
    gateway_url: str | None = None
    session: dict[str, Any] | None = None
    telegram: TelegramChannelConfig = Field(default_factory=TelegramChannelConfig)
    feishu: FeishuChannelConfig = Field(default_factory=FeishuChannelConfig)
    slack: SlackChannelConfig = Field(default_factory=SlackChannelConfig)
    discord: DiscordChannelConfig = Field(default_factory=DiscordChannelConfig)
    dingtalk: DingTalkChannelConfig = Field(default_factory=DingTalkChannelConfig)
    wechat: WechatChannelConfig = Field(default_factory=WechatChannelConfig)
    wecom: WeComChannelConfig = Field(default_factory=WeComChannelConfig)
    model_config = ConfigDict(extra="allow")


CHANNEL_NAMES: tuple[ChannelName, ...] = (
    "telegram",
    "feishu",
    "slack",
    "discord",
    "dingtalk",
    "wechat",
    "wecom",
)

_SECRET_FIELDS: dict[str, tuple[str, ...]] = {
    "telegram": ("bot_token",),
    "feishu": ("app_secret", "verification_token"),
    "slack": ("bot_token", "app_token"),
    "discord": ("bot_token",),
    "dingtalk": ("client_secret",),
    "wechat": ("bot_token",),
    "wecom": ("bot_secret",),
}


def _channels_config_file():
    return get_paths().base_dir / "channels.json"


def _env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _env_list(name: str) -> list[str]:
    value = _env(name)
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _deep_merge(base: Mapping[str, Any] | None, overlay: Mapping[str, Any] | None) -> dict[str, Any]:
    result = copy.deepcopy(dict(base or {}))
    for key, value in dict(overlay or {}).items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def _load_raw_channels_file() -> dict[str, Any]:
    path = _channels_config_file()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _merge_env_defaults(config: ChannelsConfig) -> ChannelsConfig:
    data = config.model_dump()
    data["langgraph_url"] = data.get("langgraph_url") or _env("DEER_FLOW_CHANNELS_LANGGRAPH_URL")
    data["gateway_url"] = data.get("gateway_url") or _env("DEER_FLOW_CHANNELS_GATEWAY_URL")

    telegram = data["telegram"]
    telegram["bot_token"] = telegram.get("bot_token") or _env("TELEGRAM_BOT_TOKEN")
    telegram["default_chat_id"] = telegram.get("default_chat_id") or _env("TELEGRAM_CHAT_ID")
    telegram["enabled"] = bool(telegram.get("enabled") or _env_bool("TELEGRAM_ENABLED"))
    telegram["allowed_users"] = telegram.get("allowed_users") or _env_list("TELEGRAM_ALLOWED_USERS")

    feishu = data["feishu"]
    feishu["app_id"] = feishu.get("app_id") or _env("FEISHU_APP_ID")
    feishu["app_secret"] = feishu.get("app_secret") or _env("FEISHU_APP_SECRET")
    feishu["verification_token"] = feishu.get("verification_token") or _env("FEISHU_VERIFICATION_TOKEN")
    feishu["domain"] = feishu.get("domain") or _env("FEISHU_DOMAIN") or "https://open.feishu.cn"
    feishu["default_receive_id"] = feishu.get("default_receive_id") or _env("FEISHU_RECEIVE_ID")
    feishu["default_receive_id_type"] = feishu.get("default_receive_id_type") or _env("FEISHU_RECEIVE_ID_TYPE") or "chat_id"
    feishu["enabled"] = bool(feishu.get("enabled") or _env_bool("FEISHU_ENABLED"))

    slack = data["slack"]
    slack["bot_token"] = slack.get("bot_token") or _env("SLACK_BOT_TOKEN")
    slack["app_token"] = slack.get("app_token") or _env("SLACK_APP_TOKEN")
    slack["default_channel_id"] = slack.get("default_channel_id") or _env("SLACK_CHANNEL_ID")
    slack["enabled"] = bool(slack.get("enabled") or _env_bool("SLACK_ENABLED"))
    slack["allowed_users"] = slack.get("allowed_users") or _env_list("SLACK_ALLOWED_USERS")

    discord = data["discord"]
    discord["bot_token"] = discord.get("bot_token") or _env("DISCORD_BOT_TOKEN")
    discord["default_channel_id"] = discord.get("default_channel_id") or _env("DISCORD_CHANNEL_ID")
    discord["enabled"] = bool(discord.get("enabled") or _env_bool("DISCORD_ENABLED"))
    discord["allowed_guilds"] = discord.get("allowed_guilds") or _env_list("DISCORD_ALLOWED_GUILDS")

    dingtalk = data["dingtalk"]
    dingtalk["client_id"] = dingtalk.get("client_id") or _env("DINGTALK_CLIENT_ID")
    dingtalk["client_secret"] = dingtalk.get("client_secret") or _env("DINGTALK_CLIENT_SECRET")
    dingtalk["default_conversation_id"] = dingtalk.get("default_conversation_id") or _env("DINGTALK_CONVERSATION_ID")
    dingtalk["card_template_id"] = dingtalk.get("card_template_id") or _env("DINGTALK_CARD_TEMPLATE_ID")
    dingtalk["enabled"] = bool(dingtalk.get("enabled") or _env_bool("DINGTALK_ENABLED"))
    dingtalk["allowed_users"] = dingtalk.get("allowed_users") or _env_list("DINGTALK_ALLOWED_USERS")

    wechat = data["wechat"]
    wechat["bot_token"] = wechat.get("bot_token") or _env("WECHAT_BOT_TOKEN")
    wechat["ilink_bot_id"] = wechat.get("ilink_bot_id") or _env("WECHAT_ILINK_BOT_ID")
    wechat["default_chat_id"] = wechat.get("default_chat_id") or _env("WECHAT_CHAT_ID")
    wechat["enabled"] = bool(wechat.get("enabled") or _env_bool("WECHAT_ENABLED"))
    wechat["allowed_users"] = wechat.get("allowed_users") or _env_list("WECHAT_ALLOWED_USERS")

    wecom = data["wecom"]
    wecom["bot_id"] = wecom.get("bot_id") or _env("WECOM_BOT_ID")
    wecom["bot_secret"] = wecom.get("bot_secret") or _env("WECOM_BOT_SECRET")
    wecom["default_chat_id"] = wecom.get("default_chat_id") or _env("WECOM_CHAT_ID")
    wecom["enabled"] = bool(wecom.get("enabled") or _env_bool("WECOM_ENABLED"))

    return ChannelsConfig.model_validate(data)


def load_channels_config(*, include_env: bool = True) -> ChannelsConfig:
    config = ChannelsConfig.model_validate(_load_raw_channels_file())
    return _merge_env_defaults(config) if include_env else config


def load_effective_channels_config(app_config: Any | None = None, *, include_env: bool = True) -> ChannelsConfig:
    yaml_config: dict[str, Any] = {}
    if app_config is not None:
        extra = getattr(app_config, "model_extra", None) or {}
        raw = extra.get("channels")
        yaml_config = dict(raw) if isinstance(raw, Mapping) else {}
    data = _deep_merge(yaml_config, _load_raw_channels_file())
    config = ChannelsConfig.model_validate(data)
    return _merge_env_defaults(config) if include_env else config


def save_channels_config(config: ChannelsConfig) -> ChannelsConfig:
    path = _channels_config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(config.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return config


def mask_secret(value: str | None) -> str | None:
    return SECRET_MASK if value else None


def mask_channels_config(config: ChannelsConfig) -> ChannelsConfig:
    data = config.model_dump()
    for channel, fields in _SECRET_FIELDS.items():
        channel_data = data.get(channel)
        if isinstance(channel_data, dict):
            for field in fields:
                channel_data[field] = mask_secret(channel_data.get(field))
    return ChannelsConfig.model_validate(data)


def merge_preserving_masked_secrets(
    incoming: ChannelsConfig,
    previous: ChannelsConfig,
) -> ChannelsConfig:
    data = incoming.model_dump()
    previous_data = previous.model_dump()
    for channel, fields in _SECRET_FIELDS.items():
        channel_data = data.get(channel)
        previous_channel = previous_data.get(channel)
        if not isinstance(channel_data, dict) or not isinstance(previous_channel, dict):
            continue
        for field in fields:
            if channel_data.get(field) == SECRET_MASK:
                channel_data[field] = previous_channel.get(field)
    return ChannelsConfig.model_validate(data)


def get_channel_config(config: ChannelsConfig, channel: str) -> ChannelBaseConfig | None:
    if channel not in CHANNEL_NAMES:
        return None
    value = getattr(config, channel)
    return value if isinstance(value, ChannelBaseConfig) else None


def channel_default_target(config: ChannelsConfig, channel: str) -> tuple[str | None, str | None]:
    if channel == "telegram":
        return config.telegram.default_chat_id or config.telegram.default_target_id, None
    if channel == "feishu":
        return (
            config.feishu.default_receive_id or config.feishu.default_target_id,
            config.feishu.default_receive_id_type,
        )
    if channel == "slack":
        return config.slack.default_channel_id or config.slack.default_target_id, None
    if channel == "discord":
        return config.discord.default_channel_id or config.discord.default_target_id, None
    if channel == "dingtalk":
        return config.dingtalk.default_conversation_id or config.dingtalk.default_target_id, None
    if channel == "wechat":
        return config.wechat.default_chat_id or config.wechat.default_target_id, None
    if channel == "wecom":
        return config.wecom.default_chat_id or config.wecom.default_target_id, None
    return None, None
