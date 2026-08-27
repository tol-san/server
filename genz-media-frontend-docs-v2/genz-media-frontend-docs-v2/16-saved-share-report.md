# 16 — Saved Posts, Share & Report

# Save

Feature requirement:
- Save / Unsave
- private saved post list

Documented mutation endpoints:
- `POST /api/v1/posts/{post_id}/save`
- `DELETE /api/v1/posts/{post_id}/save`

The endpoint directory does not explicitly document the list endpoint for Saved Posts.

See `22-contract-gaps-openapi-checks.md`.

## Saved UX

Profile → Saved Posts

Other users must not see who saved a post.

# Share

Backend feature requirement says:
- generate shareable link;
- increment share counter.

The API endpoint directory does not explicitly list a share endpoint.

Frontend should:
- use implemented backend share/link contract;
- invoke native system share sheet.

Do not invent a share-counter route.

# Report

`POST /api/v1/reports`

Reportable targets:
- user;
- post;
- comment;
- community;
- chat message.

Documented reasons:
- `spam`
- `harassment`
- `inappropriate_content`
- `hate_speech`
- `violence`
- `copyright`
- `other`

## Report sheet

```text
Report
Choose reason
Optional details if schema supports
Submit
```

Do not add unconfirmed fields.

## Success

Use brief acknowledgement:

> Report submitted.

Do not expose moderation outcome immediately unless backend returns it and product wants it.
