# 14 — Create Post & Media

## Supported types

### Text
- title;
- content;
- visibility;
- optional community ID.

### Image
- caption;
- one or more image URLs;
- visibility;
- optional community ID.

### Short Video
- caption;
- video URL;
- thumbnail URL;
- duration;
- visibility;
- optional community ID.

## Ownership

```text
Personal post  → community_id = null
Community post → community_id = <ID>
```

## Create hub

```text
Create

Text
Photo
Short Video
```

## Destination

```text
Post to

● My Profile
○ Joined Community A
○ Joined Community B
```

Only include valid community destinations.

## Media workflow

The backend architecture stores media in object storage, not PostgreSQL.

Flutter flow:

```text
Select
  ↓
Preview
  ↓
Metadata/caption
  ↓
Upload media according to implemented backend/storage contract
  ↓
Create post
  ↓
Published
```

## Critical state distinction

```text
Upload complete ≠ Post published
```

Do not show Published before `POST /api/v1/posts` succeeds.

## Draft preservation

On:
- network error;
- upload failure;
- post creation failure;

preserve safe user inputs/media references and allow Retry.

## Permissions

Ask for media permissions only when selecting media.

## Excluded

Do not build:
- timeline editor;
- filters marketplace;
- music library;
- transcoding pipeline;
- remix editor.
