# Kindred v1.9.0

Compatibility-first dating + social platform. Open source, privacy-first.

## Tech Stack
- **Backend**: Python 3.12+, FastAPI, Uvicorn, WebSocket
- **Database**: SQLite with WAL mode, thread-local connection pooling
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2) for semantic similarity
- **Narratives**: Puter.js (client-side, no API key)
- **Frontend**: Single-file SPA (vanilla JS), Catppuccin Mocha/Latte themes
- **Auth**: JWT (pyjwt + passlib[bcrypt]), 72-hour token expiry, persistent secret (file-backed), 2FA TOTP enforcement
- **Security**: CORS locked to localhost by default, rate limiting (slowapi), file magic byte validation, auth on all endpoints (user + admin), WebSocket JWT auth, XSS-safe HTML escaping, input length limits on regex
- **Config**: python-dotenv, `app/config.py` centralizes all settings, JWT secret auto-persisted to `.jwt_secret`

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
    main.py             # FastAPI user server (port 8000, 120+ endpoints)
    admin_app.py        # FastAPI admin server (port 8001)
    questions.py        # Questionnaire: Big Five, scenarios, trade-offs, behavioral, self-disclosure, communication, financial, energy
    engine.py           # Matching: 8-dimension scoring, calibration, coaching, template narratives
    database.py         # SQLite CRUD: 60+ tables, thread-local pooling, schema versioning
    content_filter.py   # Profanity/spam detection + censoring
    logging_config.py   # Structured JSON/text logging
    backup.py           # Database backup scheduler with rotation (SQLite backup API)
    i18n.py             # Internationalization framework (JSON locales, contextvars)
    audit.py            # Admin action audit logging
    webhooks.py         # Configurable outbound webhooks
    email_templates.py  # HTML email templates (Catppuccin themed)
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
- `KINDRED_JWT_SECRET` - JWT signing key (auto-persisted to `.jwt_secret` if not set)
- `KINDRED_ADMIN_EMAIL` / `KINDRED_ADMIN_PASSWORD` - Default admin creds
- `KINDRED_HOST` / `KINDRED_USER_PORT` / `KINDRED_ADMIN_PORT` - Server binding
- `KINDRED_CORS_ORIGINS` - Comma-separated allowed origins
- `KINDRED_RATE_LIMIT` / `KINDRED_RATE_LIMIT_AUTH` - Rate limiting
- `KINDRED_LOCATION_RADIUS_KM` - Default location matching radius
- `KINDRED_STORY_EXPIRY_HOURS` - Story lifetime (default 24)
- `KINDRED_MATCH_EXPIRY_DAYS` - Match expiry without messaging (default 7)
- `KINDRED_BACKUP_DIR` / `KINDRED_BACKUP_KEEP_COUNT` / `KINDRED_BACKUP_INTERVAL_HOURS` - Backup settings
- `KINDRED_DEFAULT_LOCALE` - Default language (default en)
- `KINDRED_BLIND_DATE_HOURS` - Blind date reveal timer (default 48)
- `KINDRED_MESSAGE_COOLDOWN_MINUTES` / `KINDRED_MESSAGE_COOLDOWN_COUNT` - Message rate limiting
- `KINDRED_UNDO_BLOCK_MINUTES` - Block undo grace period (default 5)
- `KINDRED_SAFETY_CHECKIN_MINUTES` - Safety check-in timer (default 60)
- `KINDRED_VACUUM_INTERVAL_HOURS` - DB vacuum interval (default 168)
- `KINDRED_WEBHOOKS_ENABLED` - Enable outbound webhooks
- `KINDRED_DEFAULT_THEME` - Default theme: mocha or latte

## Database Tables
profiles, messages, invites, feedback, date_plans, behavioral_events, safety_reports, profile_blog_posts, profile_comments, profile_friends, notifications, users, likes, status_updates, activity_feed, groups, group_members, group_posts, events, event_rsvps, compat_games, selfie_verifications, video_intros, music_preferences, blocks, password_resets, notification_preferences, schema_versions, refresh_tokens, email_verifications, photo_moderation, questionnaire_progress, message_reactions, daily_suggestions, totp_secrets, push_subscriptions, group_messages, content_filter_log, premium_subscriptions, analytics_events, voice_messages, profile_prompts, super_likes, stories, story_views, group_polls, poll_votes, user_sessions, user_locations, recovery_codes, icebreaker_games, game_turns, date_schedules, blind_dates, passed_profiles, threaded_replies, shared_playlists, playlist_songs, event_photos, profile_badges, story_reactions, pinned_messages, message_cooldowns, undo_blocks, safety_checkins, audit_log, webhooks, rate_limit_log, vacuum_log, availability_status, conversation_starters, date_feedback, announcements

