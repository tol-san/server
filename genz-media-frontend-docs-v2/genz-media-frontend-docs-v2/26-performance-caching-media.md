# 26 — Performance, Caching & Media

## Backend caching already exists

Backend docs describe Redis cache for:
- Discover Feed;
- Shorts Feed;
- Home Feed;
- Recommendations;
- counters;
- unread notification count;
- popular search.

Flutter should not try to reproduce backend ranking/cache behavior.

## Client cache goals

Use cache to improve perceived speed, not redefine correctness.

Good candidates:
- images;
- avatars;
- community covers;
- recently viewed feed data;
- interest taxonomy;
- non-sensitive lightweight preferences.

## Home / Discover

- paginate;
- lazy-render;
- retain loaded content on refresh;
- prevent duplicate page requests.

## Shorts

```text
Current video → active decode
Next → preload
Previous → short retention
Distant → release
```

Avoid preparing many videos simultaneously.

## Search

Debounce user typing before network calls.
Do not cache results so aggressively that updated visibility/blocking becomes stale for long periods.

## Notifications

Unread count should reconcile with backend, not rely only on local increments.

## Chat

Do not locally cache message history as source of truth.
Backend says PostgreSQL stores history; Redis is for transient real-time signals.

## Media storage

Backend stores media externally and PostgreSQL stores metadata/URLs.

Flutter should:
- use loading placeholder;
- handle failure fallback;
- avoid downloading full-resolution media when not needed;
- display upload progress;
- separate upload from publish.

## Performance instrumentation targets

- app startup;
- feed time-to-content;
- image failure;
- search latency;
- Shorts time-to-first-frame;
- rebuffer ratio;
- upload failure;
- chat send-to-confirm;
- socket reconnect;
- live join time.
