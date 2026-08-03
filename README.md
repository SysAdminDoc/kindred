<p align="center">
  <img src="static/logo.svg" alt="Kindred" width="160">
</p>

<h1 align="center">Kindred</h1>

<p align="center">
  <strong>Compatibility-first dating + social platform</strong><br>
  Open source. Privacy-first. No funny business.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-in%20development-f9e2af?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/version-2.5.1-cba6f7?style=flat-square" alt="Version">
  <img src="https://img.shields.io/badge/python-3.12+-89b4fa?style=flat-square" alt="Python">
  <img src="https://img.shields.io/badge/license-BSL%201.1-a6e3a1?style=flat-square" alt="License">
</p>

---

> **This project is in active development.** Kindred is being built to launch as a live website. This repository exists as a transparency measure -- the full source code is public so users can see exactly what runs behind the site. No hidden data collection, no dark patterns, no funny business. This is the code.

---

## What is Kindred?

Kindred is a dating and social platform built around genuine compatibility instead of swiping on photos. Users answer a detailed questionnaire covering personality, values, communication style, finances, and more. An 8-dimension matching engine scores compatibility and generates narratives explaining *why* two people might click.

## Features

**Matching Engine**
- 8-dimension compatibility scoring (personality, values, communication, financial, attachment, tradeoffs, semantic, dealbreaker)
- Adaptive IRT questionnaire with a 1000+ item bank and high-information sequencing
- Active-learning `/api/questionnaire/next` endpoint balances information gain across compatibility dimensions
- Optional country-code calibration uses private local cohorts and preserves raw scores for auditability
- Compatibility radar chart (canvas spider chart for 8 dimensions)
- sentence-transformers embeddings for semantic similarity (MPNet by default, MiniLM fallback)
- Match narratives, icebreakers, and coaching tips
- Customizable dimension weights per user
- Private post-date outcome learning adapts match weights while preserving manual priorities
- Photo reveal at compatibility threshold
- Daily curated Top Picks suggestions
- Super Like with instant notification
- Match expiry (7-day countdown without messaging)
- Location-based matching with distance filtering
- Mutual friends indicator
- Smart conversation starters (personalized from shared interests)
- Compatibility recalculation (re-score after questionnaire updates)
- AI conversation suggestions (template + Puter.js powered)
- Date feedback and rating system

**Social Platform**
- Video calling via Jitsi Meet (in-app call initiation with WebSocket signaling)
- Real-time WebSocket messaging with typing indicators and read receipts
- Voice messages (MediaRecorder API recording + playback)
- Message reactions (emoji) and GIF search (Tenor API)
- Message editing (5-minute grace period) and soft-delete
- Message status indicators (sent/delivered/read)
- Clipboard image paste in chat
- Message search across conversations
- Group chat with real-time WebSocket messaging
- Polls in groups (create, vote, results)
- Stories/Moments (24-hour ephemeral posts with gradient backgrounds)
- MySpace-style profile pages with blog, comments, friends, photo gallery
- Profile prompts (Hinge-style "Two truths and a lie", "My ideal Sunday", etc.)
- Profile themes (Cosmic, Forest, Sunset, Ocean, Aurora)
- Status updates and activity feed
- Groups and events with RSVP + calendar view + Leaflet map view
- Profile boost (premium visibility boost with countdown timer)
- Video intros and music preferences with cross-user compatibility scoring
- "This or That" compatibility games between matched pairs
- Who Viewed Me and Who Liked You feeds
- Guided onboarding tour for new users
- Notification sounds (AudioContext two-tone beep)
- Image cropping before upload (Canvas API)
- Icebreaker games (Word Association, Would You Rather, 20 Questions)
- Date scheduling with ICS calendar export
- Blind date mode (48h no-photo/name, then reveal)
- Second look (review passed profiles)
- Threaded replies (quote-reply in conversations)
- Shared playlists between matched pairs
- Event photo albums (shared galleries)
- Profile badges (achievement system)
- Story reactions (quick emoji reactions)
- Pinned messages in conversations
- Dark/Light theme toggle (Catppuccin Mocha/Latte)
- Keyboard shortcuts with help overlay
- Profile completeness coaching
- Animated page transitions
- Typing previews (opt-in)
- WebSocket auto-reconnection with exponential backoff
- Unread badge counts (tab badges, page title, per-conversation)
- Emoji picker (40-emoji floating grid)
- Availability status (active/away/busy/offline with profile badges)
- Announcement banners (platform-wide dismissible notices)
- Link preview scanning (suspicious URL warnings)
- Swipe gestures on discover cards (touch left/right for pass/like)
- Infinite scroll with lazy loading for activity feed
- Image lightbox (full-screen photo viewer with pinch-zoom)
- Pull-to-refresh on mobile
- Onboarding progress bar during questionnaire
- Skeleton shimmer loading placeholders
- Dealbreaker quiz comparison between matches
- Compatibility over time tracking with line chart
- Profile endorsements (trait badges from friends/matches)
- Shared interests visual tag comparison
- Group post emoji reactions
- Event chat (real-time messaging within events)
- Read receipts toggle (privacy setting)
- Smart notification digest (aggregated summary)
- Slow reveal profiles (progressive info unlock stages)

