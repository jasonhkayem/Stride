# Stride — AI-Powered Training Platform

A fitness coaching web application built as a final year CS project. Athletes can log workouts, sync activities from Strava, generate personalised training plans, and chat with an AI running coach powered by GPT.

---

## Features

- **Manual activity logging** — log runs, rides, and swims with distance, duration, and date
- **Strava integration** — OAuth connect and bulk-sync activities including route polylines
- **Route maps** — Leaflet.js renders each activity's GPS route on an interactive map
- **AI training plans** — generate week-by-week plans from templates using pace-aware session scheduling
- **Multi-week navigation** — browse every week of a plan with phase labels and prev/next controls
- **AI coach chat** — markdown-formatted coaching advice personalised to your real activity data
- **Plan suggestions** — coach proposes changes (volume, intensity, rest days); athlete approves or declines
- **Weekly distance chart** — Chart.js bar chart of the last 7 days on the dashboard
- **JWT authentication** — HS256 tokens, all mutations require auth
- **Admin dashboard** — basic user and activity overview

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.13, Flask 3.0, SQLAlchemy 2.0 |
| Database | PostgreSQL 18 |
| Auth | Custom HS256 JWT (stdlib only) |
| AI | OpenAI GPT via `LLMService` (stdlib `urllib`) |
| Strava | OAuth 2.0 + Activities API |
| Frontend | Vanilla JS SPA, Bootstrap 5.3, marked.js, Chart.js, Leaflet.js |
| Schema validation | marshmallow + marshmallow-sqlalchemy |
| Tests | pytest 9, Flask test client, `unittest.mock` |

---

## Prerequisites

- Python 3.11+
- PostgreSQL 18 (running locally)
- An OpenAI API key
- A Strava API application (for Strava sync — optional for basic use)

---

## Setup

### 1. Clone and install dependencies

```bash
pip install flask sqlalchemy marshmallow marshmallow-sqlalchemy \
            psycopg2-binary python-dotenv pytest flask-cors
```

### 2. Create the database

```sql
CREATE DATABASE final_year_project;
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
# Database
DATABASE_URL=postgresql+psycopg2://postgres:<password>@127.0.0.1:5432/final_year_project

# LLM (OpenAI or compatible)
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4.1-mini
LLM_TIMEOUT_SEC=30
LLM_AUTH_SCHEME=Bearer

# Strava OAuth (optional)
STRAVA_CLIENT_ID=your_client_id
STRAVA_CLIENT_SECRET=your_client_secret
STRAVA_REDIRECT_URI=http://127.0.0.1:5000/users/strava/oauth/callback
STRAVA_OAUTH_SCOPES=read,activity:read_all
STRAVA_STATE_SECRET=any_random_hex_string

# JWT signing secret
JWT_SECRET=any_random_hex_string
```

### 4. Create database tables

```bash
python -c "from training.db import Base, engine; Base.metadata.create_all(engine)"
```

### 5. Run the database patch for route polylines

```bash
"C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d final_year_project \
  -f scripts/db_patch_activity_reflection.sql
```

### 6. Seed training plan templates

```bash
python scripts/seed_training_plan_templates.py
```


## Running the App

### Start the backend

```bash
python app.py
```

The API runs at `http://127.0.0.1:5000`.

### Open the frontend

Open `frontend/index.html` in a browser, or serve it with any static file server:

```bash
cd frontend
python -m http.server 8080
```

Then navigate to `http://localhost:8080`.

---

## Running the Tests

```bash
python -m pytest tests/ -v
```

- **41 tests** covering auth, activities, training plans, AI coach, and security
- LLM calls are mocked — no API key required to run tests
- Each test creates an isolated user and cleans up after itself

```
tests/test_auth.py          — signup, login, /me, unauthenticated access
tests/test_activities.py    — CRUD, validation, Strava not-connected
tests/test_training_plan.py — generate plan, session volume, approve/reject AI actions
tests/test_coach.py         — chat reply, suggest changes, ownership enforcement
tests/test_security.py      — expired/malformed/tampered JWT, public endpoints
```

---

## Project Structure

```
├── app.py                          # Flask app factory, blueprint auto-discovery
├── frontend/
│   ├── index.html                  # Single-page app shell
│   ├── assets/css/styles.css
│   └── assets/js/app.js            # All frontend logic (routing, API calls, rendering)
├── training/
│   ├── auth/                       # Signup, login, JWT utils, @require_auth decorator
│   ├── activities/                 # Activity CRUD + Strava sync
│   ├── chatbot_sessions/           # Coach chat sessions and AI suggestion flow
│   ├── chatbot_session_messages/   # Per-message storage
│   ├── training_plan_versions/     # Plan generation, AI actions, versioning
│   ├── training_plan_templates/    # Seed templates (5K, 10K, half, marathon)
│   ├── user_training_plans/        # Link between user and their plan
│   ├── users/                      # User model and profile
│   ├── user_integrations/          # Strava OAuth token storage
│   ├── services/
│   │   ├── llm_service.py          # OpenAI-compatible HTTP client
│   │   └── strava_oauth_service.py # Strava OAuth + activities fetch
│   ├── admin/                      # Admin dashboard endpoints
│   ├── common/
│   │   └── crud_service.py         # Generic CRUD base class
│   └── db.py                       # SQLAlchemy engine and SessionLocal
├── scripts/
│   ├── seed_training_plan_templates.py
│   └── db_patch_activity_reflection.sql
└── tests/
    ├── conftest.py                 # Fixtures, cleanup, canned LLM responses
    ├── test_auth.py
    ├── test_activities.py
    ├── test_training_plan.py
    ├── test_coach.py
    └── test_security.py
```

---

## Key API Endpoints

| Method | Route | Description |
|---|---|---|
| POST | `/auth/signup` | Register |
| POST | `/auth/login` | Login, returns JWT |
| GET | `/auth/me/<user_id>` | Get user profile |
| GET/POST | `/activities` | List / create activity |
| PATCH/DELETE | `/activities/<id>` | Update / delete activity |
| POST | `/activities/strava/sync` | Bulk-import from Strava |
| GET | `/training_plan_templates` | List plan templates |
| POST | `/user_training_plans` | Create a user plan |
| POST | `/training_plan_versions/generate_from_template` | AI-generate a plan |
| POST | `/training_plan_versions/apply_ai_actions` | Approve AI suggestions |
| POST | `/chatbot_sessions` | Open a coach session |
| POST | `/chatbot_sessions/<id>/reply` | Send a message, get AI reply |
| GET | `/chatbot_sessions/<id>/messages` | List session messages |
| POST | `/chatbot_sessions/<id>/suggest_training_plan_actions` | Ask coach to suggest plan changes |
| GET | `/health` | Health check |

---

## Notes

- The `route_polyline` column on the `activities` table is added by `scripts/db_patch_activity_reflection.sql`. Run it once after initial table creation.
- Training plan templates must be seeded before generating plans.
- Strava sync requires a connected Strava account via the OAuth flow in the profile page.
- The AI coach formats all responses in Markdown, rendered in the UI via marked.js.
