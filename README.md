# Campus Management

CampusCue is a responsive campus-events dashboard connected to a Flask and Supabase API.

## Project structure

```text
frontend/   Dashboard HTML, CSS, and JavaScript
backend/    Flask API, Supabase schema, and Python dependencies
```

## Run locally

1. Create `backend/.env` using `backend/.env.example` and enter your Supabase values.
2. Install dependencies: `pip install -r backend/requirements.txt`.
3. Run: `python backend/app.py`.
4. Visit `http://localhost:5000`.

The backend serves the frontend and exposes the API at `/api/events` and `/api/registrations`. Do not put Supabase service keys in the frontend.
