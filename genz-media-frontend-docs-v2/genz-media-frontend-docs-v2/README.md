# GenZ Media — Flutter Frontend Documentation v2

**Basis:** rebuilt from the latest backend documentation in `docs.zip` plus the approved 2026 UI/UX direction.

This documentation replaces the earlier frontend split.

## Product direction

GenZ Media is an **interest-first social community platform** with short video as a first-class discovery surface.

```text
Interest
   ↓
Discover content / people / communities
   ↓
Follow / Join
   ↓
Consume / Create
   ↓
Like / Comment / Save / Share
   ↓
Chat / Live / Return
```

The frontend should feel:
- simple like modern TikTok / Instagram;
- content-dominant;
- low-chrome;
- community-aware;
- fast and predictable;
- visually consistent across normal feed, Shorts, community, chat, and live experiences.

## Primary mobile navigation

```text
Home · Shorts · Create · Discover · Profile
```

Additional high-value features are reached contextually:
- **Search** → inside Discover;
- **Notifications** → bell in top app bar;
- **Community Chat** → Community Detail;
- **Live Room** → Community Detail;
- **Reports** → overflow menus;
- **Moderation** → owner/admin management surfaces.

## Source-of-truth order

When documents conflict:

1. Running backend/OpenAPI at `/api/v1/openapi.json`
2. Latest backend implementation
3. Backend `docs/05-api-specification.md`
4. Backend `docs/03-features-and-requirements.md`
5. Backend `docs/02-architecture-and-tech-stack.md`
6. These frontend UX specifications

Never invent an endpoint, HTTP method, request field, response field, permission, or enum.

## Documentation index

| File | Purpose |
|---|---|
| `00-agent-sitemap.md` | Which docs an agent should read for each task |
| `01-product-foundation.md` | Product idea, value proposition, user journey |
| `02-backend-scope-priority.md` | P0/P1/P2 scope and exclusions |
| `03-frontend-product-decisions.md` | Combined 2026 UX decisions |
| `04-design-system.md` | Visual tokens and reusable components |
| `05-information-architecture.md` | Product hierarchy |
| `06-navigation.md` | Bottom navigation and contextual entry points |
| `07-screen-inventory.md` | Complete screen/view map |
| `08-auth-onboarding.md` | Auth, session, interest onboarding |
| `09-home-feed.md` | Home experience |
| `10-shorts-feed.md` | Vertical short-video experience |
| `11-discover-search.md` | Discover + Meilisearch-backed search UX |
| `12-profile-follow-block.md` | User profiles and relationships |
| `13-communities-membership.md` | Community lifecycle and owner UX |
| `14-create-post-media.md` | Text/image/video creation |
| `15-post-comments-engagement.md` | Post details, comments, likes |
| `16-saved-share-report.md` | Saved posts, share, report UX |
| `17-notifications.md` | Notification center and real-time delivery |
| `18-moderation.md` | Owner/admin report review UX |
| `19-community-chat.md` | WebSocket community chat |
| `20-live-rooms.md` | Live room lifecycle and viewer/host UX |
| `21-api-contract-map.md` | Backend route map for Flutter |
| `22-contract-gaps-openapi-checks.md` | Documentation inconsistencies to verify |
| `23-ui-state-error-loading.md` | Standard API/UI state behavior |
| `24-realtime-client-architecture.md` | SSE/WebSocket lifecycle rules |
| `25-flutter-architecture.md` | Recommended feature-first app architecture |
| `26-performance-caching-media.md` | Feed/video/media performance |
| `27-security-accessibility.md` | Mobile security + accessibility |
| `28-user-flows.md` | Cross-feature flows |
| `29-testing-definition-of-done.md` | Acceptance and test requirements |
| `30-development-roadmap.md` | Suggested frontend implementation order |
| `31-agent-rules.md` | Hard rules for coding agents |
| `32-backend-source-map.md` | Backend document → frontend concern mapping |
