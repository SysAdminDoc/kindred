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
- Voice messages (MediaRecorder API recording + playback) with optional server-side transcripts for accessibility
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
- Groups and events with RSVP + calendar view + local meetup discovery with a Leaflet heatmap
- Optional ticketed event RSVPs with Stripe PaymentIntents, idempotent payment records, and signed webhook confirmation
- Profile boost (premium visibility boost with countdown timer)
- Video intros and music preferences with cross-user compatibility scoring
- "This or That" compatibility games between matched pairs
- Who Viewed Me and Who Liked You feeds
- Guided onboarding tour for new users
- Notification sounds (AudioContext two-tone beep)
- Image cropping before upload (Canvas API)
- Icebreaker games (Word Association, Would You Rather, 20 Questions)
- Date scheduling with ICS calendar export
- Shared match calendars with revocable, tokenized ICS subscription URLs
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
- CCPA do-not-sell preference (enabled by default; Kindred does not sell personal information)
- Selfie verification with admin review and local ML liveness (blink + head turn)
- Sliding-window direct-message harassment signals with escalating warnings and recipient-side auto-mutes
- Upload-time pHash + dHash matching against an operator-managed known-abuse hash corpus
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
- S3-compatible object storage for photos, videos, voice messages, selfies, stories, and event media with local development fallback
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
- Photo-safety event review API and hash-corpus import command
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
    object_storage.py   # Local/S3-compatible media storage
    object_storage_migration.py # Legacy uploads/ migration command
    photo_safety.py     # pHash/dHash upload screening and optional external hook
    photo_safety_corpus.py # Hash-only corpus importer
    selfie_liveness.py  # MediaPipe blink + head-turn sequence analyzer
    harassment.py       # Explainable direct-message harassment signal scoring
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
| `KINDRED_TRANSCRIPTION_ENABLED` | `false` | Enable server-side voice transcription |
| `KINDRED_TRANSCRIPTION_URL` | empty | OpenAI-compatible `/audio/transcriptions` endpoint; required when transcription is enabled |
| `KINDRED_TRANSCRIPTION_API_KEY` | empty | Optional bearer token for the configured transcription endpoint |
| `KINDRED_TRANSCRIPTION_MODEL` | `whisper-1` | Model name sent to the transcription endpoint |
| `KINDRED_TRANSCRIPTION_TIMEOUT_SECONDS` | `120` | Per-audio transcription request timeout |
| `KINDRED_INACTIVE_ACCOUNT_HARD_DELETE_MONTHS` | `24` | Months after deactivation before scheduled hard deletion |
| `KINDRED_PRIVACY_RETENTION_INTERVAL_HOURS` | `24` | Scheduler interval for retention cleanup and inactive-account deletion |
| `KINDRED_MAX_UPLOAD_MB` | `30` | Max file upload size |
| `KINDRED_OBJECT_STORAGE_ENDPOINT` | empty | S3-compatible endpoint; leave unset for local `uploads/` storage |
| `KINDRED_OBJECT_STORAGE_BUCKET` | empty | Remote media bucket; supplying it enables S3-compatible storage |
| `KINDRED_OBJECT_STORAGE_ACCESS_KEY` | empty | S3-compatible access key or IAM-compatible credential |
| `KINDRED_OBJECT_STORAGE_SECRET_KEY` | empty | S3-compatible secret key |
| `KINDRED_OBJECT_STORAGE_REGION` | `us-east-1` | S3-compatible signing region |
| `KINDRED_OBJECT_STORAGE_PREFIX` | `media` | Remote object-key prefix; logical database keys remain unchanged |
| `KINDRED_OBJECT_STORAGE_PUBLIC_URL` | empty | Optional public/CDN base URL; empty keeps media private behind `/uploads/` |
| `KINDRED_OBJECT_STORAGE_REQUIRED` | `false` | Fail startup instead of serving new media from an unavailable or missing remote backend |
| `KINDRED_OBJECT_STORAGE_ADDRESSING_STYLE` | `auto` (`path` with an endpoint) | S3 addressing mode; `path` is recommended for MinIO and many S3-compatible services |
| `KINDRED_PHOTO_HASH_ENABLED` | `true` | Enable local pHash + dHash matching against the known-abuse corpus |
| `KINDRED_PHOTO_HASH_MAX_DISTANCE` | `5` | Maximum pHash Hamming distance for a local corpus match |
| `KINDRED_PHOTO_DHASH_MAX_DISTANCE` | `8` | Maximum dHash Hamming distance for a local corpus match |
| `KINDRED_PHOTO_SAFETY_REQUIRED` | `false` | Reject uploads if the enabled safety scan cannot complete |
| `KINDRED_PHOTODNA_ENABLED` | `false` | Enable the operator-provided PhotoDNA hash webhook adapter |
| `KINDRED_PHOTODNA_HOOK_URL` | empty | Provider-specific hash adapter URL, required when the hook is enabled |
| `KINDRED_PHOTODNA_API_KEY` | empty | Optional subscription key passed to the configured adapter |
| `KINDRED_PHOTODNA_TIMEOUT_SECONDS` | `3` | External hash adapter timeout |
| `KINDRED_HARASSMENT_ENABLED` | `true` | Enable direct-message harassment signal scoring |
| `KINDRED_HARASSMENT_WINDOW_MINUTES` | `10` | Sliding window used to aggregate sender/recipient signals |
| `KINDRED_HARASSMENT_WARN_SCORE` | `2` | Aggregate score at which a respectful-message warning is returned |
| `KINDRED_HARASSMENT_MUTE_SCORE` | `4` | Aggregate score at which the recipient-side auto-mute activates |
| `KINDRED_HARASSMENT_MUTE_MINUTES` | `60` | Auto-mute duration |
| `KINDRED_REPORT_COOLING_OFF_DAYS` | `30` | Days a reporter is excluded from seeing a reported profile; `0` is permanent |
| `KINDRED_STRIPE_ENABLED` | `false` | Enable Stripe PaymentIntent ticketing for paid events |
| `KINDRED_STRIPE_SECRET_KEY` | empty | Stripe server-side secret key; required when ticketing is enabled |
| `KINDRED_STRIPE_PUBLISHABLE_KEY` | empty | Stripe browser key returned only for paid event checkout |
| `KINDRED_STRIPE_WEBHOOK_SECRET` | empty | Stripe webhook signing secret; required to confirm payment status |
| `KINDRED_EVENT_PAYMENT_HOLD_MINUTES` | `30` | Reservation hold for an unfinished paid RSVP |
| `KINDRED_SELFIE_LIVENESS_ENABLED` | `true` | Enable local MediaPipe selfie liveness |
| `KINDRED_SELFIE_LIVENESS_REQUIRED` | `true` | Require a passing blink + head-turn sequence before queueing verification |
| `KINDRED_SELFIE_LIVENESS_MODEL_PATH` | `models/face_landmarker.task` | Local Face Landmarker model asset |
| `KINDRED_SELFIE_LIVENESS_MODEL_SHA256` | pinned asset hash | Fail startup if the model asset is not the pinned file |
| `KINDRED_SELFIE_LIVENESS_MIN_FRAMES` | `8` | Minimum ordered frames in a liveness attempt |
| `KINDRED_SELFIE_LIVENESS_MAX_FRAMES` | `24` | Maximum ordered frames accepted per attempt |
| `KINDRED_SELFIE_LIVENESS_FRAME_INTERVAL_MS` | `150` | Synthetic interval used when clients submit frames without timestamps |
| `KINDRED_SELFIE_LIVENESS_MIN_DURATION_MS` | `900` | Minimum sequence duration |
| `KINDRED_SELFIE_LIVENESS_BLINK_CLOSED_EAR` | `0.20` | Eye-aspect-ratio threshold for a closed-eye frame |
| `KINDRED_SELFIE_LIVENESS_BLINK_OPEN_EAR` | `0.24` | Eye-aspect-ratio threshold for an open-eye frame |
| `KINDRED_SELFIE_LIVENESS_HEAD_TURN_DELTA` | `0.12` | Relative nose/yaw movement required for a head turn |
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

