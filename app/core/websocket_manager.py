import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        # Maps user_id -> set of active WebSockets
        self.user_connections: Dict[int, Set[WebSocket]] = {}
        # Maps organization_id -> set of active WebSockets
        self.org_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int, organization_id: int):
        await websocket.accept()
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

        if organization_id not in self.org_connections:
            self.org_connections[organization_id] = set()
        self.org_connections[organization_id].add(websocket)
        logger.info(f"WebSocket connected for user {user_id} in org {organization_id}")

    def disconnect(self, websocket: WebSocket, user_id: int, organization_id: int):
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

        if organization_id in self.org_connections:
            self.org_connections[organization_id].discard(websocket)
            if not self.org_connections[organization_id]:
                del self.org_connections[organization_id]
        logger.info(f"WebSocket disconnected for user {user_id} in org {organization_id}")

    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.user_connections:
            payload = json.dumps(message)
            dead_sockets = set()
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Failed to send to user {user_id}: {e}")
                    dead_sockets.add(connection)
            for dead in dead_sockets:
                self.user_connections[user_id].discard(dead)

    async def broadcast_to_org(self, message: dict, organization_id: int):
        if organization_id in self.org_connections:
            payload = json.dumps(message)
            dead_sockets = set()
            for connection in self.org_connections[organization_id]:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.warning(f"Failed to broadcast to org {organization_id}: {e}")
                    dead_sockets.add(connection)
            for dead in dead_sockets:
                self.org_connections[organization_id].discard(dead)


ws_manager = WebSocketManager()
