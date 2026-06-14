# Sesame HR Python SDK

Official Python SDK for the [Sesame HR](https://www.sesamehr.com) API. Synchronous client built on `httpx` with `pydantic` models. Python port of [`@sesamehr/sdk`](https://github.com/SesameHR/sdk).

## Install

```bash
pip install sesamehr
```

Requires Python 3.10+.

## Quickstart

Authenticate with a private token — no OAuth required:

```python
from sesamehr import SesameSDK

sdk = SesameSDK(
    token="your-private-token",
    region="EU1",
    company_id="your-company-id",
    employee_id="your-employee-id",
)

for employee in sdk.employees.working():
    print(employee.name, employee.work_status)
```

Or login with email + password (same flow the SSO uses internally — no OAuth, no redirects):

```python
sdk = SesameSDK.login("user@company.com", "****")
sdk.checks.clock_in()
```

The client holds an HTTP connection pool; use it as a context manager (or call `sdk.close()`) in long-running apps:

```python
with SesameSDK.login("user@company.com", "****") as sdk:
    stats = sdk.work_stats.summary("2026-06-01", "2026-06-30")
    print(stats.seconds_worked, stats.balance)
```

## Modules

| Module | Description |
| --- | --- |
| `sdk.employees` | List/search employees, work status, counts, `me()` profile with roles & permissions |
| `sdk.checks` | Clock in/out, breaks, check history, hours aggregation, check requests |
| `sdk.vacations` | Calendars, balances, day-off history, requests |
| `sdk.work_stats` | Hours worked vs expected, balance, averages |
| `sdk.evaluations` | Performance evaluations and results |
| `sdk.documents` | Browse directories, list/upload/download documents |
| `sdk.expenses` | Personal and company expenses, categories |
| `sdk.announcements` | Company announcements |
| `sdk.job_charges` | Job positions and assigned employees |
| `sdk.recruitment` | Vacancies, totals, candidates |
| `sdk.team` | Team status, manage checks, approve/reject requests (admin) |
| `sdk.reports` | Raw BI queries against any Sesame BI table |
| `sdk.contracts` | Contracts, expirations, type/status breakdowns |
| `sdk.notifications` | Push notifications to the mobile app |
| `sdk.community` | Wall channels, posts and comments; publish posts |

All methods return pydantic models with snake_case attributes (the camelCase API fields are mapped automatically; unknown fields are kept in `model_extra`).

### Examples

```python
# Check history for a date range (positional from/to)
entries = sdk.checks.history("2026-06-01", "2026-06-12", employee="ana")

# Vacation balance for the current year
balances = sdk.vacations.balance_by_employee()

# Raw BI query
from sesamehr import BI_TABLES, BI_TEMPORAL

rows = sdk.reports.query({
    "from": BI_TABLES["checks"],
    "select": [
        {"field": "core_context_employee.name", "alias": "name"},
        {"field": "schedule_context_check.seconds_worked", "aggregate": "SUM", "alias": "total"},
    ],
    "where": [{"field": "schedule_context_check.date", "operation": BI_TEMPORAL["this_month"]}],
    "group_by": ["core_context_employee.name"],
})

# Publish a post with an image to a community channel
with open("photo.png", "rb") as f:
    sdk.community.create_post(
        channel_id="...",
        content="Hello from Python!",
        file=f,
        file_name="photo.png",
    )
```

## Error handling

```python
from sesamehr import SesameApiError, SesameConnectionError

try:
    sdk.checks.clock_in()
except SesameApiError as e:
    print(e.status, e.message, e.errors)
except SesameConnectionError as e:
    print("network problem:", e)
```

Requests are retried automatically (2 retries, 500 ms delay) on connection errors and 5xx responses; 4xx responses and timeouts are not retried.

## Differences vs the TypeScript SDK

- Synchronous API (no `await`).
- Methods and fields are snake_case: `sdk.workStats.summary()` → `sdk.work_stats.summary()`, `employee.workStatus` → `employee.work_status`.
- `timeout` is in **seconds** (TS uses milliseconds). Default: 30.
- Date-range methods take `from`/`to` as positional arguments (`from` is a reserved word in Python): `sdk.checks.history("2026-06-01", "2026-06-12")`.
- OAuth helpers (`fromCredentials`) are not included — authenticate with a private token, `SesameSDK.login()`, or `SesameSDK.auto_login()`.

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e . pytest
pytest
```

## License

MIT
