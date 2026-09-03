# 5. API Specification & Endpoints

## 5.1 Base URL & Conventions

- **Base Path:** `/api/v1`
- **Authentication Header:** `Authorization: Bearer <access_token>`
- **Response Format:** JSON (`application/json`)
- **Documentation:** `/api/v1/docs` (Swagger UI), `/api/v1/redoc` (ReDoc)

---

## 5.2 API Route Groups

```text
/api/v1/auth             # Registration, login, token refresh, password resets
/api/v1/users            # User retrieval, relationships, follow/unfollow, blocking
/api/v1/profiles         # Current user profile inspection, avatar upload, and updates
/api/v1/interests        # Available master interests taxonomy
/api/v1/communities      # Community creation, covers, settings, join/leave, moderation
/api/v1/posts            # Publishing, retrieving, filtering, updating, media upload, deleting posts
/api/v1/comments         # Post commenting and reply trees
/api/v1/saved-posts      # Bookmarks / saved post collections
/api/v1/feeds            # Home, discover, and short video feeds
/api/v1/search           # Search across users, posts, and communities
/api/v1/recommendations  # Interest-based suggestions
/api/v1/notifications    # Notification management and read states
/api/v1/reports          # User moderation and flagging
/api/v1/chats            # WebSocket endpoints, tickets, presence, and chat history
/api/v1/live-rooms       # Live streaming sessions, tokens, metrics, and webhooks
```

---

## 5.3 Endpoint Directory

### Authentication (`/api/v1/auth`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register/request-otp` | Request 6-digit email registration OTP (7-min TTL, deliverability verified) |
| `POST` | `/api/v1/auth/register/verify-otp` | Verify registration OTP, auto-generate unique username, and create user |
| `POST` | `/api/v1/auth/register` | Direct user registration (legacy) |
| `POST` | `/api/v1/auth/login` | Login and obtain access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh expired access token with token rotation |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token and session |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset OTP via email (7-min TTL) |
| `POST` | `/api/v1/auth/verify-otp` | Verify an email-bound reset OTP and return a reset-only one-time grant (no session tokens) |
| `POST` | `/api/v1/auth/reset-password` | Consume the grant, change the password, and revoke older sessions |
| `POST` | `/api/v1/auth/change-password` | Change password for authenticated user |
| `GET` | `/api/v1/auth/sessions` | List all active signed-in devices and sessions for authenticated user |
| `DELETE` | `/api/v1/auth/sessions/{session_id}` | Revoke a specific active session and blacklist its refresh token |
| `DELETE` | `/api/v1/auth/sessions/other` | Revoke all other active sessions except the current device |

### Users & Profiles (`/api/v1/users`, `/api/v1/profiles`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/users/check-username` | Check real-time username availability (`?username=...`) |
| `GET` | `/api/v1/users/me/privacy` | Get current user's privacy and visibility preferences |
| `PATCH` | `/api/v1/users/me/privacy` | Update privacy settings (`is_private`, `allow_comments`, `allow_mentions`, `show_activity_status`, `search_discoverable`) |
| `POST` | `/api/v1/users/me/deactivate` | Temporarily deactivate account, revoking sessions and hiding profile |
| `DELETE` | `/api/v1/users/me` | Permanently delete user account and cascade dependent records |
| `GET` | `/api/v1/users/{username}` | Get public user profile |
| `GET` | `/api/v1/users/{user_id}/followers` | List user's followers |
| `GET` | `/api/v1/users/{user_id}/following` | List users being followed |
| `POST` | `/api/v1/users/{user_id}/follow` | Follow a user |
| `DELETE` | `/api/v1/users/{user_id}/follow` | Unfollow a user |
| `POST` | `/api/v1/users/{user_id}/block` | Block a user |
| `DELETE` | `/api/v1/users/{user_id}/block` | Unblock a user |

| `GET` | `/api/v1/users/me/blocked` | List users blocked by current user |
| `GET` | `/api/v1/users/{user_id}/relationship` | Check bidirectional follow/block relationship |
| `GET` | `/api/v1/profiles/me` | Get current user's profile |
| `PATCH` | `/api/v1/profiles/me` | Update current user's display name, bio, or username |
| `POST` | `/api/v1/profiles/me/avatar` | Upload and auto-convert user avatar to WebP (max 5MB) |
| `DELETE` | `/api/v1/profiles/me/avatar` | Remove user avatar |
| `PUT` | `/api/v1/profiles/me/interests` | Set selected onboarding interests |

### Interests (`/api/v1/interests`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/interests` | List all available predefined interests |
| `POST` | `/api/v1/interests` | Create new interest (Admin only) |

