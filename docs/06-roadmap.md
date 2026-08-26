# 6. Development Roadmap & Implementation Plan

## 6.1 Eight-Week Implementation Timeline

| Week | Milestone / Feature Areas | Deliverables |
| --- | --- | --- |
| **Week 1** | Project setup & Core Foundation | FastAPI structure, PostgreSQL, Alembic migrations, Authentication (JWT), User Profiles |
| **Week 2** | Discovery & Community Core | Predefined Interests taxonomy, Follow/Unfollow system, Community creation (Public/Private) |
| **Week 3** | Memberships & Permissions | Join requests, Membership approval flows, Role-based permissions (Admin, Owner, Member) |
| **Week 4** | Content & Discussions | Text/Image/Short Video Posts, Media upload storage integration, Comments and Replies |
| **Week 5** | Engagement & Moderation | Post Likes, Bookmarks (Save), Sharing links, Moderation reports, In-app Notifications |
| **Week 6** | Discovery Feeds & Search | Home Feed, Discover Feed, Shorts Feed, Search (Users/Communities/Posts), Rule-Based Recommendations |
| **Week 7** | Real-Time Chat & Testing | WebSocket Community Group Chat, Redis integration, Comprehensive integration tests |
| **Week 8** | Live Streaming & Deployment | External LiveKit/Agora room tokens, OpenAPI polish, Docker Compose deployment |

---

## 6.2 Implementation Order Priority

If development falls behind schedule, strictly prioritize the core sequence before progressing:

```text
Authentication
    ↓
Users & Profiles
    ↓
Interests
    ↓
Follow System
    ↓
Communities & Memberships
    ↓
Posts & Media
    ↓
Comments
    ↓
Engagement (Likes / Saves)
    ↓
Feed & Search
    ↓
Notifications
    ↓
Group Chat (WebSocket)
    ↓
Live Room (External Integration)
```

> [!NOTE]
> Live Room integration and WebSocket Chat are treated as stretch goals and should only begin after the core CRUD, auth, community, and feed features are fully stable and tested.
