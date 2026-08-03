"""Dedicated ASGI entrypoint for horizontally scaled WebSocket workers."""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI

from app.database import init_db
from app.job_queue import job_queue
from app.object_storage import object_storage
from app.photo_safety import photo_safety
from app.main import websocket_endpoint, ws_manager
from app.redis_backend import redis_sessions


ws_app = FastAPI(title="Kindred WebSocket Worker", version="2.5.1")
ws_app.websocket("/ws/{profile_id}")(websocket_endpoint)


@ws_app.on_event("startup")
async def startup():
    redis_sessions.initialize()
    object_storage.initialize()
    photo_safety.initialize()
    init_db()
    await ws_manager.start()


@ws_app.on_event("shutdown")
async def shutdown():
    await ws_manager.stop()


@ws_app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "version": "2.5.1",
        "python": sys.version,
        "worker_role": os.getenv("KINDRED_WORKER_ROLE", "websocket"),
        "redis": redis_sessions.health(),
        "queue": job_queue.health(),
        "object_storage": object_storage.health(),
        "photo_safety": photo_safety.health(),
        "websocket_transport": "redis" if redis_sessions.enabled else "local",
        "active_websockets": sum(len(v) for v in ws_manager.active.values()),
        "pid": os.getpid(),
    }