### Communities (`/api/v1/communities`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/communities` | Create a new community |
| `GET` | `/api/v1/communities` | List/search communities with filters |
| `GET` | `/api/v1/communities/me/joined` | List communities joined by current user |
| `GET` | `/api/v1/communities/{community_id}` | Get community details |
| `PATCH` | `/api/v1/communities/{community_id}` | Update community settings (Owner) |
| `POST` | `/api/v1/communities/{community_id}/cover` | Upload community cover image (max 5MB) |
| `POST` | `/api/v1/communities/{community_id}/join` | Join public community or submit join request |
| `DELETE` | `/api/v1/communities/{community_id}/leave` | Leave a community |
| `GET` | `/api/v1/communities/{community_id}/members` | List community members |
| `DELETE` | `/api/v1/communities/{community_id}/members/{user_id}` | Remove member (Owner) |
| `GET` | `/api/v1/communities/{community_id}/join-requests` | View pending join requests (Owner) |
| `POST` | `/api/v1/communities/{community_id}/join-requests/{request_id}/approve` | Approve join request (Owner) |
| `POST` | `/api/v1/communities/{community_id}/join-requests/{request_id}/reject` | Reject join request (Owner) |

### Posts & Media (`/api/v1/posts`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/posts` | Create text, image carousel, or short video post |
| `POST` | `/api/v1/posts/media` | Upload owner-bound media to the private bucket and return a short-lived signed URL |
| `GET` | `/api/v1/posts` | List and filter posts by author, community, post type, visibility, search |
| `GET` | `/api/v1/posts/{post_id}` | Get single post details with media and author info |
| `PATCH` | `/api/v1/posts/{post_id}` | Update post content or visibility (Author only) |
| `DELETE` | `/api/v1/posts/{post_id}` | Delete post and associated media (Author / Owner / Admin) |
| `POST` | `/api/v1/posts/{post_id}/like` | Like a post |
| `DELETE` | `/api/v1/posts/{post_id}/like` | Remove like from a post |
| `POST` | `/api/v1/posts/{post_id}/save` | Save/bookmark a post |
| `DELETE` | `/api/v1/posts/{post_id}/save` | Remove post from bookmarks |
| `POST` | `/api/v1/posts/{post_id}/share` | Increment share counter and return shareable link |

### Comments (`/api/v1/comments`, `/api/v1/posts/{post_id}/comments`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/posts/{post_id}/comments` | List top-level comments for a post |
| `POST` | `/api/v1/posts/{post_id}/comments` | Post a new comment or reply |
| `GET` | `/api/v1/comments/{comment_id}` | Get single comment details |
| `GET` | `/api/v1/comments/{comment_id}/replies` | List nested replies for a comment |
| `PATCH` | `/api/v1/comments/{comment_id}` | Edit comment (Author only) |
| `DELETE` | `/api/v1/comments/{comment_id}` | Delete comment (Author / Moderator) |

### Saved Posts (`/api/v1/saved-posts`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/saved-posts` | List saved/bookmarked posts for authenticated user |

### Feeds & Discovery (`/api/v1/feeds`, `/api/v1/recommendations`, `/api/v1/search`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/feeds/home` | Personalized home feed (Following + Interested communities) |
| `GET` | `/api/v1/feeds/discover` | Community and post discovery feed |
| `GET` | `/api/v1/feeds/shorts` | Vertical short-form video feed |
| `GET` | `/api/v1/recommendations/communities` | Recommended communities by interests |
| `GET` | `/api/v1/recommendations/users` | Recommended users by shared interests |
| `GET` | `/api/v1/search` | Unified global search across users, communities, posts, and interests |
| `GET` | `/api/v1/search/users` | Search users by username, display name, or bio |
| `GET` | `/api/v1/search/communities` | Search communities by name, slug, or description |
| `GET` | `/api/v1/search/posts` | Search posts by title or text body |
| `GET` | `/api/v1/search/interests` | Search interests taxonomy |
| `POST` | `/api/v1/search/sync` | Full index synchronization to Meilisearch (Admin only) |

#### Search Integration Strategy

- **Users & Interests**: Meilisearch is used directly for typo-tolerant full-text search with block-safety enforced in-memory. Falls back to PostgreSQL `LIKE` queries when Meilisearch is unavailable.
- **Communities & Posts**: Meilisearch is used as a *first-pass candidate filter* (typo-tolerant ranking). A second SQL query re-checks authorization (visibility, privacy, blocks, community membership) on the candidate IDs, ensuring correctness. Falls back to PostgreSQL-only when Meilisearch is unavailable.
- **Write-path sync**: Indexes are updated immediately on entity create/update/delete via `sync_post_search_index`, `sync_community_search_index`, etc. Private community posts and non-public posts are removed from the index on visibility change.
- **Admin re-sync**: `POST /api/v1/search/sync` triggers a full extraction and re-index of all public entities.