Voice notes remain playable when transcription is disabled or temporarily
unavailable. To add accessible transcripts, set
`KINDRED_TRANSCRIPTION_ENABLED=true` and point `KINDRED_TRANSCRIPTION_URL` at
an approved OpenAI-compatible `/audio/transcriptions` service (a local
Whisper-compatible service works as well). Transcripts are generated in the
dedicated `kindred-transcription` worker queue when Redis/Dramatiq is enabled;
local development falls back to inline processing and exposes a pending or
unavailable state in the conversation UI.

The privacy audit records a classification and retention strategy for every
schema field and table. Administrators can inspect coverage at
`/api/admin/privacy/audit`. Deactivated accounts are hard-deleted after
`KINDRED_INACTIVE_ACCOUNT_HARD_DELETE_MONTHS`; the scheduled purge also removes
unlinked OAuth, analytics, request-log, and media records for the account.

When object storage is configured, the API stores new media under the
configured bucket and serves it through the existing `/uploads/{key}` contract;
the default keeps the bucket private and supports photo, audio, and video byte
ranges. Existing files in `uploads/` remain readable as a migration fallback.
Set `KINDRED_OBJECT_STORAGE_REQUIRED=true` in production so a missing bucket or
unavailable endpoint fails startup instead of silently writing new media to
local disk. The production environment template enables this fail-closed mode;
replace its example endpoint and credentials before launch.

