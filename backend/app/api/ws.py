"""
WebSocket manager — supports per-org isolated broadcast channels.

Clients connect with ?org_id=<id> so that a batch run for org A does not
bleed events into org B's live feed.
"""
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        # org_id → list of active WebSocket connections
        self._connections: Dict[int, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, org_id: int) -> None:
        await websocket.accept()
        self._connections[org_id].append(websocket)

    def disconnect(self, websocket: WebSocket, org_id: int) -> None:
        conns = self._connections.get(org_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast_to_org(self, org_id: int, message: dict) -> None:
        """Send a JSON message to all connections belonging to this org."""
        from fastapi.encoders import jsonable_encoder
        import logging
        payload = jsonable_encoder(message)
        dead: List[WebSocket] = []
        for connection in list(self._connections.get(org_id, [])):
            try:
                await connection.send_json(payload)
            except Exception as e:
                logging.getLogger(__name__).warning(f"WebSocket broadcast error for org {org_id}: {e}")
                dead.append(connection)
        for ws in dead:
            self.disconnect(ws, org_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast to ALL connected clients (legacy / debug use only)."""
        for org_id in list(self._connections.keys()):
            await self.broadcast_to_org(org_id, message)


manager = ConnectionManager()
