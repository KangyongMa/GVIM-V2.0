"""Gateway router for IM channel management."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.channels.commands import is_channel_command
from app.channels.message_bus import InboundMessage, InboundMessageType
from app.channels.sender import ChannelSendError, send_channel_message
from app.channels.service import get_channel_service, start_channel_service
from app.channels.store import get_channel_store
from deerflow.config.app_config import get_app_config
from deerflow.config.channels_config import (
    CHANNEL_NAMES,
    ChannelName,
    ChannelsConfig,
    load_effective_channels_config,
    mask_channels_config,
    merge_preserving_masked_secrets,
    save_channels_config,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels", tags=["channels"])


class ChannelState(BaseModel):
    enabled: bool
    configured: bool
    allow_agent_send: bool
    running: bool = False


class ChannelsResponse(BaseModel):
    config: ChannelsConfig
    channels: dict[str, ChannelState]
    service_running: bool = False


class ChannelTestRequest(BaseModel):
    text: str = Field(default="GVIM AI channel test")
    target_id: str | None = None
    target_type: str | None = None


class ChannelTestResponse(BaseModel):
    ok: bool
    message: str
    channel: str
    target_id: str | None = None


class ChannelRestartResponse(BaseModel):
    success: bool
    message: str


class ChannelWebhookEndpoints(BaseModel):
    telegram: str
    feishu: str


class ChannelInboundSession(BaseModel):
    channel_name: str
    chat_id: str
    topic_id: str | None = None
    thread_id: str
    user_id: str | None = None
    created_at: float
    updated_at: float


class ChannelInboundMessage(BaseModel):
    id: str | None = None
    direction: str
    channel_name: str
    chat_id: str
    thread_id: str | None = None
    text: str
    created_at: float
    user_id: str | None = None
    message_type: str | None = None
    in_reply_to: str | None = None
    is_final: bool | None = None


class ChannelInboundResponse(BaseModel):
    sessions: list[ChannelInboundSession]
    messages: list[ChannelInboundMessage]


_CREDENTIAL_FIELDS: dict[str, tuple[str, ...]] = {
    "telegram": ("bot_token",),
    "feishu": ("app_id", "app_secret"),
    "slack": ("bot_token", "app_token"),
    "discord": ("bot_token",),
    "dingtalk": ("client_id", "client_secret"),
    "wechat": ("bot_token",),
    "wecom": ("bot_id", "bot_secret"),
}


def _is_configured(config: ChannelsConfig, channel: str) -> bool:
    channel_config = getattr(config, channel, None)
    if channel_config is None:
        return False
    data = channel_config.model_dump()
    return all(bool(data.get(field)) for field in _CREDENTIAL_FIELDS.get(channel, ()))


def _channel_states(config: ChannelsConfig) -> tuple[dict[str, ChannelState], bool]:
    service = get_channel_service()
    service_status = service.get_status() if service is not None else {"service_running": False, "channels": {}}
    service_channels = service_status.get("channels", {})

    states: dict[str, ChannelState] = {}
    for channel in CHANNEL_NAMES:
        channel_config = getattr(config, channel)
        service_channel = service_channels.get(channel, {}) if isinstance(service_channels, dict) else {}
        states[channel] = ChannelState(
            enabled=bool(channel_config.enabled),
            configured=bool(service_channel.get("configured", _is_configured(config, channel))),
            allow_agent_send=bool(channel_config.allow_agent_send),
            running=bool(service_channel.get("running", False)),
        )
    return states, bool(service_status.get("service_running", False))


def _response(config: ChannelsConfig) -> ChannelsResponse:
    states, service_running = _channel_states(config)
    return ChannelsResponse(
        config=mask_channels_config(config),
        channels=states,
        service_running=service_running,
    )


async def _get_or_start_service():
    service = get_channel_service()
    if service is not None:
        return service
    return await start_channel_service(get_app_config())


@router.get("", response_model=ChannelsResponse)
@router.get("/", response_model=ChannelsResponse)
async def get_channels() -> ChannelsResponse:
    return _response(load_effective_channels_config(get_app_config()))


@router.put("", response_model=ChannelsResponse)
@router.put("/", response_model=ChannelsResponse)
async def update_channels(config: ChannelsConfig) -> ChannelsResponse:
    previous = load_effective_channels_config(get_app_config(), include_env=False)
    merged = merge_preserving_masked_secrets(config, previous)
    save_channels_config(merged)
    effective = load_effective_channels_config(get_app_config())
    service = await _get_or_start_service()
    await service.apply_config(effective)
    return _response(effective)


@router.post("/{channel}/test", response_model=ChannelTestResponse)
async def test_channel(channel: ChannelName, request: ChannelTestRequest) -> ChannelTestResponse:
    try:
        result = await send_channel_message(
            channel,
            request.text,
            target_id=request.target_id,
            target_type=request.target_type,
            for_agent=False,
        )
    except ChannelSendError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChannelTestResponse(
        ok=result.ok,
        message=result.message,
        channel=result.channel,
        target_id=result.target_id,
    )


@router.post("/{channel}/restart", response_model=ChannelRestartResponse)
async def restart_channel(channel: ChannelName) -> ChannelRestartResponse:
    service = await _get_or_start_service()
    success = await service.restart_channel(channel)
    if success:
        logger.info("Channel %s restarted successfully", channel)
        return ChannelRestartResponse(success=True, message=f"Channel {channel} restarted.")
    logger.warning("Failed to restart channel %s", channel)
    return ChannelRestartResponse(
        success=False,
        message=f"Channel {channel} is disabled, missing credentials, missing dependencies, or failed to start.",
    )


@router.get("/webhooks", response_model=ChannelWebhookEndpoints)
async def get_channel_webhooks(request: Request) -> ChannelWebhookEndpoints:
    base_url = str(request.base_url).rstrip("/")
    return ChannelWebhookEndpoints(
        telegram=f"{base_url}/api/channels/telegram/webhook",
        feishu=f"{base_url}/api/channels/feishu/webhook",
    )


@router.get("/inbound", response_model=ChannelInboundResponse)
async def list_inbound_channel_activity(
    channel: str | None = None,
    chat_id: str | None = None,
    thread_id: str | None = None,
    limit: int = 50,
) -> ChannelInboundResponse:
    store = get_channel_store()
    safe_limit = max(1, min(limit, 200))
    sessions = store.list_sessions(channel_name=channel, limit=safe_limit)
    messages = store.list_messages(
        channel_name=channel,
        chat_id=chat_id,
        thread_id=thread_id,
        limit=safe_limit,
    )
    return ChannelInboundResponse(sessions=sessions, messages=messages)


def _telegram_message_from_update(payload: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("message", "edited_message", "channel_post"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return None


def _telegram_inbound(payload: dict[str, Any]) -> InboundMessage | None:
    message = _telegram_message_from_update(payload)
    if not message:
        return None

    text = str(message.get("text") or message.get("caption") or "").strip()
    if not text:
        return None

    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    chat_id = str(chat.get("id") or "")
    if not chat_id:
        return None

    message_id = str(message.get("message_id") or payload.get("update_id") or "")
    chat_type = str(chat.get("type") or "private")
    reply_to = message.get("reply_to_message") if isinstance(message.get("reply_to_message"), dict) else None
    topic_id = None if chat_type == "private" else str(reply_to.get("message_id") if reply_to else message_id)

    return InboundMessage(
        channel_name="telegram",
        chat_id=chat_id,
        user_id=str(sender.get("id") or ""),
        text=text,
        msg_type=InboundMessageType.COMMAND if is_channel_command(text) else InboundMessageType.CHAT,
        message_id=f"telegram-{payload.get('update_id') or message_id}",
        thread_ts=message_id,
        topic_id=topic_id,
        metadata={"raw_update_id": payload.get("update_id"), "chat_type": chat_type},
    )


@router.post("/telegram/webhook")
async def telegram_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    inbound = _telegram_inbound(payload)
    if inbound is None:
        return {"ok": True, "ignored": True}

    service = await _get_or_start_service()
    await service.bus.publish_inbound(inbound)

    response: dict[str, Any] = {
        "method": "sendMessage",
        "chat_id": inbound.chat_id,
        "text": "Working on it...",
    }
    if inbound.thread_ts:
        response["reply_to_message_id"] = inbound.thread_ts
    return response


def _decode_feishu_content(content: Any) -> str:
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
        except Exception:
            return content
    else:
        parsed = content

    if isinstance(parsed, dict):
        text = parsed.get("text")
        if isinstance(text, str):
            return text.strip()
        rich = parsed.get("content")
        if isinstance(rich, list):
            parts: list[str] = []
            for paragraph in rich:
                if not isinstance(paragraph, list):
                    continue
                for item in paragraph:
                    if isinstance(item, dict):
                        value = item.get("text")
                        if isinstance(value, str):
                            parts.append(value)
            return " ".join(parts).strip()
    return ""


def _feishu_inbound(payload: dict[str, Any]) -> InboundMessage | None:
    event = payload.get("event") if isinstance(payload.get("event"), dict) else {}
    message = event.get("message") if isinstance(event.get("message"), dict) else {}
    sender = event.get("sender") if isinstance(event.get("sender"), dict) else {}
    if not message:
        return None

    text = _decode_feishu_content(message.get("content")).strip()
    if not text:
        return None

    sender_id = sender.get("sender_id") if isinstance(sender.get("sender_id"), dict) else {}
    chat_id = str(message.get("chat_id") or "")
    message_id = str(message.get("message_id") or "")
    topic_id = str(message.get("root_id") or message_id or chat_id)
    if not chat_id:
        return None

    return InboundMessage(
        channel_name="feishu",
        chat_id=chat_id,
        user_id=str(sender_id.get("open_id") or sender_id.get("user_id") or ""),
        text=text,
        msg_type=InboundMessageType.COMMAND if is_channel_command(text) else InboundMessageType.CHAT,
        message_id=f"feishu-{message_id or chat_id}",
        thread_ts=message_id,
        topic_id=topic_id,
        metadata={
            "message_type": message.get("message_type"),
            "root_id": message.get("root_id"),
        },
    )


@router.post("/feishu/webhook")
async def feishu_webhook(payload: dict[str, Any]) -> dict[str, Any]:
    challenge = payload.get("challenge")
    if isinstance(challenge, str) and challenge:
        return {"challenge": challenge}
    if payload.get("type") == "url_verification" and isinstance(payload.get("challenge"), str):
        return {"challenge": payload["challenge"]}

    inbound = _feishu_inbound(payload)
    if inbound is None:
        return {"code": 0, "msg": "ignored"}

    service = await _get_or_start_service()
    await service.bus.publish_inbound(inbound)

    return {"code": 0, "msg": "success", "queued": True}
