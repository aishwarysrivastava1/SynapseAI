import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class RealtimeConsumer(AsyncWebsocketConsumer):
    ngo_id: str = "global"

    async def connect(self):
        qs = self.scope.get("query_string", b"").decode()
        params = {}
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        token = params.get("token")

        if token:
            try:
                from apps.core.auth_utils import decode_token_payload
                payload = decode_token_payload(token)
                self.ngo_id = payload.get("ngo_id") or "global"
            except Exception as e:
                logger.warning("WS auth failed: %s", e)
                await self.close(code=1008)
                return

        await self.accept()
        from services.realtime_events import realtime_bus
        await realtime_bus.connect(self.ngo_id, self.channel_name)
        await self.send(text_data=json.dumps({
            "event": "connected", "payload": {"ngo_id": self.ngo_id}
        }))

    async def disconnect(self, code):
        from services.realtime_events import realtime_bus
        await realtime_bus.disconnect(self.ngo_id, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if text_data and text_data.strip().lower() == "ping":
            await self.send(text_data=json.dumps({"event": "pong", "payload": {}}))

    async def realtime_message(self, event):
        await self.send(text_data=json.dumps(event["message"]))
