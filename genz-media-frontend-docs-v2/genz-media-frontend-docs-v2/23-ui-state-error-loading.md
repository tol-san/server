# 23 — UI State, Loading & Errors

## Standard read states

```text
Initial
Loading
Success
Empty
Error
Refreshing
LoadingMore
```

## Mutation states

```text
Idle
Submitting
Success
Failure
```

## Real-time states

```text
Disconnected
Connecting
Connected
Reconnecting
ClosedByAuthorization
Failed
```

## Upload states

```text
Idle
Selecting
Ready
Uploading(progress)
UploadFailed
Uploaded
Publishing
PublishFailed
Published
```

## Rules

### Initial load
Use geometry-matching skeletons.

### Refresh
Keep current content visible.

### Pagination
Append loader below existing items.

### Transient error
Keep stale content when possible.

### Offline
Show connectivity state without destroying readable data.

### Unauthorized
Attempt centralized refresh before forcing Login.

### Forbidden
Do not automatically retry.

### Mutation failure
Preserve user input and roll back optimistic state.

## Empty-state examples

### Home
> Your feed is just getting started. Follow people or join communities.

### Search
> No results found.

### Saved
> Posts you save will appear here.

### Notifications
> You're all caught up.

### Chat
> No messages yet. Start the conversation.

### Comments
> Start the conversation.

## Error language

Never show raw:
- stack traces;
- Redis/Meilisearch errors;
- HTTP exception class names.

Map to actionable user copy.
