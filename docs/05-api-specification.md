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
/api/v1/profiles         # Current user profile inspection and updates
/api/v1/interests        # Available master interests taxonomy
/api/v1/communities      # Community creation, settings, join/leave, moderation
/api/v1/posts            # Publishing, retrieving, updating, deleting posts
/api/v1/comments         # Post commenting and reply trees
/api/v1/reactions        # Likes and reactions
/api/v1/saved-posts      # Bookmarks / saved post collections
/api/v1/feeds            # Home, discover, and short video feeds
/api/v1/search           # Search across users, posts, and communities
/api/v1/recommendations  # Interest-based suggestions
/api/v1/notifications    # Notification management and read states
/api/v1/reports          # User moderation and flagging
/api/v1/chats            # WebSocket endpoints and chat history
/api/v1/live-rooms       # Live streaming sessions and access tokens
```

---

## 5.3 Endpoint Directory

### Authentication (`/api/v1/auth`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Register new user account |
| `POST` | `/api/v1/auth/login` | Login and obtain access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh expired access token |
| `POST` | `/api/v1/auth/logout` | Revoke active refresh token |
| `POST` | `/api/v1/auth/forgot-password` | Request password reset token via email |
| `POST` | `/api/v1/auth/reset-password` | Reset password using verified token |
| `POST` | `/api/v1/auth/change-password` | Change password for authenticated user |

### Users & Profiles (`/api/v1/users`, `/api/v1/profiles`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/users/{username}` | Get public user profile |
| `GET` | `/api/v1/users/{user_id}/followers` | List user's followers |
| `GET` | `/api/v1/users/{user_id}/following` | List users being followed |
| `POST` | `/api/v1/users/{user_id}/follow` | Follow a user |
| `DELETE` | `/api/v1/users/{user_id}/follow` | Unfollow a user |
| `POST` | `/api/v1/users/{user_id}/block` | Block a user |
| `DELETE` | `/api/v1/users/{user_id}/block` | Unblock a user |
| `GET` | `/api/v1/profiles/me` | Get current user's profile |
| `PATCH` | `/api/v1/profiles/me` | Update current user's profile & avatar |
| `PUT` | `/api/v1/profiles/me/interests` | Set selected interests |

### Interests (`/api/v1/interests`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/interests` | List all available predefined interests |
| `POST` | `/api/v1/interests` | Create new interest (Admin only) |

### Communities (`/api/v1/communities`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/communities` | Create a new community |
| `GET` | `/api/v1/communities/{community_id}` | Get community details |
| `PATCH` | `/api/v1/communities/{community_id}` | Update community settings (Owner) |
| `POST` | `/api/v1/communities/{community_id}/join` | Join public community or submit request |
| `DELETE` | `/api/v1/communities/{community_id}/leave` | Leave a community |
| `GET` | `/api/v1/communities/{community_id}/members` | List community members |
| `DELETE` | `/api/v1/communities/{community_id}/members/{user_id}` | Remove member (Owner) |
| `GET` | `/api/v1/communities/{community_id}/join-requests` | View pending join requests (Owner) |
| `POST` | `/api/v1/communities/{community_id}/join-requests/{request_id}/approve` | Approve request (Owner) |
| `POST` | `/api/v1/communities/{community_id}/join-requests/{request_id}/reject` | Reject request (Owner) |

### Posts & Media (`/api/v1/posts`)
| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/v1/posts` | Create text, image, or short video post |
| `GET` | `/api/v1/posts/{post_id}` | Get single post details |
| `DELETE` | `/api/v1/posts/{post_id}` | Delete post (Author / Owner / Admin) |
| `POST` | `/api/v1/posts/{post_id}/like` | Like a post |
| `DELETE` | `/api/v1/posts/{post_id}/like` | Remove like from a post |
| `POST` | `/api/v1/posts/{post_id}/save` | Save/bookmark a post |
| `DELETE` | `/api/v1/posts/{post_id}/save` | Remove post from bookmarks |

### Comments (`/api/v1/comments`, `/api/v1/posts/{post_id}/comments`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/posts/{post_id}/comments` | List comments for a post |
| `POST` | `/api/v1/posts/{post_id}/comments` | Post a new comment or reply |
| `PATCH` | `/api/v1/comments/{comment_id}` | Edit comment (Author only) |
| `DELETE` | `/api/v1/comments/{comment_id}` | Delete comment (Author / Moderator) |

### Feeds & Discovery (`/api/v1/feeds`, `/api/v1/search`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/feeds/home` | Personalized home feed |
| `GET` | `/api/v1/feeds/discover` | Community and post discovery feed |
| `GET` | `/api/v1/feeds/shorts` | Vertical short video feed |
| `GET` | `/api/v1/search` | Search users, communities, and posts |
| `GET` | `/api/v1/recommendations/communities` | Recommended communities |
| `GET` | `/api/v1/recommendations/users` | Recommended users by interest |

### Notifications & Reports (`/api/v1/notifications`, `/api/v1/reports`)
| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/api/v1/notifications` | Get user notifications |
| `PATCH` | `/api/v1/notifications/{notification_id}/read` | Mark single notification as read |
| `POST` | `/api/v1/notifications/read-all` | Mark all notifications as read |
| `POST` | `/api/v1/reports` | Submit report against user/content/community |

### Real-Time Chat & Live Rooms (`/api/v1/chats`, `/api/v1/live-rooms`)
| Method | Path | Description |
| --- | --- | --- |
| `WS` | `/api/v1/chats/ws/{community_id}` | WebSocket connection for community chat |
| `GET` | `/api/v1/chats/{community_id}/messages` | Fetch chat message history |
| `POST` | `/api/v1/live-rooms` | Create live room session (Owner) |
| `POST` | `/api/v1/live-rooms/{room_id}/token` | Obtain streaming access token (LiveKit/Agora) |
| `POST` | `/api/v1/live-rooms/{room_id}/end` | End live room session |
