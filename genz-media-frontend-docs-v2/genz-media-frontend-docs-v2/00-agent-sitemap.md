# 00 — Agent Sitemap

## Always read first

For any Flutter implementation task:

1. `02-backend-scope-priority.md`
2. `03-frontend-product-decisions.md`
3. the feature-specific document
4. `21-api-contract-map.md`
5. `22-contract-gaps-openapi-checks.md`
6. `23-ui-state-error-loading.md`
7. `31-agent-rules.md`

## Task routing

| Task | Read |
|---|---|
| App shell | `04`, `05`, `06`, `25` |
| Login/Register | `08`, `21`, `23`, `27` |
| Session refresh/logout | `08`, `21`, `24`, `25`, `27` |
| Interests onboarding | `08`, `01`, `03`, `04` |
| Home | `09`, `15`, `21`, `23`, `26` |
| Shorts | `10`, `15`, `21`, `23`, `26`, `27` |
| Discover | `11`, `09`, `13`, `21` |
| Search | `11`, `21`, `22`, `23` |
| Profile | `12`, `21`, `23` |
| Follow/Block | `12`, `21`, `23`, `27` |
| Community | `13`, `21`, `23` |
| Owner membership management | `13`, `18`, `21` |
| Create Post | `14`, `21`, `23`, `26` |
| Comments | `15`, `21`, `23` |
| Save/Share/Report | `16`, `21`, `22` |
| Notifications | `17`, `21`, `24` |
| Moderation | `18`, `21`, `27` |
| Community Chat | `19`, `21`, `22`, `24`, `27` |
| Live Room | `20`, `21`, `22`, `24`, `26` |
| Riverpod | `25`, feature doc |
| Dio/API | `21`, `22`, `25`, `27` |
| Error/loading | `23` |
| Performance | `26` |
| Accessibility/security | `27` |
| Testing | `29`, feature doc |

## Do not browse all docs for one small task

Load only the relevant feature documents plus the contract/rules files above.

## Hard rule

If API docs and feature docs disagree:

```text
Do not guess
   ↓
Inspect running OpenAPI
   ↓
Use implemented contract
```