## Key Features
- **8-dimension matching**: Personality, values, communication, financial, attachment, tradeoffs, semantic, dealbreaker
- **Compatibility radar chart**: Canvas spider chart for 8 dimensions
- **WebSocket real-time**: Live messaging, typing indicators, online status, read receipts, auto-reconnect
- **Voice messages**: MediaRecorder recording + in-chat playback
- **Message search**: Search through conversation history
- **Profile prompts**: Hinge-style prompts (up to 3 per profile)
- **Super Like**: Special like with instant notification
- **Match expiry**: 7-day countdown on uncontacted matches
- **Stories/Moments**: 24-hour ephemeral posts (text on gradient or photo) with emoji reactions
- **Polls in groups**: Create polls, vote, see results
- **Location matching**: Geolocation + distance filtering with Haversine approximation
- **Mutual friends**: Count and list mutual connections
- **Compatibility games**: "This or That" paired questions with score tracking
- **Icebreaker games**: Word Association, Would You Rather, 20 Questions with turn-based play
- **Date scheduling**: In-app date picker with ICS calendar export
- **Blind date mode**: 48h no-photo conversation, then auto-reveal
- **Dealbreaker warnings**: Proactive conflict alerts on profile views
- **Second look**: Review previously passed profiles
- **Threaded replies**: Quote-reply to specific messages
- **Shared playlists**: Collaborative song lists between matched pairs
- **Event photo albums**: Shared galleries for group events
- **Profile badges**: Achievement system (verified, early adopter, conversation starter, etc.)
- **Pinned messages**: Pin important messages in conversations
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
- **Safety**: Block/report with undo grace period, safety check-in timer, emergency contact alerts
- **Message cooldown**: Rate limit messaging for new matches
- **Link preview scanning**: Warn on suspicious/shortened URLs
- **Profile themes**: Cosmic, Forest, Sunset, Ocean, Aurora gradient themes
- **Dark/Light theme**: Catppuccin Mocha (dark) and Latte (light) toggle
- **Keyboard shortcuts**: Tab navigation, search focus, shortcut help overlay
- **Profile completeness coaching**: Smart tips for better matches
- **Animated transitions**: Page/tab transitions, modal animations
- **Typing previews**: Opt-in message draft previews
- **Activity feed**: Friend activity aggregation
- **Search**: Multi-filter (gender, seeking, age, location)
- **Notification sounds**: AudioContext two-tone beep
- **Admin dashboard**: Stats, health check, backups, sessions, stories moderation, audit log, webhooks, rate limits, vacuum, email templates
- **Settings**: Notification preferences, password change, blocked users, profile deactivation, incognito, location, language, theme, typing preview, availability status
- **Unread badge counts**: Tab badge on Messages, page title update, per-conversation unread counts
- **Emoji picker**: 40-emoji grid popup in chat input
- **Conversation starters**: Ice-breaker suggestions for empty chats
- **Availability status**: Active/Free Tonight/Free This Weekend/Looking to Chat/Taking a Break with badges on cards
- **Announcement banners**: Dismissible system announcements (info/warning/maintenance types)
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
- **Database vacuum**: Scheduled SQLite VACUUM with admin controls
- **i18n framework**: JSON-based translations, locale selector, extensible
- **Audit log**: Admin action tracking with filtering
- **Webhook system**: Configurable outbound webhooks with HMAC signing
- **Email templates**: Catppuccin-themed HTML templates for all notifications
- **Health check**: `/api/health` endpoint with server status, DB size, version
- **Unread badge counts**: Tab badges, page title count, per-conversation unread via polling
- **Emoji picker**: 40-emoji floating grid popup on chat input
- **Conversation starters**: Personalized ice-breaker suggestions for empty chats (shared music, interests, prompts)
- **Availability status**: User-set status (active/away/busy/offline) with badges on cards
- **Announcement banners**: Admin-posted dismissible banners (info/warning/maintenance)
- **Date feedback**: Post-date rating and feedback system with stats
- **WebSocket heartbeat**: Dual ping+heartbeat every 30s with cleanup on close/logout
- **Structured error responses**: All HTTPExceptions return `{error, code}` JSON format
- **Admin user search**: Search users by email/name/ID with detailed activity view
- **Admin announcements**: Create/delete platform-wide announcements
- **Swipe gestures**: Touch swipe left/right on discover cards for pass/like
- **Infinite scroll**: Lazy-loading activity feed with IntersectionObserver
- **Image lightbox**: Full-screen photo viewer with pinch-zoom and Escape close
- **Pull-to-refresh**: Touch gesture to reload current view on mobile
- **Onboarding progress bar**: Visual question progress during questionnaire
- **Skeleton shimmer loading**: Shaped shimmer placeholders matching card layouts
- **Dealbreaker quiz**: Interactive dealbreaker comparison between matched users
- **Paginated feeds**: Offset/limit pagination for activity feed and conversations

