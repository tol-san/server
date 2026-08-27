# 28 — Core User Flows

## New user

```text
Register
 ↓
Verification behavior from backend
 ↓
Login/authenticated
 ↓
Select Interests
 ↓
Recommendations
 ↓
Home
```

## Discover → Community

```text
Discover/Search
 ↓
Community
 ↓
Join / Request
 ↓
Joined
 ↓
Posts / Chat / Live
```

## Search → User → Follow

```text
Search
 ↓
User Result
 ↓
Public Profile
 ↓
Follow
 ↓
Following
```

## Create community post

```text
Create
 ↓
Choose type
 ↓
Choose joined Community
 ↓
Enter content
 ↓
Upload media if needed
 ↓
Create post
 ↓
Post Detail
```

## Report content

```text
Overflow
 ↓
Report
 ↓
Reason
 ↓
Submit
 ↓
Acknowledgement
```

## Notification

```text
Realtime notification
 ↓
Unread badge
 ↓
Notification Center
 ↓
Open
 ↓
Mark read
 ↓
Target route when payload supports
```

## Chat

```text
Community
 ↓
Chat
 ↓
Authorize/connect
 ↓
Load history
 ↓
Send with client_message_id
 ↓
Confirmed
```

## Membership removal during chat

```text
Socket control close
 ↓
Stop composer
 ↓
Refresh membership
 ↓
Exit/restrict chat
```

## Live viewer

```text
Community
 ↓
Live Room
 ↓
Request token
 ↓
Connect provider
 ↓
Watch
 ↓
Leave / room ends
```

## Live host

```text
Community Owner
 ↓
Create Room
 ↓
Start (verify actual route)
 ↓
Host token
 ↓
Go Live
 ↓
End
 ↓
Persisted session metrics
```
