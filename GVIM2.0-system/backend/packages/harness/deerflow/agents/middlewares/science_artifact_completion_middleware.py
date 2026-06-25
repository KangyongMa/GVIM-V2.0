"""Ensure requested GVIM science artifacts are produced before final answer."""

from __future__ import annotations

import json
import re
import threading
from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ModelCallResult, ModelRequest, ModelResponse, hook_config
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.runtime import Runtime

from deerflow.agents.middlewares.todo_middleware import _has_tool_call_intent_or_error

_TOOL_PREFIXES = (
    "gvim-science_",
    "gvim_",
)

_KETCHER_MARKERS = (
    "ketcher",
    "canvas",
    "画到",
    "画在",
    "画入",
    "绘制",
    "草图",
    "结构编辑",
    "二维结构",
    "draw",
    "sketch",
)

_THREE_D_MARKERS = (
    "3d",
    "3-d",
    "3dmol",
    "三维",
    "构象",
    "立体结构",
    "空间结构",
    "conformer",
    "geometry",
    "viewer",
)

_MATERIALS_PROJECT_MARKERS = (
    "materials project",
    "material project",
    "mp-",
    "材料项目",
    "材料数据库",
)

_MATERIALS_ACTION_MARKERS = (
    "查询",
    "搜索",
    "证据",
    "数据",
    "profile",
    "evidence",
    "search",
    "band gap",
    "formation",
    "hull",
    "density",
    "structure",
)

_CONFIG_QUESTION_MARKERS = (
    "api key",
    "apikey",
    "配置",
    "填写",
    "获取",
    "教程",
    "how to get",
    "where to get",
)


def _message_text(message: object) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content or "")


def _is_hidden_human(message: object) -> bool:
    kwargs = getattr(message, "additional_kwargs", {}) or {}
    return isinstance(message, HumanMessage) and bool(kwargs.get("hide_from_ui"))


def _latest_visible_user_text(messages: list[Any]) -> str:
    for message in reversed(messages):
        if isinstance(message, HumanMessage) and not _is_hidden_human(message):
            text = _message_text(message).strip()
            if text:
                return text
    return ""


def _has_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker.lower() in lowered for marker in markers)


def _requested_artifact_kinds(text: str) -> set[str]:
    requested: set[str] = set()
    if not text:
        return requested

    lowered = text.lower()

    if _has_any(text, _KETCHER_MARKERS):
        requested.add("ketcher")

    if _has_any(text, _THREE_D_MARKERS):
        requested.add("three-d")

    material_project_requested = _has_any(text, _MATERIALS_PROJECT_MARKERS) and _has_any(text, _MATERIALS_ACTION_MARKERS)
    api_config_question = _has_any(text, _MATERIALS_PROJECT_MARKERS) and _has_any(text, _CONFIG_QUESTION_MARKERS)
    if material_project_requested and not api_config_question:
        requested.add("materials")

    # Formula-like material requests often omit "Materials Project" after the
    # first mention. Keep this narrow so general chemistry formulas do not turn
    # into materials obligations.
    if re.search(r"\bmp-\d+\b", lowered):
        requested.add("materials")

    return requested


def _parse_json_payload(text: str) -> dict[str, Any] | None:
    text = text.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _artifact_kinds_from_payload(payload: dict[str, Any]) -> set[str]:
    kinds: set[str] = set()

    declared = payload.get("science_artifacts")
    if isinstance(declared, list):
        for artifact in declared:
            if not isinstance(artifact, dict):
                continue
            kind = str(artifact.get("kind") or "").strip()
            if kind in {"ketcher", "three-d", "materials"}:
                kinds.add(kind)

    tool_key = str(payload.get("tool_key") or "").lower()
    domain = str(payload.get("domain") or "").lower()
    result = payload.get("tool_result")
    result_dict = result if isinstance(result, dict) else {}

    if tool_key in {"chemistry_studio_prepare", "structure_studio_prepare"}:
        kinds.add("ketcher")
    if tool_key == "rdkit_3d_conformer":
        kinds.add("three-d")
    if domain == "materials" or "materials" in tool_key:
        kinds.add("materials")

    viewer = str(result_dict.get("viewer") or "").lower()
    source = str(result_dict.get("source") or "").lower()
    if viewer == "3dmol" or result_dict.get("pdb_block") or ("rdkit_native" in source and result_dict.get("molblock")):
        kinds.add("three-d")

    if result_dict.get("ketcher_commands") or result_dict.get("current_structure"):
        kinds.add("ketcher")

    return kinds


