# 03 — Frontend Product Decisions

These are frontend design decisions derived from the 2026 research while staying inside the latest backend capability.

## 1. Do not clone TikTok or Instagram

Use familiar interaction patterns, not their identity.

GenZ Media should be:
- simpler than Instagram;
- more socially/community structured than TikTok;
- interest-first rather than creator-only;
- content-dominant rather than chrome-heavy.

## 2. Five primary destinations

```text
Home · Shorts · Create · Discover · Profile
```

### Why
- Home = mixed social/community feed
- Shorts = first-class video surface
- Create = central contribution action
- Discover = recommendation + real Search
- Profile = identity/account

## 3. Notifications are contextual, not a bottom tab

Use a **bell in the top app bar** with unread badge.

Reason:
- notifications are important;
- they do not need to replace one of the five core destinations.

## 4. Search is now active

The latest backend documentation includes:
- unified search;
- users search;
- communities search;
- posts search;
- interests search.

Therefore Discover should now include a real Search entry.

## 5. Chat and Live are community features

Enter them from Community Detail.

Do not add global `Chat` or `Live` bottom tabs for the current product.

## 6. Reports live in overflow menus

Examples:
- post → Report;
- comment → Report if backend UI contract supports target type;
- user → Report;
- community → Report;
- chat message → Report.

## 7. Visual language

```text
Immersive content → dark when appropriate
Social/community → clean neutral surfaces
Brand accent → violet
Interests → visible identity
Communities → visible destination
```

## 8. Shorts interaction

- one video per page;
- edge-to-edge media;
- minimal right action rail;
- creator/community entry visible;
- captions visible;
- tap play/pause;
- visible mute/audio control;
- swipe vertical;
- gestures never replace visible controls.

## 9. Creation

MVP creation is selection + preview + metadata + upload + publish.

Do not implement a TikTok editor.

## 10. Algorithm controls

Do not expose "more/less of this topic", "not interested", or recommendation tuning unless the backend exposes matching feedback APIs.

## 11. Product success

Do not optimize only for watch time.

Key loop:

```text
Watch
→ Open profile/community
→ Follow/Join
→ Comment/Create
→ Return
```
