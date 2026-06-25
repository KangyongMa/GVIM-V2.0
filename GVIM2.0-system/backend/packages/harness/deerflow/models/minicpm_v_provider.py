"""Native DeerFlow provider for MiniCPM-V chat models.

The provider plugs into DeerFlow through the normal ``models[*].use`` class
path and implements LangChain's ``BaseChatModel`` contract directly. DeerFlow
owns message conversion, tool binding, usage metadata, and vision content
handling here; the Gateway does not start or manage a model process.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain_core.callbacks import AsyncCallbackManagerForLLMRun, CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ChatMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import RunnableBinding
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_function
from pydantic import ConfigDict

logger = logging.getLogger(__name__)


class MiniCPMV46ChatModel(BaseChatModel):
    """MiniCPM-V 4.6 chat model provider loaded natively by DeerFlow.

    Config example:

        - name: minicpm-v-4.6
          use: deerflow.models.minicpm_v_provider:MiniCPMV46ChatModel
          model: minicpm-v-4.6
          endpoint_url: http://127.0.0.1:8080/v1/chat/completions
          supports_vision: true
    """

    model: str = "minicpm-v-4.6"
    endpoint_url: str = "http://127.0.0.1:8080/v1/chat/completions"
    api_key: str | None = None
    timeout: float = 600.0
    max_retries: int = 1
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    seed: int | None = None
    extra_body: dict[str, Any] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    @classmethod
    def is_lc_serializable(cls) -> bool:
        return True

    @property
    def _llm_type(self) -> str:
        return "deerflow-minicpm-v"

    @staticmethod
    def _content_to_text(content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(part for part in (MiniCPMV46ChatModel._content_to_text(item) for item in content) if part)
        if isinstance(content, dict):
            if content.get("type") == "text" and isinstance(content.get("text"), str):
                return content["text"]
            for key in ("text", "content", "output"):
                value = content.get(key)
                if isinstance(value, str):
                    return value
            try:
                return json.dumps(content, ensure_ascii=False)
            except TypeError:
                return str(content)
        if content is None:
            return ""
        try:
            return json.dumps(content, ensure_ascii=False)
        except TypeError:
            return str(content)

    @staticmethod
    def _normalize_content_blocks(content: Any) -> Any:
        """Preserve text + image_url blocks from DeerFlow's vision middleware."""
        if isinstance(content, str):
            return content
        if not isinstance(content, list):
            return MiniCPMV46ChatModel._content_to_text(content)

        blocks: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, str):
                blocks.append({"type": "text", "text": item})
                continue
            if not isinstance(item, dict):
                text = MiniCPMV46ChatModel._content_to_text(item)
                if text:
                    blocks.append({"type": "text", "text": text})
                continue
            if item.get("type") == "text":
                blocks.append({"type": "text", "text": str(item.get("text", ""))})
                continue
            if item.get("type") == "image_url" and isinstance(item.get("image_url"), dict):
                blocks.append({"type": "image_url", "image_url": item["image_url"]})
                continue
            text = MiniCPMV46ChatModel._content_to_text(item)
            if text:
                blocks.append({"type": "text", "text": text})
        return blocks or ""

    @staticmethod
    def _format_tool_call(tool_call: dict[str, Any]) -> dict[str, Any]:
        args = tool_call.get("args") or {}
        if not isinstance(args, str):
            args = json.dumps(args, ensure_ascii=False)
        return {
            "id": tool_call.get("id") or "",
            "type": "function",
            "function": {
                "name": tool_call.get("name") or "",
                "arguments": args,
            },
        }

    def _convert_messages(self, messages: list[BaseMessage]) -> list[dict[str, Any]]:
        payload_messages: list[dict[str, Any]] = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                payload_messages.append({"role": "system", "content": self._content_to_text(msg.content)})
            elif isinstance(msg, HumanMessage):
                payload_messages.append({"role": "user", "content": self._normalize_content_blocks(msg.content)})
            elif isinstance(msg, AIMessage):
                payload_msg: dict[str, Any] = {"role": "assistant", "content": self._content_to_text(msg.content)}
                if msg.tool_calls:
                    payload_msg["tool_calls"] = [self._format_tool_call(tool_call) for tool_call in msg.tool_calls]
                payload_messages.append(payload_msg)
            elif isinstance(msg, ToolMessage):
                payload_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg.tool_call_id,
                        "content": self._content_to_text(msg.content),
                    }
                )
            elif isinstance(msg, ChatMessage):
                payload_messages.append({"role": msg.role, "content": self._content_to_text(msg.content)})
            else:
                payload_messages.append({"role": msg.type, "content": self._content_to_text(msg.content)})
        return payload_messages

    @staticmethod
    def _format_tools(tools: list[Any] | None) -> list[dict[str, Any]]:
        if not tools:
            return []

        formatted_tools: list[dict[str, Any]] = []
        for tool in tools:
            if isinstance(tool, dict):
                if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
                    formatted_tools.append(tool)
                elif "name" in tool:
                    formatted_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool["name"],
                                "description": tool.get("description", ""),
                                "parameters": tool.get("parameters", {}),
                            },
                        }
                    )
                continue

            if isinstance(tool, BaseTool):
                function = convert_to_openai_function(tool)
            else:
                function = convert_to_openai_function(tool)
            formatted_tools.append({"type": "function", "function": function})
        return formatted_tools

    def _build_payload(
        self,
        messages: list[BaseMessage],
        *,
        stop: list[str] | None = None,
        tools: list[Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": self._convert_messages(messages),
            "stream": False,
        }

        for key in ("max_tokens", "temperature", "top_p", "seed"):
            value = getattr(self, key)
            if value is not None:
                payload[key] = value

        if stop:
            payload["stop"] = stop

        formatted_tools = self._format_tools(tools)
        if formatted_tools:
            payload["tools"] = formatted_tools

        # llama-server.exe does not support parallel_tool_calls and will reject it with 400 Bad Request.
        for key in ("tool_choice",):
            if key in kwargs and kwargs[key] is not None:
                payload[key] = kwargs[key]

        if self.extra_body:
            payload.update(self.extra_body)

        return payload

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(1, self.max_retries + 1)
        for attempt in range(attempts):
            try:
                with httpx.Client(timeout=self.timeout, trust_env=False) as client:
                    response = client.post(self.endpoint_url, headers=self._headers(), json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise RuntimeError("MiniCPM-V endpoint returned a non-object JSON response")
                    return data
            except (httpx.HTTPError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    raise
                logger.warning("MiniCPM-V request failed; retrying %s/%s", attempt + 1, attempts)
        raise RuntimeError("MiniCPM-V request failed") from last_error

    async def _apost_chat_completions(self, payload: dict[str, Any]) -> dict[str, Any]:
        last_error: Exception | None = None
        attempts = max(1, self.max_retries + 1)
        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, trust_env=False) as client:
                    response = await client.post(self.endpoint_url, headers=self._headers(), json=payload)
                    response.raise_for_status()
                    data = response.json()
                    if not isinstance(data, dict):
                        raise RuntimeError("MiniCPM-V endpoint returned a non-object JSON response")
                    return data
            except (httpx.HTTPError, RuntimeError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    raise
                logger.warning("MiniCPM-V request failed; retrying %s/%s", attempt + 1, attempts)
        raise RuntimeError("MiniCPM-V request failed") from last_error

    @staticmethod
    def _usage_metadata(usage: dict[str, Any] | None) -> dict[str, int] | None:
        if not usage:
            return None
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        total_tokens = int(usage.get("total_tokens") or input_tokens + output_tokens)
        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _parse_tool_calls(raw_tool_calls: list[dict[str, Any]] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        tool_calls: list[dict[str, Any]] = []
        invalid_tool_calls: list[dict[str, Any]] = []
        for raw in raw_tool_calls or []:
            function = raw.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError as exc:
                invalid_tool_calls.append(
                    {
                        "type": "invalid_tool_call",
                        "name": function.get("name"),
                        "args": str(raw_args),
                        "id": raw.get("id"),
                        "error": f"Failed to parse tool arguments: {exc}",
                    }
                )
                continue
            if not isinstance(args, dict):
                invalid_tool_calls.append(
                    {
                        "type": "invalid_tool_call",
                        "name": function.get("name"),
                        "args": str(raw_args),
                        "id": raw.get("id"),
                        "error": "Tool arguments must decode to a JSON object.",
                    }
                )
                continue
            tool_calls.append(
                {
                    "name": function.get("name") or "",
                    "args": args,
                    "id": raw.get("id") or "",
                    "type": "tool_call",
                }
            )
        return tool_calls, invalid_tool_calls

    def _parse_response(self, response: dict[str, Any]) -> ChatResult:
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError("MiniCPM-V endpoint returned no choices")

        choice = choices[0]
        raw_message = choice.get("message") or {}
        content = raw_message.get("content") or ""
        if not isinstance(content, str):
            content = self._content_to_text(content)

        tool_calls, invalid_tool_calls = self._parse_tool_calls(raw_message.get("tool_calls"))
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else None
        model_name = response.get("model") or self.model
        finish_reason = choice.get("finish_reason")

        message = AIMessage(
            content=content,
            tool_calls=tool_calls,
            invalid_tool_calls=invalid_tool_calls,
            usage_metadata=self._usage_metadata(usage),
            response_metadata={
                "finish_reason": finish_reason,
                "model_name": model_name,
                "model_provider": "minicpm-v",
                "usage": usage or {},
            },
        )

        return ChatResult(
            generations=[ChatGeneration(message=message, generation_info={"finish_reason": finish_reason, "model_name": model_name})],
            llm_output={"token_usage": usage or {}, "model_name": model_name},
        )

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        tools = kwargs.pop("tools", None)
        payload = self._build_payload(messages, stop=stop, tools=tools, **kwargs)
        return self._parse_response(self._post_chat_completions(payload))

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        tools = kwargs.pop("tools", None)
        payload = self._build_payload(messages, stop=stop, tools=tools, **kwargs)
        return self._parse_response(await self._apost_chat_completions(payload))

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ):
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        for generation in result.generations:
            message = generation.message
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=message.content,
                    tool_calls=getattr(message, "tool_calls", []),
                    invalid_tool_calls=getattr(message, "invalid_tool_calls", []),
                    usage_metadata=message.usage_metadata,
                    response_metadata=message.response_metadata,
                ),
                generation_info=generation.generation_info,
            )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ):
        result = await self._agenerate(messages, stop=stop, run_manager=run_manager, **kwargs)
        for generation in result.generations:
            message = generation.message
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content=message.content,
                    tool_calls=getattr(message, "tool_calls", []),
                    invalid_tool_calls=getattr(message, "invalid_tool_calls", []),
                    usage_metadata=message.usage_metadata,
                    response_metadata=message.response_metadata,
                ),
                generation_info=generation.generation_info,
            )

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> RunnableBinding:
        bound_kwargs = {"tools": self._format_tools(tools)}
        bound_kwargs.update(kwargs)
        return RunnableBinding(bound=self, kwargs=bound_kwargs)
