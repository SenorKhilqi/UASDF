"""
Real-time Web Server Log Monitoring Dashboard
FastAPI Backend with WebSocket Broadcasting & ML-based Payload Classification
"""

import asyncio
import json
import os
import pickle
import re
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("log_monitor")

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
LOG_FILE = Path("access.log")
MODEL_PATH = Path("rf_model.pkl")
VECTORIZER_PATH = Path("tfidf.pkl")
POLL_INTERVAL = 0.3  # seconds between file stat checks

# Common Apache/Nginx combined log format pattern
# Example: 192.168.1.1 - - [21/Apr/2026:10:00:00 +0700] "GET /index.php?id=1 HTTP/1.1" 200 512
LOG_PATTERN = re.compile(
    r'(?P<ip>\S+)\s+'          # Source IP
    r'\S+\s+\S+\s+'            # ident, authuser
    r'\[(?P<time>[^\]]+)\]\s+' # Timestamp
    r'"(?P<request>[^"]+)"'    # HTTP Request
)

# ─────────────────────────────────────────────
# ML Model & Vectorizer (module-level singletons)
# ─────────────────────────────────────────────
rf_model = None
tfidf_vectorizer = None


def load_ml_artifacts() -> bool:
    """Load the pre-trained Random Forest model and TF-IDF vectorizer from disk."""
    global rf_model, tfidf_vectorizer

    if not MODEL_PATH.exists():
        logger.warning(
            f"Model file '{MODEL_PATH}' not found. "
            "Running in DEMO mode — predictions will be simulated."
        )
        return False

    if not VECTORIZER_PATH.exists():
        logger.warning(
            f"Vectorizer file '{VECTORIZER_PATH}' not found. "
            "Running in DEMO mode — predictions will be simulated."
        )
        return False

    try:
        with open(MODEL_PATH, "rb") as f:
            rf_model = pickle.load(f)
        with open(VECTORIZER_PATH, "rb") as f:
            tfidf_vectorizer = pickle.load(f)
        logger.info("✅ ML artifacts loaded successfully.")
        return True
    except Exception as exc:
        logger.error(f"Failed to load ML artifacts: {exc}")
        return False


def predict_payload(payload: str) -> str:
    """
    Classify a URL payload as 'Normal' or 'Attack'.

    Falls back to a heuristic-based demo predictor when the model is not loaded.
    """
    global rf_model, tfidf_vectorizer

    if rf_model is None or tfidf_vectorizer is None:
        return _demo_predict(payload)

    try:
        features = tfidf_vectorizer.transform([payload])
        prediction = rf_model.predict(features)[0]
        return "Attack" if int(prediction) == 1 else "Normal"
    except Exception as exc:
        logger.error(f"Prediction error: {exc}")
        return _demo_predict(payload)


# Heuristic keywords used only in demo / fallback mode
_ATTACK_KEYWORDS = re.compile(
    r"(select|union|insert|drop|delete|update|exec|script|alert|"
    r"onerror|onload|<|>|'|\"|\.\./|%2e%2e|%00|cmd=|passwd|etc/|"
    r"eval\(|base64|fromcharcode|javascript:|vbscript:)",
    re.IGNORECASE,
)


def _demo_predict(payload: str) -> str:
    """
    Heuristic predictor used when no trained model is present.
    Checks for common SQLi / XSS / path-traversal indicators.
    """
    return "Attack" if _ATTACK_KEYWORDS.search(payload) else "Normal"