**Trust & Safety**
- Two-factor authentication (TOTP) with recovery codes
- Incognito mode (browse without appearing in Who Viewed Me)
- Session management (view/revoke active sessions)
- Account deletion (GDPR-compliant full data removal)
- Data export (GDPR-compliant download your data)
- Selfie verification with admin review
- Automated content filtering (profanity censoring, spam blocking)
- Photo moderation queue with admin review
- Profile blocking with undo grace period
- Safety check-in timer with emergency contact alerts
- Dealbreaker warnings on profile views
- Message cooldown (rate limit for new matches)
- Link preview scanning (suspicious URL warnings)
- Rate-limited auth endpoints
- Shared Redis rate limits and refresh-token sessions when `KINDRED_REDIS_URL` is configured
- File upload magic byte validation on all upload endpoints
- JWT authentication on all user and admin endpoints
- WebSocket JWT authentication (prevents impersonation)
- XSS prevention (HTML escaping on all user-rendered content)
- Persistent JWT secret (file-backed, survives restarts)
- CORS locked to localhost by default
- UPSERT-based profile saves (prevents CASCADE data loss)
- Full UUID IDs (collision-safe)
- Transaction-wrapped multi-statement operations
- Input length limits on regex processing (DoS prevention)
- HTML-escaped email templates
- Structured report system (7 reason categories with auto-escalation)
- Temporary/permanent suspensions with appeal workflow
- Photo perceptual hashing (duplicate/stolen photo detection)
- Conversation quality signals (response rate, reply time badges)

**Admin Dashboard**
- Separate admin portal on its own port (all endpoints require admin auth)
- Health check endpoint with server status monitoring
- Database backup scheduler with rotation and restore (SQLite backup API)
- Analytics dashboard with engagement metrics and charts
- Content filter log viewer
- Stories moderation
- Session management (view/revoke all user sessions)
- User management, group/event moderation
- Verification and photo moderation review queues
- Safety report triage with escalation queue and status filtering
- Suspension management (suspend/unsuspend with audit trail)
- Appeal review queue (uphold/overturn suspension appeals)
- Platform statistics
- Audit log with action filtering
- Webhook management (CRUD + HMAC-signed delivery)
- Email template preview
- Rate limit dashboard
- Database vacuum controls
- User search with detailed activity view
- Announcement management (create/delete platform-wide notices)
- Flagged content queue (flag/review/resolve with type filtering)
- Bulk profile actions (deactivate, delete, verify multiple users)
- CSV export (users, safety reports, analytics)
- Engagement over time chart (signups, messages, matches line graph)
- Shadow ban management (invisible content suppression)
- Canned responses (reusable admin reply templates with usage tracking)
- Feature flags (toggle features without deploy)
- Request stats dashboard (total requests, error rate, avg response time, top endpoints)
- Admin-to-user messaging (direct + batch send to all users)
- Retention cohort chart (week-over-week retention rates)
- User funnel visualization (signup → profile → questionnaire → match → message → date)
- Request log cleanup controls