The local safety corpus stores only 64-bit pHash/dHash pairs and metadata. Import
an operator-approved JSON corpus with
`python -m app.photo_safety_corpus corpus.json --source operator --dry-run`,
then rerun without `--dry-run`. Blocked upload metadata is visible to admins at
`/api/admin/photo-safety/events`.

Direct messages are checked before delivery for explainable threat, sexual
coercion, slur, and targeted-abuse signals. Signals are retained as category
and score metadata only; repeated signals are aggregated per sender/recipient
pair inside the configured sliding window. The first threshold returns a
respectful-message warning, while the mute threshold creates a one-way
recipient-side mute and suppresses later direct messages until it expires.
The WebSocket message path applies the same gate, and administrators can
review events and active mutes at `/api/admin/harassment`.

Reports immediately create a reporter-specific cooling-off exclusion, so the
reported profile is removed from matches, suggestions, search, explore, nearby,
availability, and recently-active/new-user discovery. The exclusion lasts
`KINDRED_REPORT_COOLING_OFF_DAYS` days and is renewed by later reports; set it
to `0` when the product policy requires a permanent exclusion. Reviewing or
closing a report does not lift the exclusion automatically.

Event ticketing remains free and local by default. To enable paid events, set
the Stripe keys and `KINDRED_STRIPE_ENABLED=true`; paid event creation then
requires a ticket price of at least 50 cents. The RSVP endpoint creates one
idempotent PaymentIntent per active attempt and returns only its client secret
to the browser. Stripe webhook signatures are verified before an RSVP changes
from pending to paid, and unfinished attempts reserve a seat only for the
configured hold window. The host is automatically marked as attending without
being charged.

Matched pairs can also create a shared calendar subscription from the date
scheduling panel. The URL is a revocable bearer credential stored only as a
hash; it includes both proposed and confirmed dates, reflects cancellations,
and stops serving as soon as the pair is blocked, reported, or no longer
mutually matched. The one-off `.ics` export remains authenticated to the date
participants.

Selfie verification now captures twelve camera frames in the user portal and
posts them as a short ordered sequence to `/api/verify/selfie/{profile_id}`.
The server runs the bundled MediaPipe Face Landmarker locally, requires a
blink and measurable head turn, stores only the first passing frame, and keeps
aggregate liveness evidence with the admin review record. If camera access is
unavailable, users can submit at least eight still frames through the fallback
picker. Set `KINDRED_SELFIE_LIVENESS_REQUIRED=false` only for a deliberately
degraded legacy still-image workflow.

To migrate an existing local upload directory, first configure the remote
backend and run `python -m app.object_storage_migration --dry-run`, then rerun
without `--dry-run`. The command is repeatable and leaves local files in place
until the remote bucket has been verified.

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
