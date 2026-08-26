# 3. Features & Requirements

## 3.1 MVP Features

### 3.1.1 Authentication
The authentication system supports:
- Register
- Login
- Logout
- Email verification
- Forgot Password & Reset Password
- JWT Access Token & Refresh Token
- Change Password

Authentication uses JWT-based access and refresh tokens.

---

### 3.1.2 User Profile
Users can:
- View user profiles
- Edit profile details (display name, bio, avatar)
- Upload avatar image
- Select and update interests
- View user's own posts
- View followers and following lists
- Follow or unfollow other users
- Block or unblock other users

Profile fields include:
- `username`, `display_name`, `bio`, `avatar_url`
- Selected interests
- Counters: `follower_count`, `following_count`, `post_count`

---

### 3.1.3 Follow System
The platform uses a **directional Follow System** instead of mutual friend requests:
- User A follows User B without requiring approval from User B.
- If both follow each other, they remain two distinct directional relationships.
- Simple, scalable database model and API.

Users can:
- Follow / unfollow another user
- View followers / following lists
- Check follow status
- Receive follow notifications

---

### 3.1.4 Interests
Predefined interests managed by System Admins (e.g. Technology, Programming, Gaming, Music, Sports, Movies, Art, Photography, Travel).

Users can:
- Select interests during onboarding
- Add or remove interests at any time
- Receive content, community, and user recommendations based on shared interests

---

### 3.1.5 Community
Users can create and join communities.

**Community Types:**
| Type | Joining Method |
| --- | --- |
| Public | Users can join immediately |
| Private | Users must submit a join request and wait for Community Owner approval |

**Community Roles:**
| Role | Permissions |
| --- | --- |
| Owner | Manage community info, cover image, approve/reject join requests, remove members, delete community posts/chat messages, start/end Live Rooms |
| Member | View and create content inside the community, participate in community group chat |

---

### 3.1.6 Content (Posts)
Supports three primary content types:

1. **Text Post:** Title, content, visibility, optional community ID.
2. **Image Post:** Caption, one or more image URLs, visibility, optional community ID.
3. **Short Video Post:** Caption, video URL, thumbnail URL, duration, visibility, optional community ID.

**Ownership rule:**
A post belongs either to a user's personal profile (`community_id = null`) or to a specific community (`community_id = <ID>`).

---

### 3.1.7 Engagement
Users can interact with content:
- **Like / Unlike:** Enforces unique constraint per user and post (`UNIQUE(user_id, post_id)`).
- **Comment / Reply:** Create comments, reply to comments, edit/delete own comments.
- **Save / Unsave:** Private saved post list per user.
- **Share:** Generate shareable link and increment share counter.
- **Report:** Report inappropriate content, comments, or users.

---

### 3.1.8 Feeds
Three primary feed streams:
1. **Home Feed:** Posts from followed users, joined communities, and interest matches ranked by recency and relevance.
2. **Discover Feed:** Community recommendations, similar users, popular trending posts.
3. **Short Video Feed:** Dedicated vertical video feed scored by interests, likes, saves, and recency.

---

### 3.1.9 Search Engine
Blazing fast, typo-tolerant full-text search powered by **Meilisearch** with automatic index synchronization and resilient PostgreSQL `ILIKE` fallback:
- **Unified & Domain Search (`/api/v1/search`)**: Query across all domains simultaneously or filter specifically by `users`, `communities`, `posts`, or `interests`.
- **Users**: Search by display name, username, and bio.
- **Communities**: Search by name, slug, and description (filtered by accessibility).
- **Posts**: Search by title and content (filtered by visibility and blocking rules).
- **Interests**: Search master taxonomy by category name, slug, and description.
- **Index Synchronization**: Automated background document indexing on creation, update, and deletion hooks, with admin-triggered full database resync (`POST /api/v1/search/sync`).
- **Resilience**: Automatic fallback to PostgreSQL queries if the search engine is unavailable.

---

### 3.1.10 Community Group Chat
Real-time messaging via **FastAPI WebSockets**:
- Active community members can join the chat room
- Send text messages & view message history
- Delete own messages; Community Owners can moderate/delete any message
- Display online user count
- Non-members / removed members lose WebSocket access immediately

