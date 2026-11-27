"""Bounded WebSocketManager & EventPublisher for Live Calls monitoring."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
from typing import Any
import uuid

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class SubscriberConnection:
    """Tracks an authorized monitoring WebSocket client and its bounded queue."""

    client_id: str
    websocket: WebSocket
    queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=100)
    )
    call_ids: set[str] = field(default_factory=set)
    subscribe_all: bool = True
    campaign_id: str | None = None
    agent_id: str | None = None


class WebSocketManager:
    """Manages live monitoring WebSocket subscriptions with slow-client backpressure."""

    def __init__(self) -> None:
        self._clients: dict[str, SubscriberConnection] = {}

    def register(self, websocket: WebSocket) -> SubscriberConnection:
        client_id = f"mon_{uuid.uuid4().hex[:10]}"
        conn = SubscriberConnection(client_id=client_id, websocket=websocket)
        self._clients[client_id] = conn
        logger.info("Registered monitoring WS client %s (total=%d)", client_id, len(self._clients))
        return conn

    def unregister(self, client_id: str) -> None:
        if client_id in self._clients:
            self._clients.pop(client_id, None)
            logger.info("Unregistered monitoring WS client %s", client_id)

    def update_subscription(
        self,
        client_id: str,
        *,
        call_ids: list[str] | None = None,
        campaign_id: str | None = None,
        agent_id: str | None = None,
        unsubscribe: bool = False,
    ) -> None:
        conn = self._clients.get(client_id)
        if not conn:
            return
        if unsubscribe and call_ids:
            for cid in call_ids:
                conn.call_ids.discard(cid)
            return

        if call_ids is not None:
            if len(call_ids) == 0 and campaign_id is None and agent_id is None:
                conn.subscribe_all = True
                conn.call_ids.clear()
            else:
                conn.subscribe_all = False
                conn.call_ids.update(call_ids)
        if campaign_id is not None:
            conn.campaign_id = campaign_id
            conn.subscribe_all = False
        if agent_id is not None:
            conn.agent_id = agent_id
            conn.subscribe_all = False

    @staticmethod
    def _matches(conn: SubscriberConnection, message: dict[str, Any]) -> bool:
        if conn.subscribe_all:
            return True
        call_id = message.get("call_id")
        if call_id and call_id in conn.call_ids:
            return True
        meta = message.get("metadata") or {}
        if conn.campaign_id and meta.get("campaign_id") == conn.campaign_id:
            return True
        if conn.agent_id and meta.get("agent_id") == conn.agent_id:
            return True
        return False

    def publish_nonblocking(self, message: dict[str, Any]) -> None:
        """Fan out monitoring events without ever blocking live audio/LLM pipelines."""
        for conn in list(self._clients.values()):
            if not self._matches(conn, message):
                continue
            if conn.queue.full():
                # Drop oldest buffered event to protect memory & prevent slow-client blocking
                try:
                    conn.queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                conn.queue.put_nowait(message)
            except asyncio.QueueFull:
                pass


# Shared singleton hub for live monitoring fan-out
monitoring_ws_hub = WebSocketManager()
