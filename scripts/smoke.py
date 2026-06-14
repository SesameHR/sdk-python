"""Read-only smoke test against the real Sesame API.

Exercises every module's read endpoints and prints a pass/fail table. The point
is to validate that the *real* API response shapes parse into the pydantic
models — something the mocked unit tests can't catch.

NOTHING here mutates state: no clock-in/out, no post creation, no approvals.

Auth (pick one, via environment variables so secrets never hit the shell
history or this file):

  # email + password (uses SesameSDK.login)
  SESAME_EMAIL=you@company.com SESAME_PASSWORD='***' .venv/bin/python scripts/smoke.py

  # or a private token you already have
  SESAME_TOKEN=... SESAME_REGION=EU1 SESAME_COMPANY_ID=... SESAME_EMPLOYEE_ID=... \
      .venv/bin/python scripts/smoke.py
"""

from __future__ import annotations

import os
import sys
import traceback
from datetime import date, timedelta

from sesamehr import SesameSDK


def build_sdk() -> SesameSDK:
    email = os.environ.get("SESAME_EMAIL")
    password = os.environ.get("SESAME_PASSWORD")
    if email and password:
        print(f"→ Logging in as {email} (email + password)\n")
        sdk = SesameSDK.login(email, password)
        print(f"  region={sdk.config.region} company={sdk.config.company_id} employee={sdk.config.employee_id}\n")
        return sdk

    token = os.environ.get("SESAME_TOKEN")
    if token:
        print("→ Using private token from env\n")
        return SesameSDK(
            token=token,
            region=os.environ["SESAME_REGION"],
            company_id=os.environ["SESAME_COMPANY_ID"],
            employee_id=os.environ["SESAME_EMPLOYEE_ID"],
        )

    sys.exit(
        "No credentials. Set SESAME_EMAIL + SESAME_PASSWORD, or "
        "SESAME_TOKEN + SESAME_REGION + SESAME_COMPANY_ID + SESAME_EMPLOYEE_ID."
    )


def summarize(value: object) -> str:
    """One-line description of a result for the report."""
    if isinstance(value, list):
        return f"{len(value)} item(s)"
    # Paginated / CommunityPage have a `.data` list and a `.meta`
    data = getattr(value, "data", None)
    if isinstance(data, list):
        meta = getattr(value, "meta", None)
        total = getattr(meta, "total", None)
        suffix = f", total={total}" if total is not None else ""
        return f"{len(data)} row(s){suffix}"
    if value is None:
        return "None"
    # A single model — show a couple of identifying fields if present
    for attr in ("id", "name", "work_status", "status"):
        got = getattr(value, attr, None)
        if got is not None:
            return f"{type(value).__name__}({attr}={got!r})"
    return type(value).__name__


def main() -> int:
    sdk = build_sdk()

    today = date.today()
    frm = (today - timedelta(days=30)).isoformat()
    to = today.isoformat()

    # (label, thunk) — every thunk is a pure read.
    checks: list[tuple[str, object]] = [
        ("employees.me", lambda: sdk.employees.me()),
        ("employees.list", lambda: sdk.employees.list(limit=5)),
        ("employees.working", lambda: sdk.employees.working(limit=5)),
        ("employees.by_department", lambda: sdk.employees.by_department()),
        ("employees.count", lambda: sdk.employees.count()),
        ("checks.today", lambda: sdk.checks.today()),
        ("checks.this_month", lambda: sdk.checks.this_month()),
        ("checks.history", lambda: sdk.checks.history(frm, to, limit=5)),
        ("checks.breaks", lambda: sdk.checks.breaks()),
        ("checks.my_requests", lambda: sdk.checks.my_requests()),
        ("vacations.calendars", lambda: sdk.vacations.calendars(limit=5)),
        ("vacations.balance_by_employee", lambda: sdk.vacations.balance_by_employee(limit=5)),
        ("vacations.history", lambda: sdk.vacations.history(frm, to, limit=5)),
        ("vacations.pending_requests", lambda: sdk.vacations.pending_requests()),
        ("work_stats.summary", lambda: sdk.work_stats.summary(frm, to)),
        ("evaluations.list", lambda: sdk.evaluations.list(limit=5)),
        ("evaluations.my_evaluations", lambda: sdk.evaluations.my_evaluations(limit=5)),
        ("evaluations.pending", lambda: sdk.evaluations.pending()),
        ("documents.list", lambda: sdk.documents.list(limit=5)),
        ("expenses.list", lambda: sdk.expenses.list(limit=5)),
        ("expenses.categories", lambda: sdk.expenses.categories()),
        ("announcements.list", lambda: sdk.announcements.list(limit=5)),
        ("job_charges.list", lambda: sdk.job_charges.list(limit=5)),
        ("recruitment.vacancies", lambda: sdk.recruitment.vacancies(limit=5)),
        ("recruitment.totals", lambda: sdk.recruitment.totals()),
        ("team.status", lambda: sdk.team.status(limit=5)),
        ("team.status_summary", lambda: sdk.team.status_summary()),
        ("team.check_requests", lambda: sdk.team.check_requests()),
        ("team.vacation_requests", lambda: sdk.team.vacation_requests()),
        ("contracts.list", lambda: sdk.contracts.list(limit=5)),
        ("contracts.active", lambda: sdk.contracts.active(limit=5)),
        ("contracts.status_summary", lambda: sdk.contracts.status_summary()),
        (
            "reports.query",
            lambda: sdk.reports.query(
                {
                    "from": "core_context_employee",
                    "select": [{"field": "core_context_employee.name", "alias": "name"}],
                    "limit": 3,
                }
            ),
        ),
        ("community.channels", lambda: sdk.community.channels(limit=5)),
        ("community.posts", lambda: sdk.community.posts(limit=5)),
    ]

    width = max(len(label) for label, _ in checks)
    passed = 0
    failed: list[str] = []

    for label, thunk in checks:
        try:
            result = thunk()
        except Exception as exc:  # noqa: BLE001 - we want every failure, not the first
            failed.append(label)
            print(f"  ✗ {label:<{width}}  {type(exc).__name__}: {exc}")
            if os.environ.get("SMOKE_VERBOSE"):
                traceback.print_exc()
        else:
            passed += 1
            print(f"  ✓ {label:<{width}}  {summarize(result)}")

    sdk.close()

    print(f"\n{passed}/{len(checks)} read endpoints OK")
    if failed:
        print(f"Failed: {', '.join(failed)}")
        print("Re-run with SMOKE_VERBOSE=1 for full tracebacks.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
