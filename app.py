"""Unauthenticated event-registration API backed by Supabase."""

import os
from pathlib import Path
from uuid import UUID

from flask import Flask, jsonify, request, send_from_directory
from supabase import Client, create_client


# Load a project-local .env for `python app.py`; hosted services can inject
# these settings directly into the process environment.
def load_local_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if not name:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '\"'):
            value = value[1:-1]
        os.environ.setdefault(name, value)


load_local_env()


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


@app.after_request
def add_cors_headers(response):
    """Allow the static frontend (or a local frontend dev server) to call the API."""
    response.headers["Access-Control-Allow-Origin"] = os.environ.get("CORS_ORIGIN", "*")
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


@app.get("/")
def index():
    """Serve the dashboard and API from one Flask application."""
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/api")
def api_index():
    return jsonify({"name": "Campus Management Event API", "status": "ok"})


def get_supabase() -> Client:
    """Create the server-side Supabase client only when a request needs it."""
    url = os.environ.get("SUPABASE_URL")
    # Prefer a secret/service-role key for server-side operations. A publishable
    # key can read data only when the project's grants and RLS policies allow it.
    key = (
        os.environ.get("SUPABASE_SECRET_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or os.environ.get("SUPABASE_PUBLISHABLE_KEY")
    )
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and a Supabase key must be configured. "
            "Set SUPABASE_SECRET_KEY or SUPABASE_SERVICE_ROLE_KEY on the server; "
            "SUPABASE_PUBLISHABLE_KEY requires matching database permissions."
        )
    return create_client(url, key)


def error(message: str, status: int):
    return jsonify({"error": message}), status


def require_json_fields(*fields: str):
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error("Request body must be a JSON object.", 400)
    missing = [field for field in fields if not payload.get(field)]
    if missing:
        return None, error(f"Missing required field(s): {', '.join(missing)}.", 400)
    return payload, None


def valid_uuid(value: str) -> bool:
    try:
        UUID(value)
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def database_error(exc: Exception):
    app.logger.exception("Supabase request failed")
    return error("Database request failed.", 502)


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.get("/api/events")
def list_events():
    """Browse events. Optional: ?status=open&limit=20&offset=0."""
    try:
        limit = min(max(int(request.args.get("limit", 50)), 1), 100)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return error("limit and offset must be integers.", 400)

    try:
        query = get_supabase().table("events").select("id,organizer_id,title,capacity,status")
        if status := request.args.get("status"):
            query = query.eq("status", status)
        response = query.order("title").range(offset, offset + limit - 1).execute()
        return jsonify({"data": response.data, "limit": limit, "offset": offset})
    except Exception as exc:
        return database_error(exc)


@app.get("/api/events/<event_id>")
def get_event(event_id: str):
    if not valid_uuid(event_id):
        return error("event_id must be a UUID.", 400)
    try:
        response = (
            get_supabase()
            .table("events")
            .select("id,organizer_id,title,capacity,status")
            .eq("id", event_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return error("Event not found.", 404)
        return jsonify({"data": response.data[0]})
    except Exception as exc:
        return database_error(exc)


@app.post("/api/registrations")
def create_registration():
    """Register a supplied user for an event; returns 409 for duplicates/full events."""
    payload, response = require_json_fields("user_id", "event_id")
    if response:
        return response
    if not valid_uuid(payload["user_id"]) or not valid_uuid(payload["event_id"]):
        return error("user_id and event_id must be UUIDs.", 400)

    try:
        db = get_supabase()
        event_result = (
            db.table("events")
            .select("id,capacity,status")
            .eq("id", payload["event_id"])
            .limit(1)
            .execute()
        )
        if not event_result.data:
            return error("Event not found.", 404)
        event = event_result.data[0]
        if event["status"] not in ("open", "upcoming"):
            return error("Event is not open for registration.", 409)

        existing = (
            db.table("registrations")
            .select("id")
            .eq("user_id", payload["user_id"])
            .eq("event_id", payload["event_id"])
            .limit(1)
            .execute()
        )
        if existing.data:
            return error("User is already registered for this event.", 409)

        registrations = db.table("registrations").select("id").eq("event_id", payload["event_id"]).execute()
        if len(registrations.data) >= event["capacity"]:
            return error("Event is at capacity.", 409)

        created = db.table("registrations").insert(
            {"user_id": payload["user_id"], "event_id": payload["event_id"]}
        ).execute()
        return jsonify({"data": created.data[0]}), 201
    except Exception as exc:
        message = str(exc).lower()
        if "duplicate key" in message or "registrations_user_event_key" in message:
            return error("User is already registered for this event.", 409)
        return database_error(exc)


@app.get("/api/me/registrations")
def my_registrations():
    # With no authentication there is no server-known "me". The caller supplies
    # the user identity; replace this with the authenticated user later.
    user_id = request.args.get("user_id")
    if not valid_uuid(user_id):
        return error("user_id query parameter must be a UUID.", 400)
    try:
        result = (
            get_supabase()
            .table("registrations")
            .select("id,user_id,event_id,created_at,events(id,title,capacity,status,organizer_id)")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return jsonify({"data": result.data})
    except Exception as exc:
        return database_error(exc)


@app.get("/api/events/<event_id>/registrations")
def event_registrations(event_id: str):
    """Lists attendees. Intentionally unrestricted until authentication is added."""
    if not valid_uuid(event_id):
        return error("event_id must be a UUID.", 400)
    try:
        db = get_supabase()
        event = db.table("events").select("id").eq("id", event_id).limit(1).execute()
        if not event.data:
            return error("Event not found.", 404)
        result = (
            db.table("registrations")
            .select("id,user_id,event_id,created_at,users(id,email,role)")
            .eq("event_id", event_id)
            .order("created_at")
            .execute()
        )
        return jsonify({"data": result.data})
    except Exception as exc:
        return database_error(exc)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