#### `PostSearchResult` Response Fields

| Field | Type | Description |
|---|---|---|
| `id` | UUID | Post identifier |
| `title` | string? | Post title |
| `content` | string? | Post body text |
| `post_type` | string | `text` / `image` / `video` |
| `visibility` | string | `public` / `followers_only` / `private` |
| `author_id` | UUID? | Author user identifier |
| `author_username` | string? | Author's username |
| `author_avatar_url` | string? | Raw author profile avatar URL (s3:// path) |
| `community_id` | UUID? | Community identifier (if community post) |
| `community_name` | string? | Community name |
| `like_count` | int | Total likes |
| `comment_count` | int | Total comments |
| `thumbnail_url` | string? | Presigned URL for first media item thumbnail (resolved at index time for image/video posts) |
| `highlight` | object? | Meilisearch `_formatted` snippet dict with `<em>`-tagged matched fragments (keys: `title`, `content`) |
| `created_at` | datetime? | Post creation timestamp |

#### `UserSearchResult` Response Fields

Includes `is_following: bool?` — set when the authenticated user is provided, allowing the client to render follow state in search cards without a separate API round-trip.

Authenticated login/signup user payloads include `is_superuser`. The Flutter
client uses this server-authoritative flag only to expose platform moderation
navigation and the administrator-only `user_suspended` resolution option;
every moderation endpoint still enforces authorization independently.

### Notifications & Reports (`/api/v1/notifications`, `/api/v1/reports`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/notifications` | Paginated user notifications with `unread_only` filter |
| `GET` | `/api/v1/notifications/unread-count` | Get total unread notifications count for badge |
| `GET` | `/api/v1/notifications/preferences` | Retrieve notification delivery and quiet hours preferences |
| `PATCH` | `/api/v1/notifications/preferences` | Update category toggles (`likes`, `comments`, `follows`, `mentions`, `community`, `push`, `email`, `quiet_hours`) |
| `PATCH` | `/api/v1/notifications/{notification_id}/read` | Mark single notification as read |
| `POST` | `/api/v1/notifications/read-all` | Mark all notifications as read |
| `DELETE` | `/api/v1/notifications/{notification_id}` | Delete notification from user history |

| `GET` | `/api/v1/notifications/stream` | Server-Sent Events (SSE) stream powered by Redis Streams |
| `WS` | `/api/v1/notifications/ws` | Real-time WebSocket connection for live notifications |
| `POST` | `/api/v1/notifications/ws-ticket` | Issue a short-lived, single-use notification WebSocket ticket |
| `POST` | `/api/v1/notifications/typing` | Broadcast typing status via Redis Pub/Sub |
| `POST` | `/api/v1/reports` | Submit report against user, post, comment, community, or chat |
| `GET` | `/api/v1/reports` | List reports with status, type, and community filters (Admin/Owner) |
| `GET` | `/api/v1/reports/{report_id}` | Get report details (Admin or Community Owner) |
| `PATCH` | `/api/v1/reports/{report_id}/status` | Update report status (`PENDING` -> `REVIEWING` -> `RESOLVED`/`REJECTED`) |

### Real-Time Chat & Live Rooms (`/api/v1/chats`, `/api/v1/live-rooms`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/chats/ws-ticket` | Issue short-lived, single-use ticket for WebSocket authentication |
| `WS` | `/api/v1/chats/ws/{community_id}` | WebSocket connection for community group chat |
| `GET` | `/api/v1/chats/{community_id}/messages` | Fetch paginated chat message history |
| `GET` | `/api/v1/chats/{community_id}/presence` | Fetch online active participants in community chat |
| `POST` | `/api/v1/live-rooms` | Create live stream room session (Owner) |
| `GET` | `/api/v1/live-rooms` | List active live stream rooms |
| `GET` | `/api/v1/live-rooms/{room_id}` | Get live room details |
| `POST` | `/api/v1/live-rooms/{room_id}/start` | Start live streaming session |
| `POST` | `/api/v1/live-rooms/{room_id}/token` | Obtain streaming participant/viewer token (LiveKit) |
| `POST` | `/api/v1/live-rooms/{room_id}/end` | End live streaming room session |
| `GET` | `/api/v1/live-rooms/{room_id}/metrics` | Get live viewer analytics and stream metrics |
| `POST` | `/api/v1/live-rooms/webhooks/livekit` | Webhook receiver for LiveKit media server lifecycle events |
| `POST` | `/api/v1/live-rooms/{room_id}/reconcile` | Synchronize Redis viewer count with LiveKit server (Admin) |
