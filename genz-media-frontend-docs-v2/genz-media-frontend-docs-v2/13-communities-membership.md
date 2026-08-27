# 13 — Communities & Membership

## Community types

### Public
Join immediately.

### Private
Join request → owner approval.

## Roles

### Owner
Can:
- manage community info;
- cover;
- join requests;
- members;
- remove members;
- moderate community posts/chat messages;
- start/end Live Rooms.

### Member
Can:
- view/create community content;
- participate in community group chat.

## Community Detail

```text
Cover

Community Name
Public / Private
Member count
Interests
Description

[ Join / Requested / Joined ]
[ Manage ] owner only

Posts | About | Members

[ Group Chat ]
[ Live Room ] when applicable
```

## Membership states

```text
Join
Joining…
Requested
Joined
Owner
```

## Public join flow

```text
Join
 ↓
Submitting
 ├─ success → Joined
 └─ error → restore Join + retry
```

## Private join flow

```text
Request to Join
 ↓
Submitting
 ├─ success → Requested
 └─ error → restore
```

## Leave

Use confirmation if leaving can interrupt chat/live access.

Leaving should:
- refresh membership;
- remove community-only compose permission;
- close chat if connected;
- update accessible UI.

## Owner management

Screens/panels:
- Edit Community
- Members
- Join Requests
- Community Reports
- moderation actions

## Member removal

Owner removes member via backend.
After success:
- remove row;
- reconcile count;
- chat access termination is backend-driven.

## Posting

Only members can publish to community.

Destination selector must use backend-confirmed membership, not guessed local state.
