# 11 — Discover & Search

## Discover purpose

Answer:
1. What should I watch/read?
2. Who should I follow?
3. Which community should I join?
4. What can I find directly?

## Backend

- `GET /api/v1/feeds/discover`
- `GET /api/v1/recommendations/users`
- `GET /api/v1/recommendations/communities`

## Suggested Discover hierarchy

```text
Discover
[ Search ]

Interest chips

Recommended posts
[content]

Communities for you
[horizontal cards]

People you may like
[horizontal cards]

Trending / more content
```

## Search is a real feature

Backend docs define Meilisearch-backed typo-tolerant search with PostgreSQL fallback.

### Unified
`GET /api/v1/search`

Across:
- users;
- communities;
- posts;
- interests.

### Domain routes
- `GET /api/v1/search/users`
- `GET /api/v1/search/communities`
- `GET /api/v1/search/posts`
- `GET /api/v1/search/interests`

## Search UX

```text
Search field
   ↓
Debounced query
   ↓
Loading
   ↓
Results
```

Use result categories/tabs only when supported by the API response/route strategy.

## User results
May match:
- display name;
- username;
- bio.

## Community results
May match:
- name;
- slug;
- description.

Backend applies accessibility filtering.

## Post results
May match:
- title;
- content.

Backend applies:
- visibility;
- blocking rules.

## Interest results
May match master taxonomy fields.

## No results

Suggested:

> No results for “query”.

Offer:
- clear query;
- switch category;
- browse recommendations.

## Search failure

Because backend documents PostgreSQL fallback, Flutter should treat backend response as authoritative and should not implement its own separate local search engine.

## Admin sync

`POST /api/v1/search/sync` is admin-only and should not appear in normal consumer UI.
