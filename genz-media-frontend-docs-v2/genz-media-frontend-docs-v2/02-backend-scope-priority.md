# 02 — Backend Scope & Priority

## P0 — Required

- Authentication
- Profile
- Interests
- Follow
- Community
- Text/Image/Video Posts
- Like
- Comment

## P1 — Important

- Save
- Share
- Report
- Search
- Feed
- Rule-Based Recommendations
- Notifications

## P2 — Stretch Goal classification

- Community Group Chat
- External Live Room Integration

## Important status note

Although Chat and Live are categorized as P2/stretch in the feature-priority table, the latest backend feature document explicitly marks both as:

- **Community Group Chat — Implemented, Level 3 Advanced Reliability**
- **Live Streaming Rooms — Implemented, Level 3 Advanced Reliability**

Therefore the frontend documentation includes them, but they should remain **contextual community features**, not global primary tabs.

## Features explicitly excluded from MVP

Do not implement:
- Friend Requests
- Stories / disappearing status
- Direct 1-on-1 messaging
- 1-on-1 video calls
- ML/AI recommendation model
- Payment / monetization / ads
- automatic AI moderation
- built-in video transcoding/editor pipeline
- microservices-specific client assumptions

## Backend rules frontend must respect

### Follow
- cannot follow self;
- cannot duplicate follow relationship;
- follow is immediate;
- unfollow removes relationship immediately.

### Community
- owner automatically member;
- no duplicate membership;
- private joins require owner approval;
- public joins are immediate;
- owner manages settings and approvals.

### Posts
- personal post: `community_id = null`;
- community post: valid `community_id`;
- must be member to create community post.

### Comments
- user edits/deletes own comments;
- community owner moderates comments in owned community;
- system admin moderates platform-wide.

### Chat
- only verified members may connect;
- leaving/removal immediately terminates authorization.

### Blocking
If A blocks B:
- B cannot follow A;
- B cannot interact with A's content;
- existing follow relationships are severed.
