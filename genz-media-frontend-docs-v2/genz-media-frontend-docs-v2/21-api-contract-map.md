# 21 — API Contract Map

**Base:** `/api/v1`  
**Auth:** `Authorization: Bearer <access_token>`

Use running OpenAPI as final authority.

## Authentication

| Method | Path | Frontend use |
|---|---|---|
| POST | `/auth/register` | Register |
| POST | `/auth/login` | Login |
| POST | `/auth/refresh` | Refresh access |
| POST | `/auth/logout` | Revoke session |
| POST | `/auth/forgot-password` | Start reset |
| POST | `/auth/reset-password` | Reset |
| POST | `/auth/change-password` | Change password |

## Users / Profiles

| Method | Path |
|---|---|
| GET | `/users/{username}` |
| GET | `/users/{user_id}/followers` |
| GET | `/users/{user_id}/following` |
| POST | `/users/{user_id}/follow` |
| DELETE | `/users/{user_id}/follow` |
| POST | `/users/{user_id}/block` |
| DELETE | `/users/{user_id}/block` |
| GET | `/profiles/me` |
| PATCH | `/profiles/me` |
| PUT | `/profiles/me/interests` |

## Interests

| Method | Path |
|---|---|
| GET | `/interests` |
| POST | `/interests` — Admin |

## Communities

| Method | Path |
|---|---|
| POST | `/communities` |
| GET | `/communities/{community_id}` |
| PATCH | `/communities/{community_id}` |
| POST | `/communities/{community_id}/join` |
| DELETE | `/communities/{community_id}/leave` |
| GET | `/communities/{community_id}/members` |
| DELETE | `/communities/{community_id}/members/{user_id}` |
| GET | `/communities/{community_id}/join-requests` |
| POST | `/communities/{community_id}/join-requests/{request_id}/approve` |
| POST | `/communities/{community_id}/join-requests/{request_id}/reject` |

## Posts

| Method | Path |
|---|---|
| POST | `/posts` |
| GET | `/posts/{post_id}` |
| DELETE | `/posts/{post_id}` |
| POST | `/posts/{post_id}/like` |
| DELETE | `/posts/{post_id}/like` |
| POST | `/posts/{post_id}/save` |
| DELETE | `/posts/{post_id}/save` |

## Comments

| Method | Path |
|---|---|
| GET | `/posts/{post_id}/comments` |
| POST | `/posts/{post_id}/comments` |
| PATCH | `/comments/{comment_id}` |
| DELETE | `/comments/{comment_id}` |

## Feeds / Recommendations

| Method | Path |
|---|---|
| GET | `/feeds/home` |
| GET | `/feeds/discover` |
| GET | `/feeds/shorts` |
| GET | `/recommendations/communities` |
| GET | `/recommendations/users` |

## Search

| Method | Path |
|---|---|
| GET | `/search` |
| GET | `/search/users` |
| GET | `/search/communities` |
| GET | `/search/posts` |
| GET | `/search/interests` |
| POST | `/search/sync` — Admin |

## Notifications

| Method | Path |
|---|---|
| GET | `/notifications` |
| GET | `/notifications/unread-count` |
| PATCH | `/notifications/{notification_id}/read` |
| POST | `/notifications/read-all` |
| DELETE | `/notifications/{notification_id}` |
| GET | `/notifications/stream` — SSE |
| WS | `/notifications/ws` |
| POST | `/notifications/typing` |

## Reports

| Method | Path |
|---|---|
| POST | `/reports` |
| GET | `/reports` |
| GET | `/reports/{report_id}` |
| PATCH | `/reports/{report_id}/status` |

## Chat

| Method | Path |
|---|---|
| WS | `/chats/ws/{community_id}` |
| GET | `/chats/{community_id}/messages` |

## Live Rooms

| Method | Path |
|---|---|
| POST | `/live-rooms` |
| POST | `/live-rooms/{room_id}/token` |
| POST | `/live-rooms/{room_id}/end` |

## Strict rule

This table mirrors the backend endpoint directory only.

Additional architecture routes must be verified in OpenAPI before use.
