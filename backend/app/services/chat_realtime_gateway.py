from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as redis
import structlog
from fastapi import WebSocket


class ChatRealtimeGateway:
    def __init__(self, redis_url: str, channel: str):
        self.redis_url = redis_url
        self.channel = channel
        self.logger = structlog.get_logger(__name__)

        self._connections: set[WebSocket] = set()
        self._connections_lock = asyncio.Lock()

        self._publisher: redis.Redis | None = None
        self._subscriber_client: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._listen_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        try:
            self._publisher = redis.from_url(self.redis_url, decode_responses=True)
            await self._publisher.ping()

            self._subscriber_client = redis.from_url(self.redis_url, decode_responses=True)
            self._pubsub = self._subscriber_client.pubsub(ignore_subscribe_messages=True)
            await self._pubsub.subscribe(self.channel)

            self._listen_task = asyncio.create_task(self._listen_loop(), name="chat-redis-listener")
            self.logger.info("chat.gateway.started", channel=self.channel)
        except Exception as exc:
            self.logger.warning("chat.gateway.redis_unavailable", error=str(exc), channel=self.channel)
            await self._cleanup_redis_handles()

    async def stop(self) -> None:
        if self._listen_task:
            self._listen_task.cancel()
            try:
                await self._listen_task
            except asyncio.CancelledError:
                pass
            self._listen_task = None

        await self._cleanup_redis_handles()

        async with self._connections_lock:
            connections = list(self._connections)
            self._connections.clear()

        for websocket in connections:
            await websocket.close(code=1001)

        self.logger.info("chat.gateway.stopped")

    async def _cleanup_redis_handles(self) -> None:
        if self._pubsub is not None:
            try:
                await self._pubsub.close()
            except Exception:
                pass
            self._pubsub = None

        if self._subscriber_client is not None:
            try:
                await self._subscriber_client.close()
            except Exception:
                pass
            self._subscriber_client = None

        if self._publisher is not None:
            try:
                await self._publisher.close()
            except Exception:
                pass
            self._publisher = None

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._connections_lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._connections_lock:
            self._connections.discard(websocket)

    async def publish_event(self, event: dict[str, Any]) -> None:
        raw_payload = json.dumps(event, default=str)
        if self._publisher is not None:
            try:
                await self._publisher.publish(self.channel, raw_payload)
                return
            except Exception as exc:
                self.logger.warning("chat.gateway.publish_failed", error=str(exc))

        # Fallback for local-dev when Redis is down.
        await self._broadcast_raw(raw_payload)

    async def _listen_loop(self) -> None:
        assert self._pubsub is not None
        while True:
            try:
                message = await self._pubsub.get_message(timeout=1.0)
                if message and message.get("type") == "message":
                    payload = message.get("data")
                    if isinstance(payload, bytes):
                        payload = payload.decode("utf-8")
                    if isinstance(payload, str):
                        await self._broadcast_raw(payload)
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self.logger.warning("chat.gateway.listen_failed", error=str(exc))
                await asyncio.sleep(1.0)

    async def _broadcast_raw(self, raw_payload: str) -> None:
        async with self._connections_lock:
            sockets = list(self._connections)

        stale_connections: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_text(raw_payload)
            except Exception:
                stale_connections.append(websocket)

        if stale_connections:
            async with self._connections_lock:
                for websocket in stale_connections:
                    self._connections.discard(websocket)
