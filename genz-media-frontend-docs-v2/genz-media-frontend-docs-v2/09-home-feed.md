# 09 — Home Feed

## Backend definition

Home includes posts from:
- followed users;
- joined communities;
- interest matches;

ranked by recency and relevance.

Endpoint:
`GET /api/v1/feeds/home`

## UI character

Home should feel like a clean social feed, not a second TikTok screen.

## Post hierarchy

```text
Avatar + name + username
Community identity if applicable
Timestamp / supported context

Text / title / caption
Media

Like · Comment · Save · Share
Counts
```

## Recommendation context

Do not fabricate explanation text such as:

> Because you like Technology

unless backend response supplies it.

## Short-video posts in Home

Use a portrait preview/player treatment without turning the whole Home feed into autoplay full-screen video.

Tapping may open the corresponding short in Shorts if the app can preserve a supported item context.

## Feed state

Required:
- initial skeleton;
- success;
- empty;
- transient error;
- refresh;
- pagination.

## Empty state

Suggested:

> Your feed is just getting started. Follow people or join communities.

## Interaction updates

Like/save/follow/join updates should reconcile with backend response.

Optimistic mutation is allowed only when rollback behavior is reliable.
