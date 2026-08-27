# 29 — Testing & Definition of Done

A feature is not complete because a screen renders.

## Every feature

- navigation works;
- backend contract is real;
- loading exists;
- error exists;
- empty exists where relevant;
- auth state is respected;
- permission state is correct;
- mutation failure recovers;
- text scaling works;
- screen reader labels exist;
- dark/light behavior is correct where applicable.

## API feature

- request schema matches OpenAPI;
- response mapping tested;
- pagination tested;
- 401 refresh path tested;
- 403 path tested;
- validation errors mapped.

## Feed

- initial load;
- refresh;
- pagination;
- duplicate request prevention;
- counter reconciliation.

## Search

- query debounce;
- no results;
- domain filters/routes;
- blocked/inaccessible results not reintroduced client-side.

## Upload

- permission denied;
- upload fail;
- publish fail after upload;
- retry;
- draft preservation.

## Notifications

- initial history;
- unread badge;
- real-time insert;
- duplicate-event handling;
- reconnect;
- mark read;
- read all;
- delete.

## Chat

- member connects;
- non-member denied;
- history pagination;
- message retry with same client ID;
- rate limit;
- typing clear;
- reconnect;
- kick/removal closes access.

## Live

- viewer token;
- host token;
- join fail;
- room ends;
- host end;
- viewer count not locally fabricated;
- provider disconnect.

## Moderation

- owner scope;
- admin scope;
- valid state transitions;
- forbidden access.

## Definition of Done

Check `31-agent-rules.md` before merging.
