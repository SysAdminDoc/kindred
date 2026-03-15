# Kindred v1.3.0

AI-powered compatibility matching + social platform. Open source, privacy-first dating.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, Uvicorn, WebSocket
- **Database**: SQLite with WAL mode, thread-local connection pooling
- **AI/ML**: sentence-transformers (all-MiniLM-L6-v2) for embeddings, Puter.js for AI narratives (client-side, no API key)
- **Frontend**: Single-file SPA (vanilla JS), Catppuccin Mocha dark theme
- **Auth**: JWT (pyjwt + passlib[bcrypt]), 72-hour token expiry, env-configurable secret
- **Security**: CORS middleware, rate limiting (slowapi), file magic byte validation, auth on all mutating endpoints
- **Config**: python-dotenv, `app/config.py` centralizes all settings

## Project Structure
```
kindred/
  start.py              # Turnkey launcher (both servers + auto-venv)
  requirements.txt
  kindred.db            # SQLite (auto-created)
  .env.example          # Configuration template
  Dockerfile            # Container build
  docker-compose.yml    # One-command deployment
  uploads/              # Photos, videos, verification selfies
  app/
    config.py           # Centralized config (env vars / .env file)
    main.py             # FastAPI user server (port 8000, 70+ endpoints)
    admin_app.py        # FastAPI admin server (port 8001)
    questions.py        # Questionnaire: Big Five, scenarios, trade-offs, behavioral, self-disclosure, communication, financial, energy
    engine.py           # Matching: 8-dimension scoring, calibration, coaching, template narratives
    database.py         # SQLite CRUD: 20+ tables, thread-local pooling, schema versioning
  static/
    index.html          # User SPA
    admin.html          # Admin SPA
```

## Run
```
python start.py
```
- **User portal**: http://localhost:8000
- **Admin portal**: http://localhost:8001 (default: admin@kindred.local / admin)
- **Docker**: `docker compose up --build`

## Configuration
Copy `.env.example` to `.env` and customize. Key vars:
- `KINDRED_JWT_SECRET` - JWT signing key (auto-generated if not set)
- `KINDRED_ADMIN_EMAIL` / `KINDRED_ADMIN_PASSWORD` - Default admin creds
- `KINDRED_HOST` / `KINDRED_USER_PORT` / `KINDRED_ADMIN_PORT` - Server binding
- `KINDRED_CORS_ORIGINS` - Comma-separated allowed origins
- `KINDRED_RATE_LIMIT` / `KINDRED_RATE_LIMIT_AUTH` - Rate limiting

## Database Tables
profiles, messages, invites, feedback, date_plans, behavioral_events, safety_reports, profile_blog_posts, profile_comments, profile_friends, notifications, users, likes, status_updates, activity_feed, groups, group_members, group_posts, events, event_rsvps, compat_games, selfie_verifications, video_intros, music_preferences, blocks, password_resets, notification_preferences, schema_versions

## Key Features
- **8-dimension matching**: Personality, values, communication, financial, attachment, tradeoffs, semantic, dealbreaker
- **WebSocket real-time**: Live messaging, typing indicators, online status, read receipts
- **Compatibility games**: "This or That" paired questions with score tracking
- **Selfie verification**: Upload selfie, admin reviews, get verified badge
- **Video intros**: Upload short video clips shown on profiles
- **Music matching**: Add songs/artists, compute music compatibility between pairs
- **Groups & Events**: Create communities, post, RSVP to events, group moderation
- **MySpace-style profiles**: Blog, comments, friends, photo gallery, profile themes
- **Photo gallery**: Multi-photo with primary designation, auto-thumbnails
- **Date plans**: Propose/accept/decline/complete
- **Safety**: Block/report with admin review, profile blocking
- **Profile themes**: Cosmic, Forest, Sunset, Ocean, Aurora gradient themes
- **Activity feed**: Friend activity aggregation
- **Search**: Multi-filter (gender, seeking, age, location)
- **Admin dashboard**: Stats, groups/events/verifications management, profile inspection
- **Settings**: Notification preferences, password change, blocked users, profile deactivation
- **Message pagination**: Load older messages, optimistic send UI

## Key Architecture
- Dual-server: user (8000) + admin (8001) sharing same SQLite DB
- `app/config.py`: Central config from env vars / .env file (JWT secret auto-generated)
- `authFetch` pattern: frontend wrapper auto-includes JWT Authorization header
- `ConnectionManager`: per-profile WebSocket connection lists (multi-tab support)
- Thread-local SQLite connection pooling with WAL mode + busy timeout
- Database migrations via `_migrate()` with try/except ALTER TABLE
- Schema version tracking via `schema_versions` table
- CORS middleware on both servers
- Rate limiting on auth endpoints (slowapi)
- File upload magic byte validation (prevents extension spoofing)
- Auth (`require_user`) on all mutating user endpoints
- Puter.js CDN for AI narratives - zero backend cost, template fallbacks
- Docker + docker-compose for deployment
- Pillow for auto-thumbnail generation

## Version History
- **v1.3.0** - Security hardening (env config, auth on all endpoints, rate limiting, CORS, file magic validation), architecture (connection pooling, config module, schema versioning), features (profile blocking, read receipts, notification prefs, password reset/change, profile deactivation, auto-thumbnails, message pagination, group moderation), UX (toast stacking, loading skeletons, optimistic messaging, empty state CTAs), deployment (Docker, .env config)
- **v1.2.0** - Video intros (upload/view/delete), music preferences (add songs, compute compatibility between pairs), music compatibility on match detail view
- **v1.1.0** - Compatibility games ("This or That" with paired scoring), selfie verification (upload + admin approve/reject), admin verification review tab
- **v1.0.0** - Polish: admin groups/events management tabs, online status indicators (green dot), profile completeness bar, improved mobile responsive, groups/events counts in admin dashboard
- **v0.12.0** - WebSocket real-time messaging, typing indicators, photo messages, photo gallery, search, activity feed, groups, events, profile themes, discover tab
- **v0.11.0** - JWT auth (user + admin), notifications with bell, likes system, status updates, explore/recent profiles
- **v0.6.0** - Admin/User port separation
- **v0.5.0** - MySpace-style profile pages
- **v0.4.0** - 8-dimension matching, one-question-per-screen, coaching tips, date plans
- **v0.3.0** - Puter.js AI narratives (replaced Ollama)
- **v0.2.0** - Major feature expansion
- **v0.1.0** - Initial build