## Key Architecture
- Dual-server: user (8000) + admin (8001) sharing same SQLite DB
- `app/config.py`: Central config from env vars / .env file, JWT secret auto-persisted to `.jwt_secret`
- `authFetch` pattern: frontend wrapper auto-includes JWT Authorization header
- `ConnectionManager`: per-profile WebSocket connection lists (multi-tab support) with JWT-authenticated connections + auto-reconnect
- Thread-local SQLite connection pooling with WAL mode + busy timeout (no manual `conn.close()`)
- Database IDs: full `uuid4().hex` (32 hex chars) for collision safety
- `save_profile()`: proper UPSERT (`ON CONFLICT DO UPDATE`) — no CASCADE data loss
- Database migrations via `_migrate()` with targeted `duplicate column` error handling
- Schema version tracking via `schema_versions` table (currently v7)
- CORS defaults to `localhost:8000,8001` (configurable via env)
- Rate limiting on auth endpoints (slowapi) with admin dashboard
- File upload magic byte validation on all upload endpoints (photos, gallery, stories, voice, video)
- Auth (`require_user`) on all user endpoints, (`require_admin`) on all admin endpoints
- 2FA TOTP enforced at login when enabled, password re-verification for disable
- XSS prevention: `escHtml()` applied to all user data in frontend innerHTML
- Multi-statement DB operations wrapped in explicit transactions
- Puter.js CDN for match narratives - zero backend cost, template fallbacks
- Docker + docker-compose for deployment
- Pillow for auto-thumbnail generation
- Background backup scheduler using SQLite backup API (configurable interval + retention)
- i18n: JSON locale files in `locales/`, `t()` helper with `contextvars` (thread-safe), fallback to English
- Audit logging for admin actions (LIKE wildcard escaped)
- Webhook system with HMAC-SHA256 signature verification
- HTML email templates with HTML-escaped user data + Catppuccin dark theme styling
- Content filter: input truncated to 10K chars before regex (DoS prevention)

## Version History

- **v1.9.0** - Phase 2: Mobile & engagement. UX: swipe gestures on discover cards (touch left=pass, right=like with tilt animation), infinite scroll for activity feed (IntersectionObserver + sentinel), image lightbox (full-screen viewer, pinch-zoom, Escape close), pull-to-refresh (touch gesture on mobile), onboarding progress bar (question count + fill bar), skeleton shimmer loading (shaped placeholders for matches/feed/discover). Features: dealbreaker quiz comparison (shared/conflicts/unique items modal), paginated feeds + conversations endpoints (offset/limit). 3 new database functions, 3 new API endpoints
- **v1.8.0** - Phase 1: UX polish + admin tools. User: unread badge counts (tab badges, page title, per-conversation via polling), emoji picker (40-emoji floating grid), smart conversation starters (personalized from shared music/interests/communication/prompts), availability status (active/away/busy/offline with profile badges), announcement banners (dismissible, type-colored). Backend: date feedback system (post-date ratings + stats), structured error responses ({error,code} format), WebSocket ping heartbeat (30s dual ping+heartbeat). Admin: user search + detail view (activity stats, sessions), announcement CRUD (info/warning/maintenance types), expanded stats. Database: schema v7, 4 new tables (availability_status, conversation_starters, date_feedback, announcements), 16 new CRUD functions
- **v1.7.0** - Core Dating: icebreaker games (word association, would you rather, 20 questions), date scheduling (ICS export), blind date mode (48h reveal), dealbreaker warnings, second look (passed profiles), compatibility insights. Social: threaded replies (quote-reply), shared playlists, event photo albums, profile badges (achievement system), story reactions (emoji), pinned messages. Trust & Safety: message cooldown (rate limiting), undo block (grace period), safety check-in (emergency contacts), link preview scanning. UX: dark/light theme toggle (Catppuccin Mocha/Latte), keyboard shortcuts, profile completeness coaching, animated transitions, typing previews, WebSocket auto-reconnect (exponential backoff). Ops: audit log (admin actions), webhook system (outbound, HMAC signed), email templates (HTML, themed), database vacuum scheduler, API rate limit dashboard. **Security audit (120 fixes)**: removed conn.close() pool corruption, replaced INSERT OR REPLACE with UPSERT, fixed block_profile column names, extended UUIDs to full hex, added WebSocket JWT auth, added auth to 47 unprotected endpoints, fixed 2FA bypass at login, added message sender verification, fixed 30+ XSS injection points with escHtml(), persisted JWT secret to file, locked CORS to localhost, added file validation to all upload endpoints, switched to SQLite backup API, added transaction wrapping, fixed memory leaks, HTML-escaped email templates, thread-safe i18n
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
