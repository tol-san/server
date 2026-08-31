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

The backend stores media in object storage, not PostgreSQL. Post media is
private and API responses contain short-lived signed URLs. Only the user who
uploaded an object may attach its canonical media reference to a post.

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

An upload failure is an error and must not be treated as a successful upload or
replaced with a placeholder URL.

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
