# Stride — AI-Powered Training Platform

Final year project. A fitness training SPA with clubs, activities, training plans, an AI coach chatbot, and Strava OAuth integration.

---

## Stack

| Layer | Tech |
|---|---|
| Backend | Python 3.13, Flask, SQLAlchemy 2 (ORM), Marshmallow 3 (serialisation), psycopg2 |
| Database | PostgreSQL (default); SQLite fallback via `DATABASE_URL` env var |
| Frontend | Vanilla JS SPA (hash-routing), Bootstrap-like custom CSS, Chart.js, Leaflet |
| AI | OpenAI API via `training/services/llm_service.py` (urllib, no SDK) |
| Auth | Custom HS256 JWT — `training/auth/jwt_utils.py` + `@require_auth` decorator |
| Strava | OAuth2 PKCE-style flow in `training/services/strava_oauth_service.py` |

---

## How to run

```bash
# Install deps
pip install -r requirements.txt

# Copy and fill in secrets
cp .env.example .env   # set DATABASE_URL, JWT_SECRET, OPENAI_API_KEY, STRAVA_*

# Start Flask dev server
python app.py           # listens on 127.0.0.1:5000

# Run tests
python -m pytest tests/ -v   # 41 tests, all should pass
```

Open `frontend/index.html` directly in a browser (no build step required).

---

## Project layout

```
app.py                          # Flask app factory — auto-discovers all blueprint modules
training/
  db.py                         # SQLAlchemy engine + SessionLocal (scoped_session)
  common/crud_service.py        # CRUDService base class (create/get/list/update/delete)
  auth/
    decorators.py               # @require_auth — sets g.current_user_id, g.current_role
    jwt_utils.py                # encode_token / decode_token (HS256)
    service.py                  # login, register, forgot-password
  services/
    llm_service.py              # LLMService — wraps OpenAI chat completions
    strava_oauth_service.py     # StravaOAuthService — OAuth flow + activity/lap fetching
    plan_versioning_service.py  # Generates training plan versions from templates via LLM
  users/                        # User CRUD, avatar upload
  activities/                   # Activity CRUD + Strava sync
  clubs/                        # Club CRUD
  club_memberships/             # Join/leave/approve/reject/kick membership; ClubKickLog audit model
  events/                       # Club events
  event_registrations/          # Event RSVP
  messages/                     # Direct messages between users
  user_follows/                 # Follow/unfollow users
  chatbot_sessions/             # AI coach chat sessions (LLM-backed)
  chatbot_session_messages/     # Individual messages in a coach session
  user_training_plans/          # One plan per user (wrapper)
  training_plan_versions/       # Versioned AI-generated plans
  training_plan_actions/        # Individual weekly workout actions inside a plan version
  training_plan_adjustments/    # AI-suggested adjustments to a plan
  training_plan_templates/      # Seed templates used to bootstrap plan generation
  completed_actions/            # User marks a plan action as done
  completed_action_laps/        # Per-lap detail for a completed action
  user_integrations/            # Strava token storage (UserIntegration model)
  admin/                        # Super-admin overview endpoints + GET /admin/kick_logs
frontend/
  index.html                    # Single HTML file (mounts <div id="app">)
  assets/js/
    new_app.js                  # Route handlers: renderDashboard, renderAdmin, route map, hashchange/load listeners
    router.js                   # renderLayout, renderEmptyState, renderStatusPill, initLayoutActions, handleRoute
    clubs.js                    # All club UI: renderClubs, openClubDetailModal, modals (leave/cancel/kick/event)
    profile.js                  # renderProfile, renderPublicProfile, Strava sync button
    (other js files per feature)
  assets/css/styles.css         # All styles
scripts/
  seed_training_plan_templates.py
tests/                          # pytest suite (41 tests)
```

---

## Blueprint pattern

Every module follows the same 5-file pattern:

```
models.py      SQLAlchemy ORM model
schemas.py     Marshmallow schema (validates + serialises)
service.py     Business logic, extends CRUDService
controller.py  Thin layer: calls service, returns jsonify(schema.dump(...))
routes.py      Flask Blueprint with URL prefix
```

`app.py` auto-discovers all `training/*/routes.py` files and registers their blueprints.

---

## Key models

| Model | PK | Notes |
|---|---|---|
| `User` | `user_id` (UUID) | `platform_role`: `"user"` or `"super_admin"` |
| `Activity` | `activity_id` (UUID) | `activity_type` enum; `laps` JSONB; `average_heart_rate` Float |
| `Club` | `club_id` (UUID) | `created_by` → User |
| `ClubMembership` | `membership_id` (UUID) | `status`: `pending/approved/rejected`; `role`: `member/club_admin` |
| `ClubKickLog` | `log_id` (UUID) | Audit log for member removals: `club_id`, `kicked_user_id`, `kicked_by`, `reason`, `created_at` |
| `UserTrainingPlan` | `user_plan_id` (UUID) | One per user |
| `TrainingPlanVersion` | `version_id` (UUID) | Many per plan; LLM-generated |
| `TrainingPlanAction` | `action_id` (UUID) | Weekly workouts inside a version |
| `ChatbotSession` | `chatbot_id` (UUID) | One active session per user |
| `UserIntegration` | `integration_id` (UUID) | Stores Strava OAuth tokens |

