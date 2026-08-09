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
- v2.5.1 — Comprehensive audit: 41 bug fixes
- v2.5.0 — Phase 8: Premium & integrations
- v2.4.0 — Phase 7: Admin & operations
- Kindred v2.3.0 Phase 6 - Message UX, profile tools, and accessibility
- Kindred v2.2.0 Phase 5 - Safety, discovery, and real-time notifications
- Kindred v2.1.0 Phase 4 - Admin infrastructure, moderation, and analytics
- Kindred v2.0.0 Phase 3 - Social, communication, and progressive profiles
- Kindred v1.9.0 Phase 2 - Mobile UX, engagement, and interaction polish
- Kindred v1.8.0 Phase 1 - UX polish, admin tools, structured backend
