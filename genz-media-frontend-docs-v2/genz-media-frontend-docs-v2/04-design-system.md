# 04 — Design System

## Style direction

- content-dominant;
- neutral surfaces;
- low chrome;
- clear hierarchy;
- modern mobile social feel;
- one recognizable brand accent.

## Palette

| Token | Hex | Usage |
|---|---:|---|
| Night 950 | `#0B0D12` | Shorts / darkest stage |
| Night 900 | `#121722` | dark elevated surfaces |
| Primary Violet | `#6D4AFF` | primary action / selected state |
| Primary Pressed | `#5B3DF5` | pressed primary |
| Signal Mint | `#38E8C6` | selective secondary accent |
| Signal Coral | `#FF6B7A` | selective social accent |
| Canvas | `#F7F8FA` | light app background |
| Surface | `#FFFFFF` | primary light surface |
| Text Primary | `#111827` | main light text |
| Text Inverse | `#F8FAFC` | dark/video text |
| Text Muted | `#64748B` | metadata |
| Border | `#E2E8F0` | subtle boundaries |
| Success | `#15803D` | success |
| Warning | `#A16207` | warning |
| Error | `#DC2626` | destructive/error |

Do not encode meaning with color only.

## Typography

Recommended UI family: **Inter** or equivalent clean system sans.

| Token | Size / line-height | Weight |
|---|---:|---:|
| Display | 32 / 38 | 700 |
| Heading Large | 28 / 34 | 700 |
| Heading | 24 / 30 | 700 |
| Title | 20 / 26 | 600 |
| Body Large | 17 / 25 | 400–500 |
| Body | 16 / 24 | 400 |
| Body Small | 14 / 20 | 400–500 |
| Label | 14 / 18 | 600 |
| Caption | 12 / 16 | 500 |

## Spacing

```text
4, 8, 12, 16, 24, 32, 48
```

Use 8dp layout rhythm with 4dp fine adjustment.

## Radius

```text
12 → compact controls
16 → cards/media
24–28 → large sheets
```

## Touch targets

Aim around **48dp × 48dp** for primary interactive icons.

## Motion

```text
~120ms micro feedback
~180ms component transition
~240–300ms sheet/navigation transition
```

Subtle spring/haptic may be used for:
- Like
- Follow
- Join
- successful send

Respect reduced-motion preference.

## Component groups

### Foundation
- colors
- type
- spacing
- icons
- safe area
- radius
- motion
- light/dark theme

### Core
- buttons
- icon buttons
- text fields
- password field
- top app bar
- bottom nav
- tabs
- chips
- snackbar
- dialog
- bottom sheet

### Social
- avatar
- author row
- post card
- user card
- community card
- Follow button
- Join state button
- counters
- comments
- media carousel

### Search
- search field
- result tabs/filter chips
- recent query row if locally stored
- empty/no-result state

### Notification
- bell + badge
- notification row
- read/unread marker

### Chat
- message bubble
- composer
- typing indicator
- presence count
- connection banner
- retry/pending/sent state

### Live
- room card
- live badge
- viewer count
- host controls
- join/leave state

### System
- skeleton
- empty state
- error
- offline banner
- pagination loader
