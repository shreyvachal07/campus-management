"""Unauthenticated event-registration API backed by Supabase."""

import os
from uuid import UUID

from flask import Flask, jsonify, request
from supabase import Client, create_client


app = Flask(__name__)


@app.get("/")
def index():
    """A friendly landing response for the Render service URL."""
    return jsonify(
        {
            "name": "Campus Management Event API",
            "status": "ok",
            "authentication": "disabled",
            "endpoints": {
                "health": "GET /health",
                "events": "GET /api/events",
                "event": "GET /api/events/{id}",
                "create_registration": "POST /api/registrations",
                "my_registrations": "GET /api/me/registrations?user_id={uuid}",
                "event_registrations": "GET /api/events/{id}/registrations",
            },
        }
    )


def get_supabase() -> Client:
    """Create the server-side Supabase client only when a request needs it."""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured. "
            "Keep the service-role key on the server only."
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
