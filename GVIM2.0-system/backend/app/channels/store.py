"""JSON-backed channel session and message store."""

from __future__ import annotations

import json
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from deerflow.config.paths import get_paths


class ChannelStore:
    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path) if path is not None else get_paths().base_dir / "channels" / "store.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data = self._load()

    @staticmethod
    def _session_key(channel_name: str, chat_id: str, topic_id: str | None = None) -> str:
        return f"{channel_name}:{chat_id}:{topic_id}" if topic_id else f"{channel_name}:{chat_id}"

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"sessions": {}, "messages": []}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except Exception:
            return {"sessions": {}, "messages": []}
        if not isinstance(data, dict):
            return {"sessions": {}, "messages": []}
        if "sessions" not in data and "messages" not in data:
            return {"sessions": self._migrate_legacy_sessions(data), "messages": []}
        if not isinstance(data.get("sessions"), dict):
            data["sessions"] = {}
        if not isinstance(data.get("messages"), list):
            data["messages"] = []
        return data

    @staticmethod
    def _migrate_legacy_sessions(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        sessions: dict[str, dict[str, Any]] = {}
        for key, entry in data.items():
            if not isinstance(entry, dict):
                continue
            parts = key.split(":", 2)
            channel_name = parts[0]
            chat_id = parts[1] if len(parts) > 1 else ""
            topic_id = parts[2] if len(parts) > 2 else None
            sessions[key] = {
                "channel_name": channel_name,
                "chat_id": chat_id,
                "topic_id": topic_id,
                "thread_id": entry.get("thread_id", ""),
                "user_id": entry.get("user_id", ""),
                "created_at": entry.get("created_at", time.time()),
                "updated_at": entry.get("updated_at", time.time()),
            }
        return sessions

    def _save_locked(self) -> None:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self._path.parent,
            suffix=".tmp",
            delete=False,
        ) as handle:
            json.dump(self._data, handle, ensure_ascii=False, indent=2)
            temp_name = handle.name
        Path(temp_name).replace(self._path)

    def get_thread_id(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> str | None:
        entry = self._data["sessions"].get(self._session_key(channel_name, chat_id, topic_id))
        if isinstance(entry, dict):
            thread_id = entry.get("thread_id")
            return str(thread_id) if thread_id else None
        return None

    def set_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
        user_id: str = "",
    ) -> None:
        with self._lock:
            key = self._session_key(channel_name, chat_id, topic_id)
            now = time.time()
            existing = self._data["sessions"].get(key)
            self._data["sessions"][key] = {
                "channel_name": channel_name,
                "chat_id": chat_id,
                "topic_id": topic_id,
                "thread_id": thread_id,
                "user_id": user_id,
                "created_at": existing.get("created_at", now) if isinstance(existing, dict) else now,
                "updated_at": now,
            }
            self._save_locked()

    def remove(self, channel_name: str, chat_id: str, topic_id: str | None = None) -> bool:
        with self._lock:
            if topic_id is not None:
                deleted = self._data["sessions"].pop(
                    self._session_key(channel_name, chat_id, topic_id),
                    None,
                ) is not None
            else:
                prefix = self._session_key(channel_name, chat_id)
                keys = [
                    item
                    for item in self._data["sessions"]
                    if item == prefix or item.startswith(prefix + ":")
                ]
                deleted = bool(keys)
                for item in keys:
                    self._data["sessions"].pop(item, None)
            if deleted:
                self._save_locked()
            return deleted

    def remove_thread_id(
        self,
        channel_name: str,
        chat_id: str,
        thread_id: str,
        *,
        topic_id: str | None = None,
    ) -> bool:
        with self._lock:
            key = self._session_key(channel_name, chat_id, topic_id)
            entry = self._data["sessions"].get(key)
            if not isinstance(entry, dict) or entry.get("thread_id") != thread_id:
                return False
            self._data["sessions"].pop(key, None)
            self._save_locked()
            return True

    def list_sessions(self, channel_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        sessions = [
            entry
            for entry in self._data["sessions"].values()
            if isinstance(entry, dict)
            and (channel_name is None or entry.get("channel_name") == channel_name)
        ]
        sessions.sort(key=lambda item: float(item.get("updated_at") or 0), reverse=True)
        return sessions[:limit]

    def list_entries(self, channel_name: str | None = None) -> list[dict[str, Any]]:
        return self.list_sessions(channel_name=channel_name, limit=1000)

    def append_message(self, item: dict[str, Any]) -> None:
        with self._lock:
            record = {"created_at": time.time(), **item}
            messages = self._data["messages"]
            messages.append(record)
            self._data["messages"] = messages[-500:]
            self._save_locked()

    def list_messages(
        self,
        *,
        channel_name: str | None = None,
        chat_id: str | None = None,
        thread_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        messages = [
            item
            for item in self._data["messages"]
            if isinstance(item, dict)
            and (channel_name is None or item.get("channel_name") == channel_name)
            and (chat_id is None or item.get("chat_id") == chat_id)
            and (thread_id is None or item.get("thread_id") == thread_id)
        ]
        messages.sort(key=lambda item: float(item.get("created_at") or 0), reverse=True)
        return messages[:limit]


_store: ChannelStore | None = None


def get_channel_store() -> ChannelStore:
    global _store
    if _store is None:
        _store = ChannelStore()
    return _store