# ─────────────────────────────────────────────
# WebSocket Connection Manager
# ─────────────────────────────────────────────
class ConnectionManager:
    """Manages all active WebSocket connections and broadcasts messages."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info(
            f"Client connected: {websocket.client}. "
            f"Total: {len(self.active_connections)}"
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info(
            f"Client disconnected: {websocket.client}. "
            f"Remaining: {len(self.active_connections)}"
        )

    async def broadcast(self, message: dict) -> None:
        """Broadcast a JSON-serialisable dict to every connected client."""
        payload = json.dumps(message, ensure_ascii=False)
        dead: list[WebSocket] = []

        async with self._lock:
            targets = list(self.active_connections)

        for ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        for ws in dead:
            await self.disconnect(ws)


manager = ConnectionManager()


# ─────────────────────────────────────────────
# Log Parsing Helpers
# ─────────────────────────────────────────────
def parse_log_line(line: str) -> Optional[dict]:
    """
    Parse a single Apache/Nginx Combined Log Format line.

    Returns a dict with keys: timestamp, ip, payload, status
    or None if the line cannot be parsed.
    """
    line = line.strip()
    if not line:
        return None

    match = LOG_PATTERN.match(line)
    if not match:
        logger.debug(f"Unmatched log line: {line!r}")
        return None

    ip = match.group("ip")
    raw_time = match.group("time")
    request = match.group("request")

    # Normalise timestamp
    try:
        dt = datetime.strptime(raw_time, "%d/%b/%Y:%H:%M:%S %z")
        timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        timestamp = raw_time

    # Extract URI (second token of the request line, e.g. GET /path HTTP/1.1)
    parts = request.split(" ")
    uri = parts[1] if len(parts) >= 2 else request

    status = predict_payload(uri)

    return {
        "timestamp": timestamp,
        "ip": ip,
        "payload": uri,
        "status": status,
        "raw": line,  # kept for debugging; stripped in broadcast
    }


# ─────────────────────────────────────────────
# Async Log Tailer (tail -f equivalent)
# ─────────────────────────────────────────────
async def tail_log_file() -> None:
    """
    Continuously monitor access.log for new lines and broadcast
    parsed + classified entries to all connected WebSocket clients.

    Behaviour mirrors `tail -f`: tracks the file position across
    polls and handles log rotation (file shrinkage / recreation).
    """
    logger.info(f"Starting log tailer on '{LOG_FILE}' …")

    # Ensure the log file exists
    LOG_FILE.touch(exist_ok=True)

    file_pos: int = LOG_FILE.stat().st_size  # start at the end (live tail)
    file_inode: int = LOG_FILE.stat().st_ino

    while True:
        await asyncio.sleep(POLL_INTERVAL)

        try:
            stat = LOG_FILE.stat()
        except FileNotFoundError:
            # File was deleted; wait for recreation
            logger.warning(f"'{LOG_FILE}' disappeared, waiting for recreation …")
            await asyncio.sleep(1)
            continue

        # Detect log rotation (inode change or file shrunk)
        if stat.st_ino != file_inode or stat.st_size < file_pos:
            logger.info("Log rotation detected, resetting file position.")
            file_pos = 0
            file_inode = stat.st_ino

        if stat.st_size == file_pos:
            # No new data
            continue

        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
                f.seek(file_pos)
                new_lines = f.readlines()
                file_pos = f.tell()
        except OSError as exc:
            logger.error(f"Error reading log file: {exc}")
            continue

        for line in new_lines:
            entry = parse_log_line(line)
            if entry is None:
                continue

            broadcast_payload = {
                "timestamp": entry["timestamp"],
                "ip": entry["ip"],
                "payload": entry["payload"],
                "status": entry["status"],
            }

            logger.info(
                f"[{entry['status'].upper():6s}] {entry['ip']} → {entry['payload']}"
            )
            await manager.broadcast(broadcast_payload)


# ─────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load ML artifacts and start the log tailer."""
    load_ml_artifacts()
    task = asyncio.create_task(tail_log_file())
    logger.info("🚀 Dashboard backend is live.")
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("👋 Shutdown complete.")


# ─────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────
app = FastAPI(
    title="Log Monitor Dashboard",
    description="Real-time web server log analysis with ML-based attack detection.",
    version="1.0.0",
    lifespan=lifespan,
)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    """Serve the frontend dashboard HTML."""
    html_path = Path("index.html")
    if not html_path.exists():
        return HTMLResponse(
            content="<h1>index.html not found</h1>"
            "<p>Place index.html in the same directory as main.py.</p>",
            status_code=404,
        )
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time log event streaming."""
    await manager.connect(websocket)
    try:
        # Send a handshake / connection confirmation
        await websocket.send_text(
            json.dumps({"type": "connected", "message": "Stream connected."})
        )
        # Keep connection alive — actual data is pushed by the tailer task
        while True:
            # Await a ping from the client or detect a close frame
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health-check endpoint."""
    return {
        "status": "ok",
        "model_loaded": rf_model is not None,
        "clients_connected": len(manager.active_connections),
        "log_file": str(LOG_FILE),
        "log_exists": LOG_FILE.exists(),
    }