def _completed_artifact_kinds(messages: list[Any]) -> set[str]:
    kinds: set[str] = set()
    for message in messages:
        if not isinstance(message, ToolMessage):
            continue

        name = str(getattr(message, "name", "") or "").lower()
        if any(name.startswith(prefix) for prefix in _TOOL_PREFIXES):
            if "prepare_studio" in name:
                kinds.add("ketcher")
            if "rdkit_conformer" in name or "3d_conformer" in name:
                kinds.add("three-d")
            if "materials" in name:
                kinds.add("materials")

        payload = _parse_json_payload(_message_text(message))
        if payload:
            kinds.update(_artifact_kinds_from_payload(payload))
    return kinds


def _format_missing_artifact_reminder(missing: set[str], user_text: str) -> str:
    lines = [
        "<system_reminder>",
        "The current user message requested GVIM science deliverables that do not yet have matching native science artifacts/tool results.",
        "",
        "Original user request:",
        user_text.strip(),
        "",
        "Before giving the final answer, continue with the missing native tool calls:",
    ]
    if "ketcher" in missing:
        lines.append("- Ketcher/canvas deliverable: call `gvim-science_gvim_chemistry_prepare_studio`; structure resolution alone is not enough.")
    if "three-d" in missing:
        lines.append("- 3D/conformer deliverable: resolve the molecule name if needed, then call `gvim-science_gvim_rdkit_conformer` with canonical SMILES.")
    if "materials" in missing:
        lines.append("- Materials Project deliverable: call the relevant `gvim-science_gvim_materials_*` Materials Project tool.")
    lines.extend(
        [
            "",
            "Preserve all returned `science_artifacts` in the tool results. Only produce the final user-facing response after every requested native science artifact is present.",
            "</system_reminder>",
        ]
    )
    return "\n".join(lines)


