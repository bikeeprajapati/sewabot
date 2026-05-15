from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json

router = APIRouter()

# ── Connection Manager ───────────────────────────────────
class ConnectionManager:
    """
    Manages all active WebSocket connections.
    Each user gets their own channel identified by user_id.

    Think of it like a telephone exchange:
    - connect()   → plug in a phone line
    - disconnect()→ unplug the line
    - send()      → call a specific person
    - broadcast() → announce to everyone
    """

    def __init__(self):
        # user_id → WebSocket connection
        self.active: Dict[str, WebSocket] = {}

    async def connect(self, user_id: str, ws: WebSocket):
        await ws.accept()
        self.active[user_id] = ws
        print(f"[WS] Connected: {user_id} | Total: {len(self.active)}")

    def disconnect(self, user_id: str):
        self.active.pop(user_id, None)
        print(f"[WS] Disconnected: {user_id} | Total: {len(self.active)}")

    async def send(self, user_id: str, data: dict):
        """Send a message to a specific user."""
        ws = self.active.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                print(f"[WS] Send error to {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, data: dict):
        """Send a message to all connected users."""
        disconnected = []
        for user_id, ws in self.active.items():
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(user_id)
        for uid in disconnected:
            self.disconnect(uid)

    def is_connected(self, user_id: str) -> bool:
        return user_id in self.active

    def connected_users(self) -> list:
        return list(self.active.keys())


# ── Global manager instance ──────────────────────────────
manager = ConnectionManager()


# ════════════════════════════════════════════════════════
# CLIENT WEBSOCKET
# Client connects → receives live worker location updates
# ════════════════════════════════════════════════════════
@router.websocket("/ws/client/{client_id}")
async def client_ws(ws: WebSocket, client_id: str):
    """
    Client connects here after booking a worker.
    Receives real-time location updates of their worker.
    """
    await manager.connect(f"client_{client_id}", ws)
    try:
        # Confirm connection
        await ws.send_json({
            "type":    "connected",
            "message": "Connected to SewaBot live tracking",
            "user_id": client_id
        })

        # Keep connection alive — listen for any client messages
        while True:
            data = await ws.receive_text()
            msg  = json.loads(data)

            # Client can send ping to keep connection alive
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(f"client_{client_id}")


# ════════════════════════════════════════════════════════
# WORKER WEBSOCKET
# Worker connects → sends live GPS location every 5 seconds
# ════════════════════════════════════════════════════════
@router.websocket("/ws/worker/{worker_id}")
async def worker_ws(ws: WebSocket, worker_id: str):
    """
    Worker connects here when they accept a job.
    Sends GPS coordinates every 5 seconds.
    Server relays location to the matched client.
    """
    await manager.connect(f"worker_{worker_id}", ws)
    try:
        await ws.send_json({
            "type":    "connected",
            "message": "Worker connected to SewaBot",
            "worker_id": worker_id
        })

        while True:
            # Receive location from worker
            data = await ws.receive_text()
            msg  = json.loads(data)

            if msg.get("type") == "location":
                lat       = msg.get("lat")
                lng       = msg.get("lng")
                client_id = msg.get("client_id")   # who to notify

                print(f"[WS] Worker {worker_id} at ({lat}, {lng})")

                # Relay location to client
                if client_id:
                    await manager.send(f"client_{client_id}", {
                        "type":      "worker_location",
                        "worker_id": worker_id,
                        "lat":       lat,
                        "lng":       lng,
                        "message":   "Worker is on the way"
                    })

            elif msg.get("type") == "job_accepted":
                client_id = msg.get("client_id")
                if client_id:
                    await manager.send(f"client_{client_id}", {
                        "type":      "job_accepted",
                        "worker_id": worker_id,
                        "message":   "Your worker has accepted the job and is on the way!"
                    })

            elif msg.get("type") == "job_completed":
                client_id = msg.get("client_id")
                if client_id:
                    await manager.send(f"client_{client_id}", {
                        "type":    "job_completed",
                        "message": "Job completed! Please leave a review."
                    })

            elif msg.get("type") == "ping":
                await ws.send_json({"type": "pong"})

    except WebSocketDisconnect:
        manager.disconnect(f"worker_{worker_id}")


# ── Status endpoint ──────────────────────────────────────
@router.get("/ws/status")
def ws_status():
    """Shows all currently connected WebSocket users."""
    return {
        "connected_users": manager.connected_users(),
        "total":len(manager.active)
    }