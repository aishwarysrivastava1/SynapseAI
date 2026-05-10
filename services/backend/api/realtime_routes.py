from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from jose import JWTError

from middleware.rbac import get_current_user, CurrentUser
from services.live_location_cache import live_location_cache
from services.realtime_events import realtime_bus
from utils.auth_utils import decode_token, is_token_blacklisted

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/status")
async def realtime_status(user: CurrentUser = Depends(get_current_user)):
    """Internal bus statistics — requires a valid JWT."""
    return {**realtime_bus.stats()}


@router.websocket("/ws")
async def realtime_ws(websocket: WebSocket):
    # Accept token from query param OR Authorization header
    token = websocket.query_params.get("token")
    if not token:
        auth_header = websocket.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        await websocket.close(code=1008, reason="Missing token")
        return

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        ngo_id  = payload.get("ngo_id")
        jti     = payload.get("jti")

        if not user_id:
            raise JWTError("Missing sub claim")
        if not ngo_id:
            # Reject tokens without an ngo_id — never fall back to "global"
            await websocket.close(code=1008, reason="Token missing ngo_id claim")
            return
        if jti and await is_token_blacklisted(jti):
            await websocket.close(code=1008, reason="Token has been revoked")
            return
    except (JWTError, KeyError):
        await websocket.close(code=1008, reason="Invalid token")
        return

    await realtime_bus.connect(ngo_id, websocket)
    try:
        await websocket.send_json({"event": "connected", "payload": {"ngo_id": ngo_id}})
        while True:
            message = await websocket.receive_text()
            if message.strip().lower() == "ping":
                await websocket.send_json({"event": "pong", "payload": {}})
    except WebSocketDisconnect:
        logger.debug("Realtime websocket disconnected for ngo scope %s", ngo_id)
    finally:
        await realtime_bus.disconnect(ngo_id, websocket)
