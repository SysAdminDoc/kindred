# Kindred Roadmap

Forward-looking scope for the compatibility-first dating + social platform (FastAPI + vanilla JS SPA + SQLite, 8-dimension matching engine).

## Planned Features

### Matching Engine
- Replace `all-MiniLM-L6-v2` with `all-mpnet-base-v2` or `bge-base-en-v1.5` once the startup cost is acceptable; retain MiniLM as a fast-path fallback.
- Question-bank expansion to 1000+ items with IRT (Item Response Theory) item-information scoring so we ask the highest-signal questions first.
- Active-learning prompt engine that picks the next question based on max expected information gain per dimension.
- Cross-cultural calibration: regional norm tables so OCEAN scores adjust for country-level mean shifts.
- Relationship-outcome feedback loop: post-date ratings flow back into weight learning.

### Scaling & Infra
- Postgres migration path for SQLite (keep SQLite as the dev default).
- Redis session + rate-limit backend (drop the in-memory slowapi store for production).
- Horizontal scale: split user API, admin API, and WebSocket workers into separate processes behind an ASGI gateway.
- Queue system (Dramatiq/Arq) for embedding compute + photo moderation instead of doing it inline on requests.
- Object storage (S3-compatible) for photos/videos instead of local `uploads/`.

### Trust & Safety
- Perceptual-hash (`phash` + `dhash`) matching against a shared known-abuse image corpus (NCMEC PhotoDNA hook behind a feature flag).
- ML-based selfie liveness check (blink + head turn) in addition to the current still-image selfie verification.
- Harassment pattern detector: sliding-window analysis of message content that escalates auto-mutes when thresholds are hit.
- Mandatory "cooling off" window between reported matches so the reporter never sees the reported user again.

### Social Layer
- Group events with ticketed RSVPs (Stripe Payment Intent integration, optional).
- Shared calendars with ICS subscription URLs per match pair.
- Local-meetup discovery powered by the existing events system with Leaflet heatmap.
- Voice notes in the messaging system (MediaRecorder + Opus encode already present; add server-side transcription for accessibility).

### Privacy / Compliance
- GDPR audit: every PII field tagged in schema, per-table retention policy, scheduled hard-delete for inactive accounts after N months.
- CCPA "do not sell" (trivial — we don't sell — but surface the toggle).
- Right-to-explanation endpoint for each algorithmic decision (match shown, match hidden, suspension).
- Data portability: export in both Kindred JSON and a standards-friendly `schema.org/Person` profile.

## Competitive Research
- **Alovoa (open-source)** — the closest peer; Kindred beats on feature depth and matching sophistication, Alovoa wins on federation and EU-hosting posture. Borrow their public-profile-URL pattern.
- **Duolicious (open-source, 2000 questions)** — question bank is the moat; Kindred should either match the scale or differentiate on quality (IRT weighting).
- **OkCupid (historical)** — the north star UX before Match Group enshittification; keep the "answer more → better matches" loop visible and free.
- **eHarmony** — 32 Dimensions branding reference; Kindred's 8 dimensions are narrower but deeper, document the tradeoff in marketing.
- **Boo (MBTI)** — MBTI approach; Kindred's OCEAN approach has better psychometric validity, but add an opt-in MBTI filter for users who want both.
- **SciMatch (AI-driven)** — AI-photo analysis; Kindred should not copy this (creepy and biased), but the AI-conversation-suggestions feature is a reasonable parallel that Kindred already has.

## Nice-to-Haves
- Federated mode (ActivityPub-style): users on different Kindred instances can match across hosts, encrypted vault stays per-instance.
- End-to-end encrypted DMs (Signal Protocol via libsignal-client bindings) as an opt-in per-match.
- Native mobile apps (Flutter or React Native) sharing the REST API.
- Video dates scheduled via the existing Jitsi integration with automatic ICS invite.
- Matchmaker mode: friends propose matches for each other (OkCupid's old "matchmaker" feature).
- AI-assisted profile coach that critiques your bio for clarity and vulnerability, runs locally via a small model.
- Accessibility sweep: WCAG 2.2 AA audit, screen-reader landmarks on the SPA, keyboard-only navigation, reduced-motion respect.
- Self-hostable Docker Hub image tagged per release for people who want a private Kindred instance for a specific community.

## Open-Source Research (Round 2)

### Related OSS Projects
- https://github.com/Alovoa/alovoa — the most-referenced OSS dating web platform. Spring Boot + Docker Compose, no-paywall charter, F-Droid + Play Store Android client, GDPR-native data export
- https://github.com/angelonazzaro/OpenMeet — student-built FastAPI-ish dating platform with separate mobile client and moderation web app; inclusive-first positioning
- https://github.com/pH7Software/pH7-Social-Dating-CMS — pH7Builder, mature PHP 8 dating CMS with 40+ modules, REST API for native clients, and a hardened pCO8 security framework (SQLi/XSS/CSRF/session-fixation hardening)
- https://github.com/Prakashchandra-007/humbble — Humbble, React Native + Expo open-source Bumble-alike; good mobile-first reference for swipe/match/chat UX
- https://github.com/topics/dating-app — topic hub for adjacent projects worth diffing
- https://github.com/topics/datingapp — alternate spelling — often surfaces projects the other topic misses

### Features to Borrow
- "No paid features, ever" charter (Alovoa) — codify this in CONTRIBUTING.md and README to lock the project against future enshittification
- Docker Compose one-shot deploy with a single `application.properties` (Alovoa) — streamline our self-host story; the Docker Hub item on the roadmap can ship with a reference `docker-compose.yml`
- Separate mobile + moderation surfaces (OpenMeet) — split Kindred into `kindred-server` (FastAPI) + `kindred-web` (SPA) + `kindred-mod` (moderator admin) so trust & safety tooling doesn't bloat the user SPA
- REST API contract for third-party clients (pH7Builder) — publish an OpenAPI spec so hobbyists can build CLI/TUI clients (matches the "privacy-first, no funny business" positioning)
- Hardened security middleware stack (pH7Builder's pCO8) — adopt equivalent FastAPI middleware: rate-limiting, brute-force lockout, CSRF double-submit, content-security-policy nonces, country-block optional
- F-Droid build pipeline (Alovoa Android) — if Kindred ever ships a mobile client, target F-Droid first; free, privacy-aligned user base
- "Open moderation" inclusive charter (OpenMeet) — publish community guidelines and moderation rubric alongside the code, not buried in the app

### Patterns & Architectures Worth Studying
- Matching-engine pluggability (shared across Alovoa/Humbble/pH7) — keep Kindred's 8-dimension engine behind an interface so community forks can swap in alternate rubrics (e.g., Big Five, Enneagram, attachment-style) without forking the whole app
- Data-portability export format — all four projects surface some variant of "download your data"; standardize on a documented JSON schema so users can actually move between instances (and between Kindred and competitors)
- Federation vs centralization tradeoff — none of the four federate. There's a clear opening for an ActivityPub-style profile-portability layer; worth studying before it becomes a v3 migration pain
- Security-middleware composition (pH7's pCO8) — layered defense-in-depth model (input validation → rate limit → auth → CSRF → content-security) is cleaner than ad-hoc decorators and scales to a moderation UI