class ScienceArtifactCompletionMiddleware(AgentMiddleware[AgentState]):
    """Prevent final answers that omit requested native science artifacts."""

    _MAX_REMINDERS_PER_RUN = 2
    _MAX_TRACKED_RUNS = 4096

    def __init__(self, *, enabled: bool | None = None) -> None:
        super().__init__()
        self._enabled_override = enabled
        self._enabled_cache: bool | None = None
        self._lock = threading.Lock()
        self._pending_reminders: dict[tuple[str, str], list[str]] = {}
        self._reminder_counts: dict[tuple[str, str], int] = {}
        self._touch_order: dict[tuple[str, str], int] = {}
        self._next_order = 0

    def _is_enabled(self) -> bool:
        if self._enabled_override is not None:
            return self._enabled_override
        if self._enabled_cache is not None:
            return self._enabled_cache
        try:
            from deerflow.config.extensions_config import ExtensionsConfig

            self._enabled_cache = "gvim-science" in ExtensionsConfig.from_file().get_enabled_mcp_servers()
        except Exception:
            self._enabled_cache = False
        return self._enabled_cache

    @staticmethod
    def _runtime_key(runtime: Runtime) -> tuple[str, str]:
        context = getattr(runtime, "context", None)
        if isinstance(context, dict):
            thread_id = str(context.get("thread_id") or "default")
            run_id = str(context.get("run_id") or "default")
            return thread_id, run_id
        return "default", "default"

    def _drop_key_locked(self, key: tuple[str, str]) -> None:
        self._pending_reminders.pop(key, None)
        self._reminder_counts.pop(key, None)
        self._touch_order.pop(key, None)

    def _touch_locked(self, key: tuple[str, str]) -> None:
        self._next_order += 1
        self._touch_order[key] = self._next_order

    def _all_keys_locked(self) -> set[tuple[str, str]]:
        keys = set(self._pending_reminders)
        keys.update(self._reminder_counts)
        keys.update(self._touch_order)
        return keys

    def _prune_locked(self, protected_key: tuple[str, str]) -> None:
        overflow = len(self._all_keys_locked()) - self._MAX_TRACKED_RUNS
        if overflow <= 0:
            return
        candidates = [key for key in self._all_keys_locked() if key != protected_key]
        candidates.sort(key=lambda key: self._touch_order.get(key, 0))
        for key in candidates[:overflow]:
            self._drop_key_locked(key)

    def _queue_reminder(self, runtime: Runtime, reminder: str) -> None:
        key = self._runtime_key(runtime)
        with self._lock:
            self._pending_reminders.setdefault(key, []).append(reminder)
            self._reminder_counts[key] = self._reminder_counts.get(key, 0) + 1
            self._touch_locked(key)
            self._prune_locked(key)

    def _drain_reminders(self, runtime: Runtime) -> list[str]:
        key = self._runtime_key(runtime)
        with self._lock:
            reminders = self._pending_reminders.pop(key, [])
            if reminders:
                self._touch_locked(key)
            return reminders

    def _reminder_count(self, runtime: Runtime) -> int:
        key = self._runtime_key(runtime)
        with self._lock:
            return self._reminder_counts.get(key, 0)

    def _clear_other_runs(self, runtime: Runtime) -> None:
        current_thread_id, current_run_id = self._runtime_key(runtime)
        with self._lock:
            for key in list(self._all_keys_locked()):
                if key[0] == current_thread_id and key[1] != current_run_id:
                    self._drop_key_locked(key)

    def _clear_current_run(self, runtime: Runtime) -> None:
        key = self._runtime_key(runtime)
        with self._lock:
            self._drop_key_locked(key)

    @override
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self._clear_other_runs(runtime)
        return None

    @override
    async def abefore_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self._clear_other_runs(runtime)
        return None

    @hook_config(can_jump_to=["model"])
    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        if not self._is_enabled():
            return None

        messages = list(state.get("messages") or [])
        last_ai = next((message for message in reversed(messages) if isinstance(message, AIMessage)), None)
        if not last_ai or _has_tool_call_intent_or_error(last_ai):
            return None

        user_text = _latest_visible_user_text(messages)
        requested = _requested_artifact_kinds(user_text)
        if not requested:
            return None

        completed = _completed_artifact_kinds(messages)
        missing = requested - completed
        if not missing:
            return None

        if self._reminder_count(runtime) >= self._MAX_REMINDERS_PER_RUN:
            return None

        self._queue_reminder(runtime, _format_missing_artifact_reminder(missing, user_text))
        return {"jump_to": "model"}

    @hook_config(can_jump_to=["model"])
    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        return self.after_model(state, runtime)

    @staticmethod
    def _dedupe_reminders(reminders: list[str]) -> str:
        return "\n\n".join(dict.fromkeys(reminders))

    def _augment_request(self, request: ModelRequest) -> ModelRequest:
        reminders = self._drain_reminders(request.runtime)
        if not reminders:
            return request

        return request.override(
            messages=[
                *request.messages,
                HumanMessage(
                    content=self._dedupe_reminders(reminders),
                    name="science_artifact_completion_reminder",
                    additional_kwargs={"hide_from_ui": True},
                ),
            ]
        )

    @override
    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelCallResult:
        return handler(self._augment_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        return await handler(self._augment_request(request))

    @override
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self._clear_current_run(runtime)
        return None

    @override
    async def aafter_agent(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        self._clear_current_run(runtime)
        return None
