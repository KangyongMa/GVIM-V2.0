from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from app.channels.message_bus import OutboundMessage
from app.channels.service import get_channel_service
from deerflow.config.app_config import get_app_config
from deerflow.config.channels_config import (
    ChannelName,
    channel_default_target,
    get_channel_config,
    load_effective_channels_config,
)


@dataclass(frozen=True)
class ChannelSendResult:
    channel: str
    target_id: str
    ok: bool
    message: str


class ChannelSendError(RuntimeError):
    pass


def _trim_text(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized:
        raise ChannelSendError("Message text is required.")
    return normalized[:8000]


async def send_channel_message(
    channel: ChannelName,
    text: str,
    *,
    target_id: str | None = None,
    target_type: str | None = None,
    for_agent: bool = False,
) -> ChannelSendResult:
    service = get_channel_service()
    if service is None:
        raise ChannelSendError("Channel service is not running.")

    config = load_effective_channels_config(get_app_config())
    channel_config = get_channel_config(config, channel)
    if channel_config is None:
        raise ChannelSendError(f"Unsupported channel: {channel}")
    if not channel_config.enabled:
        raise ChannelSendError(f"{channel} is not enabled.")
    if for_agent and not channel_config.allow_agent_send:
        raise ChannelSendError(
            f"{channel} is configured, but agent sending is disabled for this channel."
        )
    if service.get_channel(channel) is None:
        raise ChannelSendError(
            f"{channel} is enabled but not running. Check credentials and optional channel dependencies."
        )

    default_target, default_target_type = channel_default_target(config, channel)
    resolved_target = target_id or default_target
    if not resolved_target:
        raise ChannelSendError(f"{channel} target id is required.")

    metadata = {}
    resolved_target_type = target_type or default_target_type
    if resolved_target_type:
        metadata["target_type"] = resolved_target_type

    await service.bus.publish_outbound(
        OutboundMessage(
            channel_name=channel,
            chat_id=resolved_target,
            thread_id="manual-channel-message",
            text=_trim_text(text),
            metadata=metadata,
        )
    )
    return ChannelSendResult(
        channel=channel,
        target_id=resolved_target,
        ok=True,
        message=f"{channel} message queued.",
    )


def send_channel_message_sync(
    channel: ChannelName,
    text: str,
    *,
    target_id: str | None = None,
    target_type: str | None = None,
    for_agent: bool = False,
) -> ChannelSendResult:
    async def _run() -> ChannelSendResult:
        return await send_channel_message(
            channel,
            text,
            target_id=target_id,
            target_type=target_type,
            for_agent=for_agent,
        )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(lambda: asyncio.run(_run()))
        return future.result()
