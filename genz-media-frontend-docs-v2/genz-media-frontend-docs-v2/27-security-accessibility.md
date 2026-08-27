# 27 — Security & Accessibility

# Security

## Tokens

Store access and refresh tokens in OS-protected secure storage.

Never put secrets in:
- SharedPreferences;
- logs;
- analytics properties;
- crash metadata.

## Authorization

UI visibility is not security.

Backend must authorize:
- owner controls;
- member access;
- delete;
- moderation;
- chat;
- live host;
- reports.

## Refresh

Use one coordinated refresh operation to avoid parallel token-refresh races.

## Blocking

Do not cache permissions in a way that allows blocked interaction after backend state changes.

## Chat

Use backend membership check and one-time ticket contract if implemented.
Do not reconnect endlessly after authorization close.

## Live

Never expose host publishing controls based only on local UI role guess.

# Accessibility

## Required

- semantic labels;
- sufficient contrast;
- text scaling;
- ~48dp targets;
- no color-only state;
- reduced motion;
- safe areas;
- keyboard-safe forms;
- visible gesture alternatives.

## Shorts

Swipe may navigate videos, but:
- visible Like;
- visible Comment;
- visible Save;
- visible Share;
- visible play/audio control path.

## Chat

- messages must be screen-reader navigable;
- sending/failure state announced;
- composer remains visible above keyboard.

## Live

- controls have labels;
- viewer count is readable;
- ending live requires clear destructive confirmation for host.

## Dynamic text

Layouts must not clip at larger font settings.
