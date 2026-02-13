# server.py
import asyncio
import json
import logging
from typing import Optional, Set
from pathlib import Path
import os
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# BASE_DIR = Path(__file__).resolve().parent.parent
# UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", BASE_DIR / "uploads"))


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
clients: list[WebSocket] = []
app = FastAPI()


# app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")
# app.mount("/audio", StaticFiles(directory=str(UPLOADS_DIR)), name="audio")
# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or replace with ["http://localhost:5173"] for tighter security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnimationPayload(BaseModel):
    animate_type: str  # "start_vrma", "start_mixamo", or "auto" (auto-detect from extension)
    animation_url: str
    play_once: Optional[bool] = False
    crop_start: Optional[float] = 0.0  # seconds to crop from start
    crop_end: Optional[float] = 0.0  # seconds to crop from end
    lock_position: Optional[bool] = False  # If true, animation plays in place (no root motion)
    track_position: Optional[bool] = True  # If true, character stays at end position after animation




class CombinedPayload(BaseModel):
    animation_url: str
    audio_path: str
    expression: str = "neutral"
    delay: float = 0.0  # seconds


class SetStateRequest(BaseModel):
    """Set the VRM avatar's animation state"""
    state: str  # idle, listening, thinking, talking


# --- Track connections ---
active_connections: Set[WebSocket] = set()
status_connections: Set[WebSocket] = set()

# --- Simple status page (optional) ---
html = """
<!DOCTYPE html>
<html>
  <head><title>VRM Trigger Server</title></head>
  <body>
    <h1>VRM Trigger Server</h1>
    <p>WebSocket clients: <span id="count">0</span></p>
    <script>
      const ws = new WebSocket(`ws://${location.host}/ws_status`);
      ws.onmessage = e => {
        const msg = JSON.parse(e.data);
        if (msg.type === 'count_update') {
          document.getElementById('count').textContent = msg.count;
        }
      };
    </script>
  </body>
</html>
"""

@app.get("/")
async def root():
    return HTMLResponse(html)

# --- Models ---
class TalkRequest(BaseModel):
    audio_path: str
    expression: str = "neutral"
    audio_text: str
    audio_duraction: int

# --- Notification logic ---
async def notify_clients(message: dict):
    """Broadcast JSON `message` to every active WS client."""
    if not active_connections:
        logger.info("No clients connected; skipping notify.")
        return
    data = json.dumps(message)
    logger.info(f"Broadcasting to {len(active_connections)} client(s): {data}")
    coros = [ws.send_text(data) for ws in list(active_connections)]
    results = await asyncio.gather(*coros, return_exceptions=True)
    for ws, res in zip(list(active_connections), results):
        if isinstance(res, Exception):
            logger.error(f"Failed to send to {ws.client}: {res}")
            active_connections.discard(ws)

async def broadcast_status(count: int):
    msg = json.dumps({"type": "count_update", "count": count})
    coros = [ws.send_text(msg) for ws in list(status_connections)]
    await asyncio.gather(*coros, return_exceptions=True)

# --- WebSocket endpoints ---
@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    active_connections.add(ws)
    logger.info(f"Client connected: {ws.client} (total {len(active_connections)})")
    await broadcast_status(len(active_connections))
    try:
        while True:
            # Keep-alive or handle incoming if needed
            await ws.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(ws)
        logger.info(f"Client disconnected: {ws.client} (total {len(active_connections)})")
        await broadcast_status(len(active_connections))
    except Exception as e:
        logger.error(f"WS error: {e}")
        active_connections.discard(ws)
        await broadcast_status(len(active_connections))

@app.websocket("/ws_status")
async def ws_status(ws: WebSocket):
    await ws.accept()
    status_connections.add(ws)
    # send initial count
    await ws.send_text(json.dumps({"type": "count_update", "count": len(active_connections)}))
    try:
        while True:
            msg = await ws.receive_text()
            if msg == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        status_connections.discard(ws)
    except Exception:
        status_connections.discard(ws)

# --- HTTP trigger endpoint ---
@app.post("/talk")
async def talk(req: TalkRequest):
    """Receive audio_path & optional expression, broadcast to VRM clients."""
    payload = {
        "type":        "start_animation",
        "audio_path":  req.audio_path,
        "expression":  req.expression,
        "audio_text":  req.audio_text,
        "audio_duraction":  req.audio_duraction
    }
    await notify_clients(payload)
    return {"status": "sent", "payload": payload}


@app.post("/animate")
async def animate(payload: AnimationPayload):
    # Auto-detect animation type from file extension if set to "auto"
    anim_type = payload.animate_type
    if anim_type == "auto":
        url_lower = payload.animation_url.lower()
        if url_lower.endswith(".vrma"):
            anim_type = "start_vrma"
        elif url_lower.endswith(".fbx"):
            anim_type = "start_mixamo"
        else:
            # Default to mixamo for unknown extensions
            anim_type = "start_mixamo"
        logger.info(f"Auto-detected animation type: {anim_type} for {payload.animation_url}")

    # forward these fields to clients
    forwarded = {
        "type": anim_type,
        "animation_url": payload.animation_url,
        "play_once": payload.play_once,
        "crop_start": payload.crop_start,
        "crop_end": payload.crop_end,
        "lock_position": payload.lock_position,
        "track_position": payload.track_position,
    }

    await notify_clients(forwarded)
    return {"status": "sent", "payload": forwarded}

@app.post("/animate_and_talk")
async def animate_and_talk(payload: CombinedPayload):
    payload = {
        "type": "start_vrma_and_talk",
        "animation_url": payload.animation_url,
        "audio_path": payload.audio_path,
        "expression": payload.expression,
        "delay": payload.delay
    }
    for ws in clients:
        await ws.send_json(payload)
    return {"status": "combined sent"}


# ============ STATE CONTROL ============

@app.post("/set_state")
async def set_state(req: SetStateRequest):
    """
    Set the VRM avatar's animation state.
    This controls head microexpressions and animations.

    Valid states:
        - idle: Avatar looks around naturally with eye leading
        - listening: Avatar nods and tilts head while listening
        - thinking: Avatar looks away with pauses while thinking
        - talking: Avatar nods frequently while talking

    Example:
        POST /set_state
        {
            "state": "idle"
        }

        POST /set_state
        {
            "state": "talking"
        }
    """
    valid_states = ["idle", "listening", "thinking", "talking"]
    if req.state not in valid_states:
        return {
            "status": "error",
            "message": f"Invalid state: {req.state}",
            "valid_states": valid_states
        }

    payload = {
        "type": "set_state",
        "state": req.state
    }
    await notify_clients(payload)
    return {
        "status": "state_set",
        "state": req.state
    }





# --- Run with: python server.py ---
if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8001, reload=True)
