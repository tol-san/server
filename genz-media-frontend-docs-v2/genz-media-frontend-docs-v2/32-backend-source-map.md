# 32 — Backend Source Map

This frontend documentation was rebuilt from the latest backend `docs.zip`.

## `docs/01-overview.md`

Frontend uses it for:
- project idea;
- target users;
- unique value proposition;
- recommendation concept;
- core user journey;
- final MVP scope.

## `docs/02-architecture-and-tech-stack.md`

Frontend uses it for:
- backend infrastructure boundaries;
- Redis Streams / Pub/Sub distinctions;
- SSE and WebSocket availability;
- Meilisearch;
- external media storage;
- chat advanced reliability;
- LiveKit room lifecycle;
- viewer count semantics;
- outbox/event behavior.

Flutter must not reproduce backend cache/event infrastructure.

## `docs/03-features-and-requirements.md`

Primary product requirements:
- auth;
- profile;
- follow;
- interests;
- communities;
- content;
- engagement;
- feeds;
- search;
- chat;
- live;
- notifications;
- moderation;
- P0/P1/P2;
- excluded features;
- backend rules.

## `docs/04-database-design.md`

Frontend uses indirectly for:
- understanding entity relationships;
- uniqueness semantics;
- avoiding duplicate client actions;
- notification/report/chat/live domain relationships.

Flutter should not couple UI directly to DB schema.

## `docs/05-api-specification.md`

Primary endpoint directory.

Use this only as documentation; running OpenAPI is final authority.

## `docs/06-roadmap.md`

Used for:
- implementation dependency order;
- frontend sequencing.

## 2026 UI/UX research

Used only for:
- simple TikTok/Instagram-inspired interaction language;
- five-tab navigation;
- content-dominant visual direction;
- Shorts treatment;
- community-visible differentiation;
- accessibility;
- low-chrome video principles.

Where research assumptions conflict with the latest backend docs, the latest backend capability wins.
