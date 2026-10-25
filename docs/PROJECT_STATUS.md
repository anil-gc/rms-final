# Project status

Date: 2026-10-20 (Asia/Kathmandu).
Current phase: **Phase 3 - Restaurant, Menu & Table Management**.
State: **implemented and verified; publication authorized for PR review**.
The owner authorized committing/pushing `feature/restaurant-menu-tables` and
opening a PR against `feature/react-frontend`. No merge is authorized.
Phase 4 has not started.

## Branch and preserved baseline

Branch: `feature/restaurant-menu-tables`, created from the completed frontend
commit `64d0debd98652c411293795508935c2962cba140`. That commit includes the
Phase 2 accounts backend (`2006becdb1222132b7b9fa3f0b06a9c971ab2477`) and
Phase 1 foundation (`551ac051ccd2706da325ad57ac45c5cef5201cb2`). Origin remains
`https://github.com/anil-gc/rms-final.git`.

[Frontend PR #1](https://github.com/anil-gc/rms-final/pull/1) was inspected and
left open/unmerged. No existing branch was merged or overwritten. Existing
accounts models, authentication, permissions, credential services, and account
migrations remain unchanged. Existing account IDs, roles, credential hashes,
PIN flags, active states, and authentication versions matched a pre-migration
digest after browser verification. The separate prototype/database is untouched.

Publication review confirmed PR #1 is still open and unmerged, and the remote
frontend head is still the baseline commit above. The Phase 3 PR is stacked
against `feature/react-frontend` so it contains only Phase 3 changes. Once the
parent PR is separately integrated, reviewers should reassess the target base
before a future merge; no parent merge or branch rewrite was performed here.

## Phase 3 implementation

- Singleton restaurant name, description, address, phone, email, logo, fixed NPR
  currency, daily opening/closing hours (including overnight), and active state.
- Validated bounded raster upload, normalized PNG storage, protected logo
  delivery, replacement/removal, and no public media route.
- Menu categories with display order and descriptions; items with category,
  descriptions, exact decimal prices, availability, and active state.
- Effective availability considers item, category, and restaurant activity.
- Physical table names, capacity, manual available/occupied state, and archiving.
  An occupied table must be made available before archiving.
- Owner/Manager manage workspace records; other provisioned users read active
  records. Archived records remain accessible to management and can be restored.
- Strict API inputs, database constraints, protected foreign keys, transactional
  updates, no-store responses, and read-only Django admin inspection.
- New React restaurant, menu, and table screens; sidebar/overview navigation;
  shared session/CSRF transport for JSON and multipart; loading/error/empty/
  success states; search, filters, edit dialogs, archiving and reactivation.
- Existing temporary-PIN route restrictions and server permissions apply to
  every new resource. No authentication workflow was replaced.

New dependency: `Pillow==13.0.0`. New migrations:
`restaurants/0001_initial.py` and `menu/0001_initial.py`. Only these new domain
migrations were applied to the isolated preview database; existing migrations
were not edited. No automatic seed, bootstrap user, tenancy, or business-order
record is added by migrations. See [the Phase 3 contract](PHASE_3.md).

## Verification

| Check | Result |
| --- | --- |
| Frontend ESLint | Passed |
| Frontend Vitest | 22 tests passed across 5 files |
| TypeScript + Vite production build | Passed |
| Production-dependency npm audit | 0 vulnerabilities |
| Django system/database checks | Passed, no issues |
| Production Django deploy checks | Passed with TLS-required configuration; no deployment performed |
| Migration drift and pending checks | Passed; two new migrations applied locally |
| Backend pytest against PostgreSQL 18 | 201 tests passed, including 66 new workspace cases |
| Ruff lint/format and Python dependency consistency | Passed |

The backend suite includes the 135 existing account/foundation regressions.
All checks in the table were rerun successfully for publication on 2026-10-20.
New tests cover all five roles, anonymous/legacy/temporary-PIN rejection, CSRF,
non-overwriting singleton setup, field validation, case-insensitive uniqueness,
archive/read rules, exact prices, direct PostgreSQL constraints (including NaN),
protected relationships, invalid occupancy/archive combinations, logo size/
format/dimensions/normalization/protection/cleanup, and read-only admin.
Frontend additions cover multipart CSRF/cookies, decimal string transport,
unconfigured versus failed requests, Manager setup, staff read-only screens,
and the profile prerequisite, alongside all existing auth tests.

Real-browser verification against Django/PostgreSQL passed:

- Owner profile creation, email/hours, logo upload/authenticated PNG delivery,
  and removal; the generated test logo was removed afterwards.
- Category/item create/edit, exact decimal price changes, availability, category
  and item archive/reactivate, and menu search.
- Table creation, occupancy, occupied-table archive rejection, archive/reactivate,
  and reload persistence.
- Staff PIN login, read-only restaurant/menu/table screens, hidden mutation
  controls, backend write denial, mobile navigation, and logout/private-logo denial.
- Owner and staff layouts at 768px, 390px, and 320px without horizontal overflow;
  desktop views and mobile edit dialog/Escape behavior.
- No JavaScript runtime errors in the monitored Owner and staff flows. Expected
  anonymous, deliberate validation, and forbidden-resource responses are not
  treated as application failures.

Initial logo test fixtures needed the correct multipart request and a
transactional streaming-response lifecycle. An additional NaN test was changed
to raw SQL because Django rejects NaN before database execution. Those test
issues were corrected; no failed checks remain. Production hosting, HTTPS
traffic, shared media storage, load testing, and GitHub Actions were not run.

## Running local preview

Frontend: **http://localhost:5174/**.
Phase 3 backend readiness: **http://127.0.0.1:8002/api/v1/health/ready/**.

The previous Django preview on 8000 runs without auto-reload and is preserved.
The Phase 3 process uses 8002, with the ignored `frontend/.env.local` proxy
pointing at it. Port 5173 belongs to another application and was preserved.
The shared Vite default still targets 8000 for other developers. Servers remain
running for review; these are computer-local URLs, not a hosted deployment.

PostgreSQL: isolated `rms_frontend_development` on 127.0.0.1:55440. Browser tests
created one clearly labeled `RMS Preview Kitchen` profile, one category/item,
and one active table through real APIs. They are review data in that local
database, not production data or fixtures automatically seeded by the product.
Existing two preview accounts and their credentials were preserved. Private
login details remain in ignored `.local/preview-credentials.txt`.

Startup/configuration: [frontend guide](../frontend/README.md) and
[backend guide](../backend/README.md). Private environment files, credentials,
media, database files, logs, browser state, dependencies, and build output stay
ignored. No credentials or private artifacts are intended for Git.

## Limits and next review

Phase 3 is a modular monolith for one restaurant. Occupancy and menu availability
are manually maintained; no orders, reservations, cashier approvals, kitchen
workflows, bills, payments, printing, inventory, analytics, tenancy, memberships,
or subscriptions were implemented. Read lists are ordered arrays with client
filters; there is no pagination, push synchronization, or collaborative draft
merge. Database constraints and row locks protect stored invariants; concurrent
form drafts use the latest submitted values. Refresh for other-device changes.

The publication commit message is
`feat(rms): implement restaurant menu and table management`. Review the feature
branch and its stacked PR; merging requires separate approval. Phase 4 (orders
and cashier approval) remains unstarted and requires explicit approval.
