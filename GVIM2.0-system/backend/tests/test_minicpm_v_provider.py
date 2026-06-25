from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from deerflow.config.app_config import AppConfig
from deerflow.config.model_config import ModelConfig
from deerflow.config.sandbox_config import SandboxConfig
from deerflow.models import factory as factory_module
from deerflow.models.minicpm_v_provider import MiniCPMV46ChatModel


def test_minicpm_provider_builds_multimodal_payload():
    model = MiniCPMV46ChatModel(
        model="minicpm-v-4.6",
        endpoint_url="http://127.0.0.1:8080/v1/chat/completions",
        max_tokens=512,
    )

    payload = model._build_payload(
        [
            HumanMessage(
                content=[
                    {"type": "text", "text": "Describe this image."},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
                ]
            )
        ]
    )

    assert payload["model"] == "minicpm-v-4.6"
    assert payload["max_tokens"] == 512
    assert payload["messages"][0] == {
        "role": "user",
        "content": [
            {"type": "text", "text": "Describe this image."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,AAA"}},
        ],
    }


def test_minicpm_provider_converts_tool_messages_and_tool_calls():
    model = MiniCPMV46ChatModel()

    payload = model._build_payload(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "read_file",
                        "args": {"path": "/mnt/user-data/workspace/a.txt"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(content="file content", tool_call_id="call_1"),
        ]
    )

    assert payload["messages"][0]["role"] == "assistant"
    assert payload["messages"][0]["tool_calls"][0]["function"]["name"] == "read_file"
    assert payload["messages"][0]["tool_calls"][0]["function"]["arguments"] == '{"path": "/mnt/user-data/workspace/a.txt"}'
    assert payload["messages"][1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "file content",
    }


def test_minicpm_provider_parse_response_with_usage_and_tool_call():
    model = MiniCPMV46ChatModel()

    result = model._parse_response(
        {
            "model": "minicpm-v-4.6",
            "choices": [
                {
                    "finish_reason": "tool_calls",
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "bash", "arguments": '{"cmd": "pwd"}'},
                            }
                        ],
                    },
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
        }
    )

    message = result.generations[0].message
    assert message.tool_calls == [{"name": "bash", "args": {"cmd": "pwd"}, "id": "call_1", "type": "tool_call"}]
    assert message.usage_metadata == {"input_tokens": 3, "output_tokens": 5, "total_tokens": 8}
    assert message.response_metadata["model_provider"] == "minicpm-v"


def test_minicpm_provider_bind_tools_uses_deerflow_bound_model():
    @tool
    def read_file(path: str) -> str:
        """Read a file."""
        return path

    model = MiniCPMV46ChatModel()
    bound = model.bind_tools([read_file], tool_choice="auto")

    assert bound.bound is model
    assert bound.kwargs["tool_choice"] == "auto"
    assert bound.kwargs["tools"][0]["type"] == "function"
    assert bound.kwargs["tools"][0]["function"]["name"] == "read_file"


def test_model_factory_loads_minicpm_provider_natively(monkeypatch):
    app_config = AppConfig(
        models=[
            ModelConfig(
                name="minicpm-v-4.6",
                display_name="MiniCPM-V 4.6",
                description=None,
                use="deerflow.models.minicpm_v_provider:MiniCPMV46ChatModel",
                model="minicpm-v-4.6",
                endpoint_url="http://127.0.0.1:8080/v1/chat/completions",
                supports_vision=True,
            )
        ],
        sandbox=SandboxConfig(use="deerflow.sandbox.local:LocalSandboxProvider"),
    )
    monkeypatch.setattr(factory_module, "get_app_config", lambda: app_config)
    monkeypatch.setattr(factory_module, "build_tracing_callbacks", lambda: [])

    model = factory_module.create_chat_model(name="minicpm-v-4.6")

    assert isinstance(model, MiniCPMV46ChatModel)
    assert model.endpoint_url == "http://127.0.0.1:8080/v1/chat/completions"
