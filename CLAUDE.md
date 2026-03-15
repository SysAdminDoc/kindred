# Kindred v1.6.0

Compatibility-first dating + social platform. Open source, privacy-first.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, Uvicorn, WebSocket
- **Database**: SQLite with WAL mode, thread-local connection pooling
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) for semantic similarity
- **Narratives**: Puter.js (client-side, no API key)
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
  uploads/              # Photos, videos, verification selfies, voice messages
  backups/              # Auto-created database backups
  locales/              # i18n JSON translation files (auto-created)
  app/
    config.py           # Centralized config (env vars / .env file)
    main.py             # FastAPI user server (port 8000, 90+ endpoints)
    admin_app.py        # FastAPI admin server (port 8001)
    questions.py        # Questionnaire: Big Five, scenarios, trade-offs, behavioral, self-disclosure, communication, financial, energy
    engine.py           # Matching: 8-dimension scoring, calibration, coaching, template narratives
    database.py         # SQLite CRUD: 40+ tables, thread-local pooling, schema versioning
    content_filter.py   # Profanity/spam detection + censoring
    logging_config.py   # Structured JSON/text logging
    backup.py           # Database backup scheduler with rotation
    i18n.py             # Internationalization framework (JSON locales)
  static/
    index.html          # User SPA
    admin.html          # Admin SPA
    manifest.json       # PWA manifest
    service-worker.js   # Push notifications + offline caching
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
- `KINDRED_LOCATION_RADIUS_KM` - Default location matching radius
- `KINDRED_STORY_EXPIRY_HOURS` - Story lifetime (default 24)
- `KINDRED_MATCH_EXPIRY_DAYS` - Match expiry without messaging (default 7)
- `KINDRED_BACKUP_DIR` / `KINDRED_BACKUP_KEEP_COUNT` / `KINDRED_BACKUP_INTERVAL_HOURS` - Backup settings
- `KINDRED_DEFAULT_LOCALE` - Default language (default en)

## Database Tables
profiles, messages, invites, feedback, date_plans, behavioral_events, safety_reports, profile_blog_posts, profile_comments, profile_friends, notifications, users, likes, status_updates, activity_feed, groups, group_members, group_posts, events, event_rsvps, compat_games, selfie_verifications, video_intros, music_preferences, blocks, password_resets, notification_preferences, schema_versions, refresh_tokens, email_verifications, photo_moderation, questionnaire_progress, message_reactions, daily_suggestions, totp_secrets, push_subscriptions, group_messages, content_filter_log, premium_subscriptions, analytics_events, voice_messages, profile_prompts, super_likes, stories, story_views, group_polls, poll_votes, user_sessions, user_locations, recovery_codes

## Key Features
- **8-dimension matching**: Personality, values, communication, financial, attachment, tradeoffs, semantic, dealbreaker
- **Compatibility radar chart**: Canvas spider chart for 8 dimensions
- **WebSocket real-time**: Live messaging, typing indicators, online status, read receipts
- **Voice messages**: MediaRecorder recording + in-chat playback
- **Message search**: Search through conversation history
- **Profile prompts**: Hinge-style prompts (up to 3 per profile)
- **Super Like**: Special like with instant notification
- **Match expiry**: 7-day countdown on uncontacted matches
- **Stories/Moments**: 24-hour ephemeral posts (text on gradient or photo)
- **Polls in groups**: Create polls, vote, see results
- **Location matching**: Geolocation + distance filtering with Haversine approximation
- **Mutual friends**: Count and list mutual connections
- **Compatibility games**: "This or That" paired questions with score tracking
- **Selfie verification**: Upload selfie, admin reviews, get verified badge
- **Video intros**: Upload short video clips shown on profiles
- **Music matching**: Add songs/artists, compute music compatibility between pairs
- **Groups & Events**: Create communities, post, RSVP to events, group moderation
- **MySpace-style profiles**: Blog, comments, friends, photo gallery, profile themes
- **Photo gallery**: Multi-photo with primary designation, auto-thumbnails
- **Image cropping**: Crop/rotate before upload via Canvas API
- **Date plans**: Propose/accept/decline/complete
- **Incognito mode**: Browse without appearing in Who Viewed Me
- **Session management**: View/revoke active sessions
- **Account deletion**: GDPR-compliant full data removal
- **Data export**: GDPR-compliant download your data
- **2FA TOTP + recovery codes**: Authenticator app 2FA with backup codes
- **Safety**: Block/report with admin review, profile blocking
- **Profile themes**: Cosmic, Forest, Sunset, Ocean, Aurora gradient themes
- **Activity feed**: Friend activity aggregation
- **Search**: Multi-filter (gender, seeking, age, location)
- **Notification sounds**: AudioContext two-tone beep
- **Admin dashboard**: Stats, health check, backups, sessions, stories moderation, groups/events/verifications management
- **Settings**: Notification preferences, password change, blocked users, profile deactivation, incognito, location, language
- **Message pagination**: Load older messages, optimistic send UI
- **Message reactions**: Emoji reactions on messages
- **Daily suggestions**: Top Picks curated daily match suggestions
- **Who Viewed Me**: See who visited your profile
- **Who Liked You**: See who liked your profile (premium-gatable)
- **Web push notifications**: Service worker + Push API for background notifications
- **Group chat**: Real-time WebSocket messaging within groups
- **Events calendar**: Month grid calendar view with event indicators
- **GIF search**: Tenor API integration for in-chat GIF sharing
- **Guided onboarding**: First-time user walkthrough tour
- **Content filtering**: Automated profanity censoring and spam blocking
- **Premium tier**: Subscription scaffolding with gated features
- **Analytics dashboard**: Admin engagement metrics, daily signups chart, feature metrics
- **PWA**: Installable web app with offline caching
- **Database backups**: Automatic scheduled backups with rotation and restore
- **i18n framework**: JSON-based translations, locale selector, extensible
- **Health check**: `/api/health` endpoint with server status, DB size, version