*Phase 2 additions:* Voice/video messages, reactions, read receipts, typing indicators.

---

### 3.1.11 Live Room
FastAPI manages business logic and access control while external services (LiveKit, Agora) handle video streaming:
- Create live room & generate access tokens
- Start / join / leave / end live sessions
- Link Live Room to community and verify host/member permissions
- Track viewer count and live text comments

*Note:* Stretch goal for Phase 1. Core API must be completed first.

---

### 3.1.12 Notifications Engine
Event-driven in-app notifications system powered by PostgreSQL persistence, **Redis Streams** for durable event processing, and multi-channel real-time streaming:
- **Event Triggers**:
  - `new_follower`: When a user is followed.
  - `post_like`: When a user's post is liked.
  - `post_comment` & `comment_reply`: When a post is commented on or a comment receives a reply.
  - `community_join_approved`: When a private community join request is approved.
- **Delivery Channels**:
  - **REST API (`/api/v1/notifications`)**: Paginated list, unread count badge query, mark individual/all as read, delete notification.
  - **Server-Sent Events (SSE) (`/api/v1/notifications/stream`)**: Real-time push streaming from Redis Streams.
  - **WebSocket (`/api/v1/notifications/ws`)**: Interactive bidirectional socket for instant notifications.
  - **Ephemeral Signals (Redis Pub/Sub)**: Fire-and-forget real-time signals such as typing indicators (`"User A is typing..."` at `/api/v1/notifications/typing`).

---

### 3.1.13 Report & Moderation Workflow
Multi-entity reporting and stateful moderation lifecycle:
- **Reportable Entities**: Users, Posts, Comments, Communities, and Chat Messages.
- **Reasons**: `spam`, `harassment`, `inappropriate_content`, `hate_speech`, `violence`, `copyright`, `other`.
- **Moderation Workflow States**:
  `PENDING` → `REVIEWING` → `RESOLVED` / `REJECTED`
- **Resolution Actions**:
  `none`, `content_deleted`, `user_warned`, `user_suspended`, `community_closed`, `dismissed`.
- **Role-Based Access Control (RBAC)**:
  - **System Admin**: Platform-wide moderation, review global reports, suspend/deactivate user accounts, close communities.
  - **Community Owner**: Community-scoped moderation for reports on content within their owned communities.

---

## 3.2 Feature Priority

| Priority | Features |
| --- | --- |
| **P0 — Required** | Authentication, Profile, Interests, Follow, Community, Text/Image/Video Posts, Like, Comment |
| **P1 — Important** | Save, Share, Report, Search, Feed, Rule-Based Recommendations, Notifications |
| **P2 — Stretch Goal** | Community Group Chat (WebSocket), External Live Room Integration |

---

## 3.3 Features Excluded from MVP

To ensure delivery within a 1–2 month development window by a single backend engineer, the following are out of MVP scope:

- Friend Request system (replaced with Follow model)
- Stories / Disappearing status
- Direct 1-on-1 Messages (DMs)
- 1-on-1 Video Calls
- Machine Learning / AI recommendation models
- Payment / Monetization / Ad network
- Automatic AI content moderation
- Built-in video transcode/editor pipeline
- Microservices deployment

---

## 3.4 Core Backend Rules

### Follow
- A user cannot follow themselves.
- A user cannot create duplicate follow records.
- Following is immediate and does not require approval.
- Unfollowing immediately removes the relationship record.

### Community
- Community Owner is automatically a member.
- A user cannot join the same community twice.
- Private communities require join request approval by Owner.
- Public communities can be joined instantly.
- Only the Owner can manage community settings and member approvals.

### Posts
- Personal posts have `community_id = null`.
- Community posts require a valid `community_id`.
- User must be a member of the community to create a community post.

### Comments
- Users can only edit and delete their own comments.
- Community Owners can moderate comments on posts within their community.
- System Admins can moderate comments platform-wide.

### Group Chat
- Only verified community members can connect to the chat room WebSocket.
- Leaving/removal from community terminates chat authorization immediately.

### Blocking
- If User A blocks User B:
  - User B cannot follow User A.
  - User B cannot interact with User A's content.
  - Any existing follow relationships between them are severed immediately.
