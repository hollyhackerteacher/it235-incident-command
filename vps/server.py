#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(os.environ.get("IT235_STATIC_ROOT", Path(__file__).resolve().parents[1])).resolve()
DATA = Path(os.environ.get("IT235_DATA_DIR", ROOT / "data")).resolve()
DB_PATH = Path(os.environ.get("IT235_DB", DATA / "it235.sqlite3")).resolve()
PORT = int(os.environ.get("IT235_PORT", "8096"))
FACILITATOR_PIN = os.environ.get("IT235_FACILITATOR_PIN", "235control")
DATA.mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS control (
          id INTEGER PRIMARY KEY CHECK (id = 1), current_phase INTEGER NOT NULL,
          updated_at TEXT NOT NULL
        );
        INSERT OR IGNORE INTO control (id, current_phase, updated_at) VALUES (1, 1, CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS teams (
          team_id TEXT PRIMARY KEY, team_name TEXT NOT NULL, members TEXT NOT NULL,
          registered_at TEXT NOT NULL, ready INTEGER NOT NULL DEFAULT 0,
          phase INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS submissions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT NOT NULL,
          team_name TEXT NOT NULL, phase INTEGER NOT NULL, answer TEXT NOT NULL,
          submitted_at TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 0,
          feedback TEXT NOT NULL DEFAULT ''
        );
        """)


def state():
    with db() as conn:
        control = conn.execute("SELECT current_phase FROM control WHERE id=1").fetchone()
        teams = conn.execute("SELECT team_id, team_name, members, registered_at, ready, phase, updated_at FROM teams ORDER BY registered_at").fetchall()
    return {
        "ok": True,
        "currentPhase": int(control["current_phase"]),
        "teams": [
            {"teamId": r["team_id"], "teamName": r["team_name"], "members": r["members"],
             "registeredAt": r["registered_at"], "ready": bool(r["ready"]),
             "phase": int(r["phase"]), "updatedAt": r["updated_at"]}
            for r in teams
        ],
    }


def action(payload):
    kind = payload.get("action")
    stamp = now()
    with db() as conn:
        if kind == "registerTeam":
            conn.execute("""INSERT INTO teams(team_id, team_name, members, registered_at, ready, phase, updated_at)
              VALUES(?,?,?,?,0,1,?) ON CONFLICT(team_id) DO UPDATE SET team_name=excluded.team_name,
              members=excluded.members, updated_at=excluded.updated_at""",
              (str(payload.get("teamId", "")), str(payload.get("teamName", "Unnamed team")), str(payload.get("members", "")), stamp, stamp))
            return {"ok": True, "teamId": payload.get("teamId")}
        if kind == "submit":
            conn.execute("""INSERT INTO submissions(team_id, team_name, phase, answer, submitted_at, points, feedback)
              VALUES(?,?,?,?,?,?,?)""", (str(payload.get("teamId", "")), str(payload.get("teamName", "")),
              int(payload.get("phase", 1)), str(payload.get("answer", "")), stamp, int(payload.get("points", 0)), str(payload.get("feedback", ""))))
            return {"ok": True}
        if kind == "ready":
            conn.execute("UPDATE teams SET ready=1, phase=?, updated_at=? WHERE team_id=?",
                         (int(payload.get("phase", 1)), stamp, str(payload.get("teamId", ""))))
            return {"ok": True}
        if kind == "setPhase":
            if str(payload.get("pin", "")) != FACILITATOR_PIN:
                return {"ok": False, "error": "Invalid facilitator PIN"}
            phase = max(1, min(4, int(payload.get("phase", 1))))
            conn.execute("UPDATE control SET current_phase=?, updated_at=? WHERE id=1", (phase, stamp))
            conn.execute("UPDATE teams SET ready=0, updated_at=? WHERE phase < ?", (stamp, phase))
            return {"ok": True, "currentPhase": phase}
    return {"ok": False, "error": "Unknown action"}


class Handler(BaseHTTPRequestHandler):
    server_version = "IT235Incident/1.0"

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json({"status": "ok", "service": "it235-incident-command"})
        if path == "/api/state":
            return self.send_json(state())
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        target = (ROOT / relative).resolve()
        if ROOT not in target.parents and target != ROOT:
            return self.send_error(HTTPStatus.NOT_FOUND)
        if not target.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = target.read_bytes()
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "text/css; charset=utf-8" if target.suffix == ".css" else "application/javascript; charset=utf-8" if target.suffix == ".js" else "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlparse(self.path).path != "/api/action":
            return self.send_error(HTTPStatus.NOT_FOUND)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            return self.send_json(action(payload))
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"ok": False, "error": "Invalid request"}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    init_db()
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
