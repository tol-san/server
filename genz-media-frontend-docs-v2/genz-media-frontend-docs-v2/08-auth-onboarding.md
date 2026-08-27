# 08 — Auth, Session & Onboarding

## Supported backend features

- Register
- Login
- Logout
- Email verification (feature requirement)
- Forgot password
- Reset password
- Access token
- Refresh token
- Change password

## Session gate

```text
Launch
  ↓
Read secure session
  ↓
Access token valid?
  ├─ Yes → load profile → app
  └─ No/unknown → refresh
                  ├─ success → app
                  └─ failure → login
```

## Login

Inputs follow OpenAPI.

Frontend:
- validate required fields;
- disable duplicate submit;
- translate backend errors;
- preserve non-sensitive input when useful.

## Registration

Expected product data from backend requirements includes account credentials; exact request schema must come from OpenAPI.

After successful registration:
- follow backend verification behavior;
- do not assume automatic login if implementation differs;
- continue to interest onboarding after authenticated state is established.

## Email verification

The feature docs list Email Verification, but the endpoint directory does not document its route.

See `22-contract-gaps-openapi-checks.md`.

Do not invent `/verify-email`.

## Password reset

Flows:
```text
Forgot Password
   ↓
Request reset
   ↓
Backend/email token process
   ↓
Reset Password
   ↓
Success → Login
```

## Interest onboarding

Backend supports:
- `GET /api/v1/interests`
- `PUT /api/v1/profiles/me/interests`

Suggested copy:

> Choose what you're into. We'll use this to recommend people, communities, posts, and shorts.

Use selectable chips/cards.

Do not request media permissions during onboarding.

## Logout

1. call backend logout/revocation;
2. clear secure local credentials;
3. clear sensitive app state;
4. disconnect notification/chat/live real-time clients;
5. reset navigation to Login.
