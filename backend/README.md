# Event API backend

Flask/Supabase backend implementing every endpoint in `api.png` against the three tables in `database.png`. Authentication and authorization are intentionally absent for now.

## Setup

1. Create the database tables by running [`schema.sql`](schema.sql) in the Supabase SQL editor, if they do not already exist.
2. Fill in the backend `.env` file. `app.py` loads it automatically when run locally. Use `SUPABASE_SECRET_KEY` or `SUPABASE_SERVICE_ROLE_KEY` for full server-side database access. A `SUPABASE_PUBLISHABLE_KEY` can be used only when the Supabase table grants and row-level security policies permit the requested operations. Never put a secret/service-role key in frontend code.
3. Activate the existing virtual environment and run:

   ```powershell
   .\venv\Scripts\Activate.ps1
   python app.py
   ```

The server listens on `http://localhost:5000`.

## API

| Method | Endpoint | Notes |
| --- | --- | --- |
| GET | `/api/events` | Optional `status`, `limit`, and `offset` query parameters. |
| GET | `/api/events/{id}` | Event details. |
| POST | `/api/registrations` | Body: `{ "user_id": "uuid", "event_id": "uuid" }`; returns 201 or 409. |
| GET | `/api/me/registrations?user_id={uuid}` | `user_id` replaces the unavailable current user until auth exists. |
| GET | `/api/events/{id}/registrations` | Attendee list, public for now. |

`POST /api/registrations` checks event availability (`upcoming` or `open`), duplicate registrations, and capacity. The database unique constraint additionally prevents duplicate registrations during concurrent requests.

## Important temporary limitation

Without authentication, anyone who knows a user UUID can read that user's registrations and everyone can read attendee lists. Before deploying, replace `user_id` in `/api/me/registrations` with the authenticated user and restrict the attendee-list endpoint to the event organizer.

