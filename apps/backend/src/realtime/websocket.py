import logging
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket, subprotocol: str | None = None):
        """
        Accepts and registers a new WebSocket connection.
        """
        await websocket.accept(subprotocol=subprotocol)
        self.active_connections.append(websocket)
        logger.info(
            f"New WebSocket client connected. Active connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        """
        Deregisters a closed WebSocket connection.
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket client disconnected. Active connections: {len(self.active_connections)}"
            )

    async def broadcast_transition(self, message: dict):
        """
        Broadcasts a message payload to all active WebSocket clients.
        Fails safe; if a connection is broken, it removes the client and continues.
        """
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(
                    f"Error sending message to WebSocket client: {e}. Mark for removal."
                )
                disconnected.append(connection)

        # Cleanup closed connections found during broadcast
        for conn in disconnected:
            self.disconnect(conn)


# Shared connection manager instance
manager = ConnectionManager()
