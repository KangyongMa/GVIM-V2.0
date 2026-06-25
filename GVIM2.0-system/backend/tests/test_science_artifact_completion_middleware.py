"""Tests for GVIM science artifact completion middleware."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.agents.middlewares.science_artifact_completion_middleware import ScienceArtifactCompletionMiddleware


def _runtime(thread_id: str = "thread-1", run_id: str = "run-1"):
    return SimpleNamespace(context={"thread_id": thread_id, "run_id": run_id})


def _final_ai() -> AIMessage:
    return AIMessage(content="done")


def _tool_message(payload: dict, *, name: str = "gvim-science_gvim_science_run_tool", tool_call_id: str = "tc-1") -> ToolMessage:
    return ToolMessage(content=json.dumps(payload), name=name, tool_call_id=tool_call_id)


def _artifact_payload(kind: str, tool_key: str, domain: str = "chemistry") -> dict:
    return {
        "success": True,
        "tool_key": tool_key,
        "domain": domain,
        "tool_result": {"success": True},
        "science_artifacts": [{"kind": kind, "title": kind, "payload": {"success": True}}],
    }


def test_missing_3d_artifact_jumps_back_to_model_and_injects_hidden_reminder():
    mw = ScienceArtifactCompletionMiddleware(enabled=True)
    runtime = _runtime()
    state = {
        "messages": [
            HumanMessage(content="请把咖啡因画到 Ketcher，生成苯的 3D 构象，并查询 BaTiO3 的 Materials Project 证据数据。"),
            _tool_message(_artifact_payload("ketcher", "chemistry_studio_prepare"), name="gvim-science_gvim_chemistry_prepare_studio"),
            _tool_message(_artifact_payload("materials", "materials_project_deep_profile", "materials"), name="gvim-science_gvim_materials_project_deep_profile"),
            _final_ai(),
        ]
    }

    result = mw.after_model(state, runtime)

    assert result == {"jump_to": "model"}

    request = MagicMock()
    request.runtime = runtime
    request.messages = state["messages"]
    request.override.return_value = "patched-request"
    handler = MagicMock(return_value="response")

    assert mw.wrap_model_call(request, handler) == "response"
    reminder = request.override.call_args.kwargs["messages"][-1]
    assert isinstance(reminder, HumanMessage)
    assert reminder.name == "science_artifact_completion_reminder"
    assert reminder.additional_kwargs["hide_from_ui"] is True
    assert "gvim-science_gvim_rdkit_conformer" in reminder.content
    assert "gvim_chemistry_prepare_studio" not in reminder.content


def test_allows_final_answer_when_requested_artifacts_are_present():
    mw = ScienceArtifactCompletionMiddleware(enabled=True)
    state = {
        "messages": [
            HumanMessage(content="把咖啡因画到 Ketcher，并生成苯的 3D 构象。"),
            _tool_message(_artifact_payload("ketcher", "chemistry_studio_prepare"), name="gvim-science_gvim_chemistry_prepare_studio"),
            _tool_message(_artifact_payload("three-d", "rdkit_3d_conformer"), name="gvim-science_gvim_rdkit_conformer"),
            _final_ai(),
        ]
    }

    assert mw.after_model(state, _runtime()) is None


def test_does_not_intervene_while_model_is_still_calling_tools():
    mw = ScienceArtifactCompletionMiddleware(enabled=True)
    state = {
        "messages": [
            HumanMessage(content="生成苯的 3D 构象。"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "gvim-science_gvim_rdkit_conformer",
                        "id": "tc-1",
                        "args": {"smiles": "c1ccccc1"},
                    }
                ],
            ),
        ]
    }

    assert mw.after_model(state, _runtime()) is None


def test_materials_project_api_key_question_is_not_treated_as_data_artifact_request():
    mw = ScienceArtifactCompletionMiddleware(enabled=True)
    state = {
        "messages": [
            HumanMessage(content="如何获取 Materials Project 的 API Key？"),
            _final_ai(),
        ]
    }

    assert mw.after_model(state, _runtime()) is None
