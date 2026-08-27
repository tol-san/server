# 01 — Product Foundation

## Project

**Name:** GenZ Media  
**Type:** Social Community Platform  
**Mobile client:** Flutter

## Core idea

Connect people through **shared interests and communities**, not friend requests.

Users can:
- discover people with similar interests;
- create/join communities;
- publish text, image, and short-video posts;
- follow users;
- like, comment, save, share, and report;
- search across platform entities;
- receive in-app notifications;
- participate in community chat;
- join community live rooms.

## Unique value proposition

> **Interest-Based Community Discovery**

Recommendation inputs documented by the backend include:
- selected interests;
- joined communities;
- liked posts;
- saved content;
- viewed content types;
- followed users.

The first recommendation model is rule-based rather than ML.

## Product promise

Recommended frontend positioning:

> **Discover people, content, and communities through shared interests.**

Shorter brand expression:

> **Watch. Join. Belong.**

## Core journey

```text
Register / Login
      ↓
Select Interests
      ↓
Receive Recommendations
      ↓
Join Community / Follow User
      ↓
View or Create Content
      ↓
Like / Comment / Save / Share
      ↓
Search / Discover More
      ↓
Notifications
      ↓
Community Chat / Live Room
```

## Frontend responsibility

Flutter owns:
- presentation;
- navigation;
- local UI state;
- session coordination;
- API consumption;
- device media interaction;
- real-time connection lifecycle;
- accessibility.

Backend owns:
- authentication;
- authorization;
- business rules;
- permissions;
- persistence;
- search filtering;
- ranking;
- recommendation scoring;
- moderation;
- membership;
- chat authorization;
- live room authorization.
