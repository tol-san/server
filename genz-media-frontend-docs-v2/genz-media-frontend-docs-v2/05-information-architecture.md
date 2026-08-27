# 05 — Information Architecture

## Global app

```text
App
├── Auth / Onboarding
└── Main Shell
    ├── Home
    ├── Shorts
    ├── Create
    ├── Discover
    └── Profile
```

## Contextual global access

```text
Top App Bar
├── Notifications
└── contextual actions
```

## Discover hierarchy

```text
Discover
├── Search
│   ├── All
│   ├── Users
│   ├── Communities
│   ├── Posts
│   └── Interests
├── Recommended Posts
├── Recommended Users
└── Recommended Communities
```

## Community hierarchy

```text
Community Detail
├── Posts
├── About
├── Members
├── Group Chat
├── Live Room
└── Manage (Owner)
    ├── Edit
    ├── Join Requests
    ├── Members
    └── Community-scoped Reports
```

## Profile hierarchy

```text
My Profile
├── Edit
├── Interests
├── Followers
├── Following
├── Saved Posts
├── Communities
├── Account/Security
└── Logout
```

## Entity action pattern

Use overflow menus for low-frequency or destructive actions:
- Report
- Block
- Delete
- Leave
- moderation actions

## Admin/moderation hierarchy

Admin functionality is not a primary bottom tab.
Expose only to authorized users through a management entry point if the mobile app is intended to support admin operations.
