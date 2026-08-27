# 12 — Profile, Follow & Block

## Profile fields documented

- `username`
- `display_name`
- `bio`
- `avatar_url`
- selected interests
- `follower_count`
- `following_count`
- `post_count`

## Public profile

```text
Avatar
Display Name
@username
Bio
Interest chips

Posts · Followers · Following

[ Follow / Following ]
Content
```

Overflow:
- Block / Unblock
- Report

## My profile

Replace Follow with:
- Edit Profile

Provide entry points:
- Manage Interests
- Saved Posts
- Followers
- Following
- Communities
- Change Password
- Logout

## Follow

Backend:
- directional;
- no approval;
- no self-follow;
- unique relationship.

Button states:
```text
Follow
Submitting
Following
```

Update visible follower counts after success.

Follow event can produce notification to target user.

## Block

Confirmation recommended.

```text
Block user?
   ↓
Confirm
   ↓
POST block
   ↓
Refresh relationship/content state
```

Backend effects include:
- sever follow relationships;
- prevent target from following blocker;
- prevent interaction with blocker's content.

Do not recreate all blocking logic in Flutter. Render server-authorized state.

## Profile content

Avoid fake local tabs for text/image/shorts unless backend provides efficient server filtering.
