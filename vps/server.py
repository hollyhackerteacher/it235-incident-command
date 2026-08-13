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
SCENARIO_PATH = Path(os.environ.get("IT235_SCENARIO", ROOT / "vps" / "scenario.json")).resolve()
PORT = int(os.environ.get("IT235_PORT", "8096"))
FACILITATOR_PIN = os.environ.get("IT235_FACILITATOR_PIN", "235control")
DATA.mkdir(parents=True, exist_ok=True)


def now():
    return datetime.now(timezone.utc).isoformat()


def scenario():
    return json.loads(SCENARIO_PATH.read_text())


def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS control (id INTEGER PRIMARY KEY CHECK (id = 1), current_phase INTEGER NOT NULL, updated_at TEXT NOT NULL);
        INSERT OR IGNORE INTO control (id, current_phase, updated_at) VALUES (1, 1, CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS teams (team_id TEXT PRIMARY KEY, team_name TEXT NOT NULL, members TEXT NOT NULL, registered_at TEXT NOT NULL, ready INTEGER NOT NULL DEFAULT 0, phase INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL, known TEXT NOT NULL DEFAULT '', think TEXT NOT NULL DEFAULT '', unknown TEXT NOT NULL DEFAULT '', ruled_out TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS submissions (id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT NOT NULL, team_name TEXT NOT NULL, phase INTEGER NOT NULL, kind TEXT NOT NULL DEFAULT 'decision', answer TEXT NOT NULL, submitted_at TEXT NOT NULL, points INTEGER NOT NULL DEFAULT 0, feedback TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS evidence_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, team_id TEXT NOT NULL, team_name TEXT NOT NULL, evidence_id TEXT NOT NULL, question TEXT NOT NULL, reason TEXT NOT NULL, requested_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'requested');
        CREATE TABLE IF NOT EXISTS scores (team_id TEXT NOT NULL, phase INTEGER NOT NULL, category TEXT NOT NULL, points INTEGER NOT NULL, note TEXT NOT NULL DEFAULT '', updated_at TEXT NOT NULL, PRIMARY KEY(team_id, phase, category));
        """)
        columns = {r[1] for r in conn.execute("PRAGMA table_info(teams)")}
        for name in ("known", "think", "unknown", "ruled_out"):
            if name not in columns:
                conn.execute(f"ALTER TABLE teams ADD COLUMN {name} TEXT NOT NULL DEFAULT ''")
        columns = {r[1] for r in conn.execute("PRAGMA table_info(submissions)")}
        if "kind" not in columns:
            conn.execute("ALTER TABLE submissions ADD COLUMN kind TEXT NOT NULL DEFAULT 'decision'")


def public_state():
    src = scenario()
    with db() as conn:
        control = conn.execute("SELECT current_phase FROM control WHERE id=1").fetchone()
        teams = conn.execute("SELECT * FROM teams ORDER BY registered_at").fetchall()
        released = conn.execute("SELECT evidence_id FROM evidence_requests WHERE status='released' GROUP BY evidence_id").fetchall()
        requests = conn.execute("SELECT * FROM evidence_requests ORDER BY requested_at DESC LIMIT 40").fetchall()
        scores = conn.execute("SELECT team_id, SUM(points) total FROM scores GROUP BY team_id").fetchall()
    released_ids = {r["evidence_id"] for r in released}
    score_map = {r["team_id"]: int(r["total"] or 0) for r in scores}
    evidence = [e for e in src["evidence"] if e["id"] in released_ids]
    phase = int(control["current_phase"])
    return {"ok": True, "currentPhase": phase, "incident": {"name": src["name"], "organization": src["organization"], "severity": src["severity"], "businessImpact": src["businessImpact"], "update": src["phaseUpdates"][str(phase)]}, "releasedEvidence": evidence, "requests": [{"teamName": r["team_name"], "evidenceId": r["evidence_id"], "question": r["question"], "reason": r["reason"], "status": r["status"]} for r in requests], "teams": [{"teamId": r["team_id"], "teamName": r["team_name"], "members": r["members"], "ready": bool(r["ready"]), "phase": int(r["phase"]), "score": score_map.get(r["team_id"], 0), "board": {"known": r["known"], "think": r["think"], "unknown": r["unknown"], "ruledOut": r["ruled_out"]}} for r in teams]}


def action(payload):
    kind = payload.get("action")
    stamp = now()
    with db() as conn:
        if kind == "registerTeam":
            conn.execute("""INSERT INTO teams(team_id,team_name,members,registered_at,ready,phase,updated_at) VALUES(?,?,?,?,0,1,?)
              ON CONFLICT(team_id) DO UPDATE SET team_name=excluded.team_name,members=excluded.members,updated_at=excluded.updated_at""", (str(payload.get("teamId", "")), str(payload.get("teamName", "Unnamed team")), str(payload.get("members", "")), stamp, stamp))
            return {"ok": True, "teamId": payload.get("teamId")}
        if kind == "updateBoard":
            conn.execute("UPDATE teams SET known=?, think=?, unknown=?, ruled_out=?, updated_at=? WHERE team_id=?", (str(payload.get("known", "")), str(payload.get("think", "")), str(payload.get("unknown", "")), str(payload.get("ruledOut", "")), stamp, str(payload.get("teamId", ""))))
            return {"ok": True}
        if kind == "submit":
            conn.execute("INSERT INTO submissions(team_id,team_name,phase,kind,answer,submitted_at,points,feedback) VALUES(?,?,?,?,?,?,?,?)", (str(payload.get("teamId", "")), str(payload.get("teamName", "")), int(payload.get("phase", 1)), str(payload.get("kind", "decision")), str(payload.get("answer", "")), stamp, int(payload.get("points", 0)), str(payload.get("feedback", ""))))
            conn.execute("UPDATE teams SET ready=1, phase=?, updated_at=? WHERE team_id=?", (int(payload.get("phase", 1)), stamp, str(payload.get("teamId", ""))))
            return {"ok": True}
        if kind == "requestEvidence":
            conn.execute("INSERT INTO evidence_requests(team_id,team_name,evidence_id,question,reason,requested_at) VALUES(?,?,?,?,?,?)", (str(payload.get("teamId", "")), str(payload.get("teamName", "")), str(payload.get("evidenceId", "")), str(payload.get("question", "")), str(payload.get("reason", "")), stamp))
            return {"ok": True}
        if kind == "setPhase":
            if str(payload.get("pin", "")) != FACILITATOR_PIN:
                return {"ok": False, "error": "Invalid facilitator PIN"}
            phase = max(1, min(7, int(payload.get("phase", 1))))
            conn.execute("UPDATE control SET current_phase=?, updated_at=? WHERE id=1", (phase, stamp))
            conn.execute("UPDATE teams SET ready=0, updated_at=? WHERE phase < ?", (stamp, phase))
            return {"ok": True, "currentPhase": phase}
        if kind == "releaseEvidence":
            if str(payload.get("pin", "")) != FACILITATOR_PIN:
                return {"ok": False, "error": "Invalid facilitator PIN"}
            conn.execute("UPDATE evidence_requests SET status='released' WHERE evidence_id=?", (str(payload.get("evidenceId", "")),))
            return {"ok": True}
        if kind == "score":
            if str(payload.get("pin", "")) != FACILITATOR_PIN:
                return {"ok": False, "error": "Invalid facilitator PIN"}
            conn.execute("INSERT INTO scores(team_id,phase,category,points,note,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(team_id,phase,category) DO UPDATE SET points=excluded.points,note=excluded.note,updated_at=excluded.updated_at", (str(payload.get("teamId", "")), int(payload.get("phase", 1)), str(payload.get("category", "process")), int(payload.get("points", 0)), str(payload.get("note", "")), stamp))
            return {"ok": True}
        if kind == "instructor":
            if str(payload.get("pin", "")) != FACILITATOR_PIN:
                return {"ok": False, "error": "Invalid facilitator PIN"}
            src = scenario()
            return {"ok": True, "sourceOfTruth": {"timeline": src["timeline"], "rootCause": src["rootCause"], "verification": src["verification"], "learningObjectives": src["learningObjectives"]}, "allEvidence": src["evidence"]}
    return {"ok": False, "error": "Unknown action"}


class Handler(BaseHTTPRequestHandler):
    server_version = "IT235Incident/2.0"

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
            return self.send_json(public_state())
        relative = "index.html" if path in ("", "/") else path.lstrip("/")
        if relative == "vps" or relative.startswith("vps/") or relative == "data" or relative.startswith("data/"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        target = (ROOT / relative).resolve()
        if ROOT not in target.parents and target != ROOT or not target.is_file():
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = target.read_bytes()
        content_type = "text/html; charset=utf-8" if target.suffix == ".html" else "text/css; charset=utf-8" if target.suffix == ".css" else "application/javascript; charset=utf-8" if target.suffix == ".js" else "application/json; charset=utf-8" if target.suffix == ".json" else "application/octet-stream"
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
            return self.send_json(action(json.loads(self.rfile.read(length) or b"{}")))
        except (ValueError, json.JSONDecodeError):
            return self.send_json({"ok": False, "error": "Invalid request"}, HTTPStatus.BAD_REQUEST)

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}", flush=True)


if __name__ == "__main__":
    init_db()
    ThreadingHTTPServer.allow_reuse_address = True
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
