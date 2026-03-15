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
  <img src="https://img.shields.io/badge/version-1.6.0-cba6f7?style=flat-square" alt="Version">
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
- Compatibility radar chart (canvas spider chart for 8 dimensions)
- sentence-transformers embeddings for semantic similarity
- Match narratives, icebreakers, and coaching tips
- Customizable dimension weights per user
- Photo reveal at compatibility threshold
- Daily curated Top Picks suggestions
- Super Like with instant notification
- Match expiry (7-day countdown without messaging)
- Location-based matching with distance filtering
- Mutual friends indicator

**Social Platform**
- Real-time WebSocket messaging with typing indicators and read receipts
- Voice messages (MediaRecorder API recording + playback)
- Message reactions (emoji) and GIF search (Tenor API)
- Message search across conversations
- Group chat with real-time WebSocket messaging
- Polls in groups (create, vote, results)
- Stories/Moments (24-hour ephemeral posts with gradient backgrounds)
- MySpace-style profile pages with blog, comments, friends, photo gallery
- Profile prompts (Hinge-style "Two truths and a lie", "My ideal Sunday", etc.)
- Profile themes (Cosmic, Forest, Sunset, Ocean, Aurora)
- Status updates and activity feed
- Groups and events with RSVP + calendar view
- Video intros and music preferences with cross-user compatibility scoring
- "This or That" compatibility games between matched pairs
- Who Viewed Me and Who Liked You feeds
- Guided onboarding tour for new users
- Notification sounds (AudioContext two-tone beep)
- Image cropping before upload (Canvas API)

**Trust & Safety**
- Two-factor authentication (TOTP) with recovery codes
- Incognito mode (browse without appearing in Who Viewed Me)
- Session management (view/revoke active sessions)
- Account deletion (GDPR-compliant full data removal)
- Data export (GDPR-compliant download your data)
- Selfie verification with admin review
- Automated content filtering (profanity censoring, spam blocking)
- Photo moderation queue with admin review
- Profile blocking and safety reports
- Rate-limited auth endpoints
- File upload magic byte validation
- JWT authentication on all mutating endpoints

**Admin Dashboard**
- Separate admin portal on its own port
- Health check endpoint with server status monitoring
- Database backup scheduler with rotation and restore
- Analytics dashboard with engagement metrics and charts
- Content filter log viewer
- Stories moderation
- Session management (view/revoke all user sessions)
- User management, group/event moderation
- Verification and photo moderation review queues
- Safety report triage
- Platform statistics

**Platform**
- Progressive Web App (installable, offline caching)
- Web push notifications
- Premium subscription tier scaffolding
- i18n framework (internationalization-ready with JSON locale files)
- Health check endpoint (`/api/health`)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12+, FastAPI, Uvicorn |
| Database | SQLite (WAL mode, thread-local pooling) |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Narratives | Puter.js (client-side) |
| Frontend | Vanilla JS single-file SPA |
| Auth | JWT (pyjwt + passlib/bcrypt) |
| Security | CORS, slowapi rate limiting, magic byte validation |
| Theme | Catppuccin Mocha |
| Deploy | Docker, docker-compose |

## Project Structure

```
kindred/
  start.py              # Turnkey launcher
  app/
    config.py           # Centralized env-based config
    main.py             # User API server (70+ endpoints)
    admin_app.py        # Admin API server
    database.py         # SQLite CRUD (20+ tables)
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

## Configuration

Copy `.env.example` to `.env` to customize:

| Variable | Default | Description |
|----------|---------|-------------|
| `KINDRED_JWT_SECRET` | *auto-generated* | JWT signing key |
| `KINDRED_ADMIN_EMAIL` | `admin@kindred.local` | Default admin email |
| `KINDRED_ADMIN_PASSWORD` | `admin` | Default admin password |
| `KINDRED_HOST` | `127.0.0.1` | Server bind address |
| `KINDRED_USER_PORT` | `8000` | User portal port |
| `KINDRED_ADMIN_PORT` | `8001` | Admin portal port |
| `KINDRED_CORS_ORIGINS` | `*` | Allowed CORS origins |
| `KINDRED_RATE_LIMIT` | `60/minute` | General rate limit |
| `KINDRED_RATE_LIMIT_AUTH` | `10/minute` | Auth endpoint rate limit |
| `KINDRED_MAX_UPLOAD_MB` | `30` | Max file upload size |

## License

This project is licensed under the [Business Source License 1.1](LICENSE.md).

**What this means:**
- You can read, fork, and study the code freely
- You can use it for personal, non-commercial purposes
- Commercial use (running a competing service, selling it, etc.) requires written permission from the licensor
- On **March 15, 2030**, the license automatically converts to **MIT**, making it fully open source

This license exists to protect the project while keeping the code transparent. See [LICENSE.md](LICENSE.md) for full terms.
