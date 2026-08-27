# 15 — Posts, Comments & Engagement

## Post detail

Endpoint:
`GET /api/v1/posts/{post_id}`

Structure:

```text
Author / community
Full content
Media
Like · Comment · Save · Share
Counts
Comments
```

Delete appears only for authorized contexts and still relies on backend authorization.

## Like

Endpoints:
- `POST /api/v1/posts/{post_id}/like`
- `DELETE /api/v1/posts/{post_id}/like`

Backend enforces one like per user/post.

UI:
```text
Not Liked
Submitting
Liked
```

## Comments

Endpoints:
- `GET /api/v1/posts/{post_id}/comments`
- `POST /api/v1/posts/{post_id}/comments`
- `PATCH /api/v1/comments/{comment_id}`
- `DELETE /api/v1/comments/{comment_id}`

Supports:
- comments;
- replies;
- edit own;
- authorized moderation delete.

## Reply UI

Avoid deeply nested indentation.

```text
Main comment
  ├─ reply
  └─ View more replies
```

One visual indentation level is preferred on phones.

## Comment composer

- attached above keyboard;
- prevent duplicate submission;
- preserve text on failure;
- reply target clearly visible.

## Authorization

Backend rules:
- user edits/deletes own comment;
- community owner can moderate inside owned community;
- admin can moderate platform-wide.
