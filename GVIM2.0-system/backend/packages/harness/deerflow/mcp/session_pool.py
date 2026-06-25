"""Persistent MCP session pool for stateful tool calls.

When MCP tools are loaded via langchain-mcp-adapters with ``session=None``,
each tool call creates a new MCP session. For stateful servers like Playwright,
this means browser state (opened pages, filled forms) is lost between calls.

This module provides a session pool that maintains persistent MCP sessions,
scoped by ``(server_name, scope_key)``. Consecutive tool calls in the same scope
share server-side state, and sessions are evicted in LRU order at capacity.
"""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import OrderedDict
from concurrent.futures import TimeoutError as FutureTimeoutError
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from mcp import ClientSession

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class _ManagedSession:
    """A session owned by a long-lived task in one event loop.

    MCP stdio sessions use anyio cancel scopes internally. Those scopes must be
    entered and exited by the same task, so the pool must not call a stored
    async context manager's ``__aexit__`` from an arbitrary cleanup task.
    """

    session: ClientSession
    loop: asyncio.AbstractEventLoop
    close_event: asyncio.Event
    task: asyncio.Task[None]


class MCPSessionPool:
    """Manages persistent MCP sessions scoped by ``(server_name, scope_key)``."""

    MAX_SESSIONS = 256
    SESSION_CLOSE_TIMEOUT = 5.0  # seconds to wait for owner-task shutdown

    def __init__(self) -> None:
        self._entries: OrderedDict[tuple[str, str], _ManagedSession] = OrderedDict()
        # threading.Lock is not bound to any event loop, so it is safe to
        # acquire from both async paths and sync/worker-thread paths.
        self._lock = threading.Lock()

    async def get_session(
        self,
        server_name: str,
        scope_key: str,
        connection: dict[str, Any],
    ) -> ClientSession:
        """Get or create a persistent MCP session.

        If an existing session was created in a different event loop (e.g. the
        sync-wrapper path), it is closed and replaced with a fresh one in the
        current loop.
        """
        key = (server_name, scope_key)
        current_loop = asyncio.get_running_loop()

        sessions_to_close: list[tuple[tuple[str, str], _ManagedSession]] = []
        with self._lock:
            if key in self._entries:
                managed = self._entries[key]
                if managed.loop is current_loop and not managed.loop.is_closed() and not managed.task.done():
                    self._entries.move_to_end(key)
                    return managed.session

                # The old session is tied to a different or stale loop.
                self._entries.pop(key)
                sessions_to_close.append((key, managed))

            while len(self._entries) >= self.MAX_SESSIONS:
                oldest_key, managed = self._entries.popitem(last=False)
                sessions_to_close.append((oldest_key, managed))

        for close_key, managed in sessions_to_close:
            await self._close_managed(close_key, managed)

        managed = await self._start_managed_session(key, connection)

        with self._lock:
            self._entries[key] = managed

        logger.info("Created persistent MCP session for %s/%s", server_name, scope_key)
        return managed.session

    async def _session_owner(
        self,
        key: tuple[str, str],
        connection: dict[str, Any],
        ready: asyncio.Future[_ManagedSession],
        close_event: asyncio.Event,
    ) -> None:
        """Open and close an MCP session from one owning task."""
        from langchain_mcp_adapters.sessions import create_session

        loop = asyncio.get_running_loop()
        try:
            async with create_session(connection) as session:
                await session.initialize()
                task = asyncio.current_task()
                if task is None:
                    raise RuntimeError("MCP session owner task is unavailable")

                managed = _ManagedSession(
                    session=session,
                    loop=loop,
                    close_event=close_event,
                    task=task,
                )
                if not ready.done():
                    ready.set_result(managed)
                await close_event.wait()
        except BaseException as exc:
            if not ready.done():
                ready.set_exception(exc)
                return
            raise

    async def _start_managed_session(
        self,
        key: tuple[str, str],
        connection: dict[str, Any],
    ) -> _ManagedSession:
        loop = asyncio.get_running_loop()
        ready: asyncio.Future[_ManagedSession] = loop.create_future()
        close_event = asyncio.Event()
        task = loop.create_task(
            self._session_owner(key, connection, ready, close_event),
            name=f"mcp-session:{key[0]}:{key[1]}",
        )

        try:
            managed = await asyncio.shield(ready)
        except BaseException:
            task.cancel()
            with suppress(BaseException):
                await task
            raise

        task.add_done_callback(lambda completed: self._owner_task_done(key, managed, completed))
        return managed

    def _owner_task_done(
        self,
        key: tuple[str, str],
        managed: _ManagedSession,
        task: asyncio.Task[None],
    ) -> None:
        self._discard_entry_if_current(key, managed)
        with suppress(asyncio.CancelledError):
            exc = task.exception()
            if exc is not None and not managed.close_event.is_set():
                logger.warning(
                    "MCP session owner task failed for %s",
                    key,
                    exc_info=(type(exc), exc, exc.__traceback__),
                )

    def _discard_entry_if_current(self, key: tuple[str, str], managed: _ManagedSession) -> None:
        with self._lock:
            if self._entries.get(key) is managed:
                self._entries.pop(key, None)

    async def _signal_and_wait(self, managed: _ManagedSession) -> None:
        managed.close_event.set()
        if managed.task is asyncio.current_task():
            return
        await asyncio.shield(managed.task)

    async def _close_managed(self, key: tuple[str, str], managed: _ManagedSession) -> None:
        """Close one managed session without exiting its context from this task."""
        if managed.loop.is_closed():
            return

        try:
            current_loop = asyncio.get_running_loop()
            if managed.loop is current_loop:
                await asyncio.wait_for(
                    self._signal_and_wait(managed),
                    timeout=self.SESSION_CLOSE_TIMEOUT,
                )
            elif managed.loop.is_running():
                future = asyncio.run_coroutine_threadsafe(self._signal_and_wait(managed), managed.loop)
                await asyncio.wait_for(
                    asyncio.wrap_future(future),
                    timeout=self.SESSION_CLOSE_TIMEOUT,
                )
            else:
                logger.debug("Skipping stopped-loop MCP session close for %s", key)
        except (TimeoutError, FutureTimeoutError):
            logger.warning("Timed out closing MCP session %s", key, exc_info=True)
        except Exception:
            logger.warning("Error closing MCP session %s", key, exc_info=True)

    async def close_scope(self, scope_key: str) -> None:
        """Close all sessions for a given scope (e.g. thread_id)."""
        with self._lock:
            keys = [key for key in self._entries if key[1] == scope_key]
            sessions = [(key, self._entries[key]) for key in keys]
            for key in keys:
                self._entries.pop(key, None)

        for key, managed in sessions:
            await self._close_managed(key, managed)

    async def close_server(self, server_name: str) -> None:
        """Close all sessions for a given server."""
        with self._lock:
            keys = [key for key in self._entries if key[0] == server_name]
            sessions = [(key, self._entries[key]) for key in keys]
            for key in keys:
                self._entries.pop(key, None)

        for key, managed in sessions:
            await self._close_managed(key, managed)

    async def close_all(self) -> None:
        """Close every managed session."""
        with self._lock:
            sessions = list(self._entries.items())
            self._entries.clear()

        for key, managed in sessions:
            await self._close_managed(key, managed)

    def close_all_sync(self) -> None:
        """Close all sessions using their owning event loops (synchronous).

        The owner task performs the actual async-context exit. If this method is
        called from the same running loop as a managed session, it can only
        signal shutdown; callers in async contexts should prefer ``close_all``.
        """
        with self._lock:
            entries = list(self._entries.items())
            self._entries.clear()

        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        for key, managed in entries:
            loop = managed.loop
            if loop.is_closed():
                continue

            try:
                if loop.is_running():
                    if loop is current_loop:
                        managed.close_event.set()
                        continue
                    future = asyncio.run_coroutine_threadsafe(self._signal_and_wait(managed), loop)
                    future.result(timeout=self.SESSION_CLOSE_TIMEOUT)
                else:
                    if current_loop is not None and current_loop.is_running():
                        logger.debug("Skipping stopped-loop MCP session close for %s", key)
                        continue
                    loop.run_until_complete(self._signal_and_wait(managed))
            except FutureTimeoutError:
                logger.debug("Timed out closing MCP session %s during sync close", key, exc_info=True)
            except Exception:
                logger.debug("Error closing MCP session %s during sync close", key, exc_info=True)


# ------------------------------------------------------------------
# Module-level singleton
# ------------------------------------------------------------------

_pool: MCPSessionPool | None = None
_pool_lock = threading.Lock()


def get_session_pool() -> MCPSessionPool:
    """Return the global session-pool singleton."""
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = MCPSessionPool()
    return _pool


def reset_session_pool() -> None:
    """Reset the singleton (for tests)."""
    global _pool
    _pool = None