**Platform**
- Progressive Web App (installable, offline caching)
- Web push notifications
- Premium subscription tier scaffolding
- i18n framework (internationalization-ready with JSON locale files)
- Audit log (admin action tracking)
- Webhook system (configurable outbound webhooks)
- HTML email templates (verification, reset, match notifications)
- Database vacuum scheduler
- API rate limit dashboard (admin)
- Health check endpoint (`/api/health`)
- Read-only public API (profiles, events, stats with API key auth)
- OAuth social login scaffolding (Google, Apple)
- API key management (admin create/revoke with HMAC hashing)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, Uvicorn |
| Database | SQLite (WAL mode, thread-local pooling); PostgreSQL migration utility |
| Embeddings | sentence-transformers (all-mpnet-base-v2, MiniLM fallback) |
| Narratives | Puter.js (client-side) |
| Frontend | Vanilla JS single-file SPA |
| Auth | JWT (pyjwt + passlib/bcrypt), 2FA TOTP, WebSocket JWT |
| Security | CORS (locked to localhost), slowapi rate limiting, magic byte validation, XSS escaping |
| Jobs | Dramatiq workers over Redis (production), inline fallback (development) |
| Theme | Catppuccin Mocha (dark) / Latte (light) |
| Deploy | Docker, docker-compose, Caddy |

## Project Structure

```
kindred/
  start.py              # Turnkey launcher
  app/
    config.py           # Centralized env-based config
    main.py             # User API server (120+ endpoints)
    admin_app.py        # Admin API server
    ws_app.py           # Dedicated WebSocket worker entrypoint
    job_queue.py        # Dramatiq broker and queue submission policy
    tasks.py            # Embedding and photo-moderation actors
    database.py         # SQLite CRUD (70+ tables)
    engine.py           # 8-dimension matching engine
    questions.py        # Questionnaire definitions
  static/
    index.html          # User SPA
    admin.html          # Admin SPA
    logo.svg            # Logo
    favicon.svg         # Favicon
```

## The 8 Dimensions

| Dimension | What it measures |
|-----------|-----------------|
| Personality | Big Five traits (OCEAN) cross-correlated with scenarios |
| Values | Core life priorities and moral foundations |
| Communication | Conflict style, love language, emotional expression |
| Financial | Spending habits, financial goals, money attitudes |
| Attachment | Attachment style (secure, anxious, avoidant, fearful) |
| Tradeoffs | Life preference polarities (city/country, save/spend, etc.) |
| Semantic | Free-text response similarity via sentence embeddings |
| Dealbreaker | Hard compatibility filters |

## Running Locally (Development)

```bash
git clone https://github.com/SysAdminDoc/kindred.git
cd kindred
python start.py
```

The launcher auto-creates a virtual environment, installs dependencies, and starts both servers.

- **User portal**: http://localhost:8000
- **Admin portal**: http://localhost:8001
  - Default login: `admin@kindred.local` / `admin`

### Docker

```bash
cp .env.example .env
docker compose up --build
```

The root Docker Compose file and `start.py` are intentionally convenient
two-server development launchers. For a horizontally scaled deployment, use
the production stack instead:

```bash
cp deploy/.env.production .env
# Fill in the required values, then replace YOUR_DOMAIN in deploy/Caddyfile
docker compose -f deploy/docker-compose.prod.yml up --build -d
```

The production gateway sends user traffic to the user API workers on port
8000, admin traffic to the admin workers on port 8001, and `/ws/*` upgrades to
dedicated WebSocket workers on port 8002. Redis supplies shared rate limits,
refresh sessions, WebSocket pub/sub, connection presence, and the Dramatiq job
broker; the production stack starts a persistent Redis service and requires it
for every worker. The separate job worker handles profile embeddings and photo
moderation queue records.

### PostgreSQL migration

SQLite remains the local-development default. To migrate an existing database
into an empty PostgreSQL database, install the normal requirements and run the
explicit bridge command:

```bash
python -m app.postgres_migration --sqlite ./kindred.db --dry-run --json
export KINDRED_POSTGRES_DSN='postgresql://kindred:password@localhost/kindred'
python -m app.postgres_migration --sqlite ./kindred.db --postgres-dsn "$KINDRED_POSTGRES_DSN"
```

The command refuses a non-empty target, creates PostgreSQL-compatible tables,
constraints, indexes, and identity sequences, streams rows in batches, and
verifies per-table row counts before committing. It never drops or overwrites
the SQLite source. The application continues using SQLite until a separately
planned PostgreSQL runtime cutover is performed.

## Configuration

Copy `.env.example` to `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `KINDRED_JWT_SECRET` | *auto-persisted* | JWT signing key (saved to `.jwt_secret`) |
| `KINDRED_ADMIN_EMAIL` | `admin@kindred.local` | Default admin email |
| `KINDRED_ADMIN_PASSWORD` | `admin` | Default admin password |
| `KINDRED_HOST` | `127.0.0.1` | Server bind address |
| `KINDRED_USER_PORT` | `8000` | User portal port |
| `KINDRED_ADMIN_PORT` | `8001` | Admin portal port |
| `KINDRED_CORS_ORIGINS` | `localhost:8000,8001` | Allowed CORS origins |
| `KINDRED_RATE_LIMIT` | `60/minute` | General rate limit |
| `KINDRED_RATE_LIMIT_AUTH` | `10/minute` | Auth endpoint rate limit |
| `KINDRED_REDIS_URL` | empty | Redis URL for shared rate limits, sessions, WebSocket pub/sub, and presence |
| `KINDRED_REDIS_REQUIRED` | `false` | Fail startup instead of falling back when Redis is unavailable |
| `KINDRED_REDIS_KEY_PREFIX` | `kindred` | Prefix for Redis session keys |
| `KINDRED_USER_WORKERS` | `2` | User API worker count in the production Compose stack |
| `KINDRED_ADMIN_WORKERS` | `1` | Admin API worker count in the production Compose stack |
| `KINDRED_WS_WORKERS` | `2` | Dedicated WebSocket worker count in the production Compose stack |
| `KINDRED_QUEUE_ENABLED` | `false` | Enable Dramatiq embedding and moderation jobs |
| `KINDRED_QUEUE_REQUIRED` | `false` | Fail startup instead of falling back to inline jobs |
| `KINDRED_QUEUE_PROCESSES` | `2` | Dramatiq worker process count in the production Compose stack |
| `KINDRED_QUEUE_THREADS` | `2` | Dramatiq threads per worker process in the production Compose stack |
| `KINDRED_MAX_UPLOAD_MB` | `30` | Max file upload size |
| `KINDRED_EMBEDDING_MODEL` | `all-mpnet-base-v2` | Preferred semantic embedding model |
| `KINDRED_EMBEDDING_FALLBACK_MODEL` | `all-MiniLM-L6-v2` | Fallback when the preferred model cannot load |

For a multi-worker production deployment, set `KINDRED_REDIS_URL` and
`KINDRED_REDIS_REQUIRED=true`; the split user/admin/WebSocket topology also
uses Redis pub/sub and short-lived presence leases to keep notifications and
online status correct across processes. Leaving the requirement disabled
intentionally keeps local development on SQLite sessions, in-memory rate
limiting, process-local WebSocket delivery, and inline embedding/moderation
work. Production should keep both queue flags enabled and run the supplied
`kindred-worker` systemd service or Compose service.

For a bare-metal systemd deployment, install `deploy/kindred-ws.service` and
`deploy/kindred-worker.service` alongside the existing user/admin units and
enable all four services. The supplied Caddyfile expects the WebSocket worker
on localhost:8002.

## License

This project is licensed under the [Business Source License 1.1](LICENSE.md).

**What this means:**
- You can read, fork, and study the code freely
- You can use it for personal, non-commercial purposes
- Commercial use (running a competing service, selling it, etc.) requires written permission from the licensor
- On **March 15, 2030**, the license automatically converts to **MIT**, making it fully open source

This license exists to protect the project while keeping the code transparent. See [LICENSE.md](LICENSE.md) for full terms.
