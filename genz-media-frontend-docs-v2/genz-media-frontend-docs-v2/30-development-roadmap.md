# 30 — Frontend Development Roadmap

This order follows backend priorities while building shared mobile foundations first.

## Phase 0 — Foundation

1. Project shell
2. Theme/design tokens
3. Router
4. Dio/API client
5. Secure storage
6. Auth state/refresh
7. reusable loading/error components

## Phase 1 — P0 core

8. Register/Login/Reset
9. Interest onboarding
10. My Profile/Edit
11. Public Profile
12. Follow/Unfollow/Block
13. Community detail/membership
14. Create/Edit community
15. Text/Image/Short post creation
16. Post Detail
17. Like
18. Comments/Replies

## Phase 2 — P1 discovery/engagement

19. Save/Saved Posts after endpoint verification
20. Share after contract verification
21. Home Feed
22. Discover Feed
23. Recommendations
24. Shorts Feed polish
25. Search
26. Notifications
27. Report submission

## Phase 3 — Moderation

28. Community owner reports
29. Admin report workflow if consumer app should support it

## Phase 4 — P2 implemented backend integrations

30. Community Chat
31. Live Room

## Final polish

32. accessibility
33. reconnect behavior
34. feed/video performance
35. empty/error states
36. analytics/performance instrumentation
37. integration tests

## Important

Chat/Live are documented as backend-implemented, but they remain later frontend work because they depend on stable:
- auth;
- communities;
- real-time lifecycle;
- media/provider integration.
