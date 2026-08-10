# Changelog

All notable changes to kindred will be documented in this file.

## [v2.5.2] - 2026-08-03

- Added: Add production deployment guide and config files
- Added: Configurable MPNet semantic embeddings with automatic MiniLM fallback and mixed-dimension migration safety
- Added: Adaptive 2PL IRT question selection over a 1,015-item Big Five bank with incremental SPA batches
- Added: Dimension-aware active-learning questionnaire endpoint for next-prompt selection
- Added: Cohort-backed country calibration with raw-score retention and private country fields
- Added: Private post-date feedback learning with persisted weight events and manual-weight blending
- Added: Safe SQLite-to-PostgreSQL migration utility with schema, data, and row-count verification
- Added: Optional Redis-backed rate limits and refresh sessions with fail-closed production mode
- Added: Separate user API, admin API, and WebSocket worker processes behind the Caddy gateway with Redis pub/sub presence
- Added: Dramatiq Redis workers for asynchronous profile embeddings and photo-moderation queue submission with local inline fallback
- Added: Optional S3-compatible object storage for all media uploads with private `/uploads/` delivery, video range support, legacy local-file reads, and fail-closed production configuration
- Added: Upload-time pHash/dHash screening against an operator-managed abuse-hash corpus with admin safety events and an opt-in external hash hook
- Added: Local MediaPipe selfie liveness using ordered blink and head-turn evidence, with sequence capture, pinned model validation, and admin review metadata
- Added: Explainable sliding-window harassment detection for direct messages with escalating warnings, recipient-side auto-mutes, WebSocket enforcement, and admin review data
- Added: Report-triggered cooling-off exclusions across profile discovery, matching, suggestions, and pair compatibility surfaces
- Added: Optional ticketed event RSVPs with Stripe PaymentIntents, payment-hold capacity accounting, and signed webhook confirmation
- Added: Shared match calendar subscriptions with hashed bearer URLs, revocation, cancellation-aware ICS feeds, and participant-only exports
- Added: Local meetup discovery with opt-in event coordinates, radius-filtered nearby events, and a Leaflet heatmap
- Added: Server-side voice transcription with durable status, queue processing, and accessible transcript disclosure
- Added: Schema-wide privacy field tags, per-table retention policies, and leased inactive-account hard deletion
- Added: Default-on CCPA do-not-sell preference with authenticated API and profile settings control
- Added: Right-to-explanation endpoints for match visibility, score dimensions, and suspension appeals
- Added: Versioned Kindred data exports and downloadable schema.org/Person JSON-LD profiles
- Added: Opt-in ActivityPub-style federation with WebFinger actors, Ed25519-signed delivery, and cross-instance match offers that keep private vault data local
- Added: Optional React Native/Expo mobile client for iOS and Android sharing REST authentication, discovery, matches, and messaging
- Added: Optional Jitsi rooms for scheduled dates with participant-only REQUEST calendar invites and notifications
- Added: Consent-based matchmaker proposals that let accepted friends suggest profiles before the recipient sends a like
- Added: Private local profile coach with explainable clarity, specificity, warmth, and vulnerability feedback
- v2.5.1 — Comprehensive audit: 41 bug fixes
- v2.5.0 — Phase 8: Premium & integrations
- v2.4.0 — Phase 7: Admin & operations
- Kindred v2.3.0 Phase 6 - Message UX, profile tools, and accessibility
- Kindred v2.2.0 Phase 5 - Safety, discovery, and real-time notifications
- Kindred v2.1.0 Phase 4 - Admin infrastructure, moderation, and analytics
- Kindred v2.0.0 Phase 3 - Social, communication, and progressive profiles
- Kindred v1.9.0 Phase 2 - Mobile UX, engagement, and interaction polish
- Kindred v1.8.0 Phase 1 - UX polish, admin tools, structured backend

## Roadmap archive — 2026-08-10 — ROADMAP.md

<details>
<summary>Original roadmap snapshot</summary>

```markdown
# Kindred Roadmap

Forward-looking scope for the compatibility-first dating + social platform (FastAPI + vanilla JS SPA + SQLite, 8-dimension matching engine).

## Planned Features

### Matching Engine

### Scaling & Infra

### Trust & Safety

### Social Layer

### Privacy / Compliance

## Competitive Research
- **Alovoa (open-source)** — the closest peer; Kindred beats on feature depth and matching sophistication, Alovoa wins on federation and EU-hosting posture. Borrow their public-profile-URL pattern.
- **Duolicious (open-source, 2000 questions)** — question bank is the moat; Kindred should either match the scale or differentiate on quality (IRT weighting).
- **OkCupid (historical)** — the north star UX before Match Group enshittification; keep the "answer more → better matches" loop visible and free.
- **eHarmony** — 32 Dimensions branding reference; Kindred's 8 dimensions are narrower but deeper, document the tradeoff in marketing.
- **Boo (MBTI)** — MBTI approach; Kindred's OCEAN approach has better psychometric validity, but add an opt-in MBTI filter for users who want both.
- **SciMatch (AI-driven)** — AI-photo analysis; Kindred should not copy this (creepy and biased), but the AI-conversation-suggestions feature is a reasonable parallel that Kindred already has.

## Nice-to-Haves
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
```

</details>