---

## Auth

- `POST /auth/login` → returns `{ token, user_id, role }`
- Token stored in `localStorage` on the frontend (`stride.token`, `stride.userId`, `stride.platformRole`)
- `@require_auth` decorator validates Bearer token and sets `g.current_user_id`
- Only activity mutations and chatbot endpoints currently have `@require_auth` — most other routes are unprotected (known gap, documented as future work)

---

## Strava integration

Flow: `GET /strava/authorize` → redirect → `GET /strava/callback` → tokens stored in `user_integrations`.

Sync: `POST /activities/strava/sync` calls `ActivityService.sync_from_strava()`:
- Fetches activity list from Strava (paginated)
- For each new activity, fetches detail endpoint for lap data (best-effort, won't fail sync)
- Normalises `average_heartrate` → `average_heart_rate` (Float)
- Normalises lap data → `laps` JSONB: `[{lap_index, distance_km, duration_sec, avg_hr}]`
- Skips activities already in DB (by `strava_id`)

---

## Frontend architecture

Single file `app.js`. Key globals:
- `state` — all loaded data (activities, clubs, users, etc.)
- `apiFetch(path, options)` — authenticated fetch wrapper
- `ensureXxxLoaded(force?)` — lazy-load + cache in `state`
- Hash routing: `routes` object maps `#/path` → render function

Key render functions:
- `renderDashboard()`, `renderActivities()`, `renderClubs()`, `renderProfile()`, `renderCoach()`, `renderTrainingPlan()`, `renderAdmin()`
- `renderApiActivityCard(activity)` — renders a single activity card
- `renderActivityModal()` — HTML for the activity detail modal
- `renderModalPaceChart(activityId, type)` — recent sessions bar chart (Chart.js)
- `renderModalHrChart(activityId, type)` — heart rate trend bar chart (Chart.js)
- `renderModalLapChart(laps)` — dual-axis lap breakdown: pace bars + HR line (Chart.js)
- `attachActivityCardHandlers()` — wires all activity card interactions
- `attachClubActions()` — wires all club interactions including leave/cancel-request/kick modals
- `openLeaveClubModal(clubId, membershipId, clubName)` — shows leave confirmation modal
- `openCancelRequestModal(clubId, membershipId, clubName)` — styled cancel-pending-request modal (no `window.confirm`)
- `openKickMemberModal(membershipId, userName)` — styled kick modal with reason textarea
- `openClubDetailModal(club)` — shows club detail with members + leaderboard tabs; admin sees Remove buttons

Club admin role detection: `isClubAdmin(clubId)` checks `status === "approved" && role === "club_admin"`.
Club admins see an "Admin" badge instead of join/leave/pending button everywhere (card + detail modal footer).

Activity modal sections (in order): stats → map (Leaflet) → lap breakdown → recent sessions pace → heart rate trend → comments.

---

## Activity types

Strava types are normalised to: `run`, `bike`, `swim`, `walk`, `weights`, `mobility`.
Distance-capable types (show distance/pace): `run`, `bike`, `swim`, `walk`, `hike`.

---

## Environment variables

| Var | Purpose |
|---|---|
| `DATABASE_URL` | SQLAlchemy connection string (default: SQLite) |
| `JWT_SECRET` | HS256 signing key |
| `OPENAI_API_KEY` | LLM service |
| `STRAVA_CLIENT_ID` | Strava OAuth |
| `STRAVA_CLIENT_SECRET` | Strava OAuth |
| `STRAVA_REDIRECT_URI` | Strava OAuth callback URL |
| `STRAVA_STATE_SECRET` | HMAC key for signed OAuth state param |
| `STRAVA_OAUTH_SCOPES` | Default: `read,activity:read_all` |

---

## Testing

```bash
python -m pytest tests/ -v    # 41 tests, all passing
```

Tests live in `tests/`. Run after any backend change to confirm nothing is broken.

---

## DB table creation note

`app.py` explicitly creates the `ClubKickLog` table on startup using:
```python
ClubKickLog.__table__.create(engine, checkfirst=True)
```
This is done INSIDE `create_app()` after `_load_env_file()` so `DATABASE_URL` is resolved before the engine is imported. Do NOT move these imports to module top-level — it breaks the test suite (SQLite vs PostgreSQL divergence).

---

## Known limitations / future work

- Most routes lack `@require_auth` (activity + chatbot routes are protected; clubs, users, messages, events are not)
- No rate limiting
- JWT stored in `localStorage` (XSS risk; production would use HttpOnly cookies)
- CORS wildcard (`Access-Control-Allow-Origin: *`)
- Strava sync does not update existing activities (only imports new ones); re-syncing from Strava will not add `laps`/`average_heart_rate` to already-imported activities
- No soft delete or audit trail
- N+1 query pattern in `UserTrainingPlanService.list_all_with_related()`
