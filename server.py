"""Baby Names — FastAPI backend for Glicko-2 state persistence."""

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
DB_PATH = DATA_DIR / "babynames.db"

app = FastAPI(title="Baby Names")


# ---------------------------------------------------------------
# Database
# ---------------------------------------------------------------


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db_session():
    conn = get_db()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with db_session() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_state (
                user TEXT NOT NULL,
                gender TEXT NOT NULL,
                state TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user, gender)
            )
        """)


# ---------------------------------------------------------------
# Models
# ---------------------------------------------------------------


class SaveStateRequest(BaseModel):
    user: str
    gender: str
    ratings: dict
    vetoes: dict
    history: list
    totalComparisons: int
    scopeLimit: int = 250
    activeOrigins: list = []


# ---------------------------------------------------------------
# API Routes
# ---------------------------------------------------------------


@app.post("/api/state")
def save_state(req: SaveStateRequest):
    if not req.user or not req.user.strip():
        raise HTTPException(400, "User name required")

    state = req.model_dump(exclude={"user", "gender"})

    with db_session() as conn:
        conn.execute(
            """INSERT INTO user_state (user, gender, state, updated_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(user, gender) DO UPDATE SET
               state = excluded.state, updated_at = CURRENT_TIMESTAMP""",
            (req.user.lower(), req.gender, json.dumps(state)),
        )
    return {"ok": True}


@app.get("/api/state")
def load_state(user: str = Query(...), gender: str = Query("M")):
    with db_session() as conn:
        row = conn.execute(
            "SELECT state FROM user_state WHERE user = ? AND gender = ?",
            (user.lower(), gender),
        ).fetchone()

    if not row:
        raise HTTPException(404, "No saved state")

    return JSONResponse(json.loads(row["state"]))


@app.get("/api/compare")
def compare(a: str = Query(...), b: str = Query(...), gender: str = Query("M")):
    with db_session() as conn:
        row_a = conn.execute(
            "SELECT state FROM user_state WHERE user = ? AND gender = ?",
            (a.lower(), gender),
        ).fetchone()
        row_b = conn.execute(
            "SELECT state FROM user_state WHERE user = ? AND gender = ?",
            (b.lower(), gender),
        ).fetchone()

    if not row_a:
        raise HTTPException(404, f"No saved state for {a}")
    if not row_b:
        raise HTTPException(404, f"No saved state for {b}")

    state_a = json.loads(row_a["state"])
    state_b = json.loads(row_b["state"])

    def top_n(ratings_dict, n=30):
        entries = [
            {"rank": int(k), **v}
            for k, v in ratings_dict.get("ratings", {}).items()
            if v.get("comparisons", 0) > 0
        ]
        entries.sort(key=lambda e: e.get("mu", 0), reverse=True)
        return entries[:n]

    top_a = top_n(state_a)
    top_b = top_n(state_b)

    return {"a": top_a, "b": top_b}


# ---------------------------------------------------------------
# Static files — serve the frontend
# ---------------------------------------------------------------


@app.get("/")
def index():
    return FileResponse("index.html")


# Mount static files last so API routes take priority
app.mount("/", StaticFiles(directory="."), name="static")


# ---------------------------------------------------------------
# Startup
# ---------------------------------------------------------------


@app.on_event("startup")
def on_startup():
    init_db()
