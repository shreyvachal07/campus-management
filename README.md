# Campus Management

CampusCue is a responsive campus-events dashboard served by a Flask/Supabase API.

## Run locally

1. In the repository root, create `.env` with `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`).
2. Install dependencies: `pip install -r requirements.txt`.
3. Run: `python app.py`.
4. Open `http://localhost:5000`.

The frontend loads real events from `GET /api/events`. Its RSVP controls post to `POST /api/registrations` once the signed-in user's UUID is assigned to `window.CAMPUS_USER_ID`; this prevents putting a Supabase secret in the browser.

Use `schema.sql` to create the required tables before starting the API.

## Deploy to Vercel

1. Import this GitHub repository in Vercel; it detects the Flask application in `app.py`.
2. Add `SUPABASE_URL` and `SUPABASE_SECRET_KEY` (or `SUPABASE_SERVICE_ROLE_KEY`) under **Project Settings → Environment Variables**.
3. Deploy. Vercel serves the dashboard from `public/` through its CDN and runs the Flask API as a Python function.

Never add the Supabase secret to the frontend or commit the `.env` file.
