# 10 — Shorts Feed

## Backend

`GET /api/v1/feeds/shorts`

Ranking inputs include:
- interests;
- likes;
- saves;
- recency.

## Layout

```text
┌────────────────────────────┐
│                            │
│         VIDEO              │
│                            │
│                    Avatar  │
│                    Like    │
│                    Comment │
│                    Save    │
│                    Share   │
│                            │
│ @creator  [Follow]         │
│ Community / interest       │
│ Caption                    │
│                            │
│ Bottom navigation          │
└────────────────────────────┘
```

## Paging

One video per page, vertical snapping.

Resource model:

```text
Current  → active
Next     → preload
Previous → optional short cache
Distant  → release
```

## Controls

Permanent high-frequency rail:
1. creator/avatar entry
2. Like
3. Comments
4. Save
5. Share

Overflow:
- Report
- Block user where relevant
- Delete if authorized

## Gestures

- vertical swipe → next/previous;
- single tap → play/pause;
- optional double tap → Like.

Gestures do not replace visible controls.

## Audio

Keep a visible mute/audio affordance.

## Comments

Open as a draggable bottom sheet so the video context remains visible.

## Community context

If the short belongs to a community, make that community tappable and visible.

## Low-chrome enhancement

A clear-screen/reduced-overlay mode can be future polish, not a requirement for first implementation.

## Performance metrics to watch

- time to first frame;
- start failures;
- rebuffering;
- early swipe-away;
- completion;
- follow after view;
- community open/join after view.