## Key Architecture
- Dual-server: user (8000) + admin (8001) sharing same SQLite DB
- `app/config.py`: Central config from env vars / .env file (JWT secret auto-generated)
- `authFetch` pattern: frontend wrapper auto-includes JWT Authorization header
- `ConnectionManager`: per-profile WebSocket connection lists (multi-tab support)
- Thread-local SQLite connection pooling with WAL mode + busy timeout
- Database migrations via `_migrate()` with try/except ALTER TABLE
- Schema version tracking via `schema_versions` table (currently v5)
- CORS middleware on both servers
- Rate limiting on auth endpoints (slowapi)
- File upload magic byte validation (prevents extension spoofing)
- Auth (`require_user`) on all mutating user endpoints
- Puter.js CDN for match narratives - zero backend cost, template fallbacks
- Docker + docker-compose for deployment
- Pillow for auto-thumbnail generation
- Background backup scheduler (configurable interval + retention)
- i18n: JSON locale files in `locales/`, `t()` helper, fallback to English

## Version History

- **v1.6.0** - Core Dating: voice messages (MediaRecorder), profile prompts (Hinge-style), super like with notification, match expiry (7-day countdown), location-based matching (geolocation + distance), compatibility radar chart (canvas spider). Social: stories/moments (24h ephemeral), polls in groups, mutual friends indicator, message search. Safety: incognito mode, session management (view/revoke), account deletion (GDPR), data export (GDPR), 2FA recovery codes. UX: notification sounds (AudioContext), image cropping (Canvas API). Ops: health check endpoint, database backup scheduler with rotation/restore, i18n framework (JSON locales). Admin: health status card, backup management tab, session management tab, stories moderation, expanded analytics, i18n management
- **v1.5.0** - Features: daily match suggestions (top picks), message reactions, who viewed me, who liked you (premium-gatable), group chat (WebSocket), events calendar view, GIF search (Tenor), guided onboarding tour, 2FA TOTP. Infrastructure: content filtering (profanity/spam), premium subscription scaffolding, analytics events tracking, PWA (manifest + service worker + push notifications). Admin: analytics dashboard (summary cards, daily signups chart, engagement metrics), content filter log viewer
- **v1.4.0** - Security: refresh token rotation, configurable bcrypt rounds, email verification flow, photo moderation queue. Infrastructure: structured JSON/text logging, new DB tables (refresh_tokens, email_verifications, photo_moderation, questionnaire_progress), schema v3 migration. Backend: questionnaire progress save/restore endpoints, logout/logout-all, refresh token endpoint. Admin: photo moderation review (approve/reject). Frontend: OpenGraph/description meta tags, theme-color, expanded mobile responsive (768px + 400px breakpoints), ARIA roles (banner/main/status+live), keyboard focus-visible outlines, sr-only utility, questionnaire progress persistence (save/load via API), skeleton loading states for Matches/Feed/Discover/Groups/Events
- **v1.3.0** - Security hardening (env config, auth on all endpoints, rate limiting, CORS, file magic validation), architecture (connection pooling, config module, schema versioning), features (profile blocking, read receipts, notification prefs, password reset/change, profile deactivation, auto-thumbnails, message pagination, group moderation), UX (toast stacking, loading skeletons, optimistic messaging, empty state CTAs), deployment (Docker, .env config)
- **v1.2.0** - Video intros (upload/view/delete), music preferences (add songs, compute compatibility between pairs), music compatibility on match detail view
- **v1.1.0** - Compatibility games ("This or That" with paired scoring), selfie verification (upload + admin approve/reject), admin verification review tab
- **v1.0.0** - Polish: admin groups/events management tabs, online status indicators (green dot), profile completeness bar, improved mobile responsive, groups/events counts in admin dashboard
- **v0.12.0** - WebSocket real-time messaging, typing indicators, photo messages, photo gallery, search, activity feed, groups, events, profile themes, discover tab
- **v0.11.0** - JWT auth (user + admin), notifications with bell, likes system, status updates, explore/recent profiles
- **v0.6.0** - Admin/User port separation
- **v0.5.0** - MySpace-style profile pages
- **v0.4.0** - 8-dimension matching, one-question-per-screen, coaching tips, date plans
- **v0.3.0** - Puter.js narratives (replaced Ollama)
- **v0.2.0** - Major feature expansion
- **v0.1.0** - Initial build
