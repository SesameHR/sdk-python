# SDK Parity — TypeScript ↔ Python

This document records the parity audit between [`@sesamehr/sdk`](https://github.com/SesameHR/sdk)
(TypeScript, source of truth) and `sesamehr` (Python). The goal: the two SDKs are
**clones** — same modules, methods, endpoints, defaults, request bodies, BI queries,
and retry/error/header behavior — differing only in agreed language idioms.

Last audited: 2026-06-14, against TS SDK `0.5.0` / Python SDK `0.1.0`.

## Verdict

**Structural parity: confirmed.** Across the 15 modules + core (errors, retry, config,
http, bi, types, auth, autologin, client/exports):

| Dimension | Result |
| --- | --- |
| Public methods | 1:1 in every module (camelCase ↔ snake_case) |
| Endpoints (URL paths) | identical, char-for-char |
| HTTP methods | identical |
| Method-arg defaults (limit/offset/page/orderBy/…) | identical |
| Request body keys/values | identical |
| BI query construction (from/select/where/group_by/order_by) | identical |
| Retry policy (2 retries, 500 ms, 5xx + connection only) | identical |
| Headers (Authorization/CSID/ESID/x-company-id/X-Region) | identical |
| Public export surface | full parity (minus intentional idioms below) |

Verification: a 25-unit adversarial source audit (each divergence re-checked by an
independent verifier), a mechanical method/endpoint/default cross-check, the unit
suite (67 tests), and a read-only smoke test against the live API (34/35 endpoints;
the 35th is a server-side bug — see below).

## Method parity matrix

Every method exists on both sides (TS name ↔ Python name):

| Module | Methods |
| --- | --- |
| employees | list, working, on_break, remote, offline, search, by_department, by_office, by_job_charge, count, me |
| checks | history, today, this_week, this_month, remote_only, open_checks, hours_by_employee, hours_by_department, total_hours, my_requests, clock_in, clock_out, breaks, pause, request_create, request_edit, request_delete |
| vacations | calendars, balance_by_employee, history, by_type, pending_requests, requests_by_employee, request, cancel |
| work_stats | summary |
| evaluations | list, detail, results, my_evaluations, pending |
| documents | directory, list, upload, download_url |
| expenses | list, detail, categories, company_expenses |
| announcements | list, detail |
| job_charges | list, detail, employees |
| recruitment | vacancies, totals, vacancy, candidates |
| team | status, working, status_summary, employee_checks, check_requests, vacation_requests, create_check, edit_check, delete_check, approve_check_request, reject_check_request, approve_vacation, reject_vacation |
| reports | query |
| contracts | list, active, expiring_soon, by_type, status_summary |
| notifications | send_push |
| community | channels, posts, post, comments, create_post |

## Intentional language idioms (not divergences)

These are agreed Python idioms, applied consistently. They are the *only* expected
differences in how the surface looks:

1. **Naming**: methods and model fields are `snake_case` (TS `camelCase`). `workStats` → `work_stats`, `firstName` → `first_name`.
2. **Synchronous**: no `async`/`await`. Calls block.
3. **`timeout` in seconds** (TS uses milliseconds). Default 30.
4. **Keyword args instead of options objects**: TS `*Params` interfaces (`ListEmployeesParams`, `WorkStatsParams`, `RetryOptions`, …) become Python keyword arguments. Same inputs, no separate exported type. Date-range params `from`/`to` are positional (`from` is a reserved word).
5. **pydantic models instead of interfaces**: responses are validated models with `snake_case` attributes + camelCase aliases. Unknown API fields are preserved in `model_extra` (never dropped). Models are **permissive** — every field is optional — so validation never rejects data the TS `as T` cast would accept (see below).
6. **OAuth helpers omitted**: `configFromCredentials`, `SesameSDK.fromCredentials`, `SesameCredentials` are intentionally absent. Authenticate with a private token, `login()`, or `auto_login()`.

## Divergences found and fixed

The audit + smoke test surfaced these; all are now resolved in the Python SDK:

| Area | Was | Fix |
| --- | --- | --- |
| `expenses.list` / `company_expenses` | crashed — API returns `{data:{expenses,totals}, meta}`, not `Paginated` | modeled the real envelope as `ExpensePage` |
| `evaluations` models | `my_evaluations` crashed — API uses `evaluationId`, model required `id` | all id/title fields optional; added `evaluation_id` |
| Response models with required `id` | could reject sparse responses TS accepts | `id` made optional on all response models |
| retry timeout detection | case-insensitive + extra `'timed out'` substring → could skip a retry TS would do | aligned to TS exactly (case-sensitive, `'aborted'`/`'timeout'`); kept the robust `is_timeout` flag for genuine timeouts (same outcome as TS) |
| `BiOrderBy.direction` | empty-string `''` coerced to `'ASC'` | preserves `''` like TS `?? 'ASC'` |
| `_build_check_timestamp` | replaced only the first space with `T` | replaces all spaces, matching TS |
| `work_stats.summary` employee id | `or` truthiness (empty string fell through) | `is not None` check, matching TS `??` |
| `auth` login token check | extra `isinstance` guard | falsiness-only, matching TS |
| Public exports | `tenant_headers`, `default_should_retry` were public (TS keeps them internal) | removed from `__all__`; added `PermissionVisibilities`, `Reaction` to match TS |

## Divergences fixed on the TypeScript side

Three cases where the Python behavior was correct and the TS SDK had a latent bug.
**Both SDKs are now aligned** (TS changed to match the correct/real shape):

1. **Empty-body responses.** TS `doFetch` parsed the body unconditionally and threw on an empty `2xx` (e.g. a `204` from a DELETE). Now returns `undefined` on an empty body, matching Python's `None`.
2. **Expenses return type.** TS typed `expenses.list`/`companyExpenses` as `Paginated<Expense>`, which never matched the real API. Now returns `ExpensePage` (`{expenses, totals…, meta}`) — the same shape as the Python `ExpensePage`. **Breaking change for existing TS consumers** (the return type changed); ship behind a version bump.
3. **`Evaluation`.** TS declared `id: string` (required) and lacked `evaluationId`. Now every field is optional with an index signature, and `evaluationId`/`evaluationTitle`/`formTitle`/… are typed — matching the Python `Evaluation`.

TS suite after these fixes: 168 tests green.

## Not an SDK issue

- **`evaluations.list` → HTTP 500.** Deterministic on the QA account with `limit=5` (works with `limit=2`); a server-side serialization error on specific evaluation data. The TS SDK issues the identical request and fails identically. Tracked as a backend bug, not a parity gap.
