# Project status

## Branch publication - 2026-10-27

The owner authorized committing and pushing the combined Phase 4 ordering
implementation, expanded planning documentation and four-digit PIN update
on `feature/order-management`. This supersedes the earlier no-commit/no-push
instructions in the historical snapshots below. No merge or pull request is
part of this authorization. Local verification passed 292 PostgreSQL backend
tests and 54 frontend tests, plus lint/format, configuration, migration and
production-build checks. Private preview credentials, environments, database
files and browser artifacts are excluded from publication. Branch publication
is not production deployment; remote CI results are separate from local checks.

## Four-digit staff PIN update - 2026-10-27

New staff creation, Owner PIN reset and self-service replacement now require
exactly four ASCII digits as strings, preserving leading zeros and rejecting
repeated/sequential choices. Login and current-PIN forms have an explicit
legacy six-digit option so existing hashes/users are not silently changed or
locked out. See [the transition plan](AUTHENTICATION.md#existing-six-digit-credentials-compatible-transition).

Argon2, pepper derivation, secure sessions, CSRF and role rules are unchanged.
PIN login/current-PIN verification now admits at most three failed/in-flight
attempts per account per 15 minutes, retaining shared database admission and
IP limits; Owner passwords retain five attempts. No schema/data migration
is needed or created. Legacy support has no automatic removal date.

All four known isolated Phase 4 staff accounts were explicitly transitioned
through the PIN-change API. Generated credentials were atomically updated in
ignored `.local/phase4-preview-credentials.json`. Preservation assertions
confirmed unchanged Owner credentials, IDs and restaurant/menu/order/audit
records. The older preview DB/environment was never opened. Prior Phase 4
staff sessions are invalidated by their explicit credential changes.

Fresh checks: **292 PostgreSQL backend tests passed**, including original
order/approval regressions, and **54 frontend tests passed across 8 files**.
Ruff lint/format (97 files), ESLint, Python dependency consistency, TypeScript/
Vite build, Django database/production configuration, migration drift/pending
and documentation checks passed. New tests cover leading zeros, weak/invalid
PINs, all credential forms, legacy hash/session preservation, safe transition,
session revocation and real concurrent enforcement of the three-attempt cap.

Verified local login: `http://localhost:5175/login/staff`, backed by the
isolated `127.0.0.1:8004` service and `rms_phase4_dev` on port 55444. Chromium
successfully signed in with a new four-digit Waiter PIN and opened Waiter
orders. Real HTTP checks also verified four-digit login/logout for Waiter,
Cashier, Manager and Chef, with order histories preserved and Chef access
still denied. These are local URLs, not a deployment.

The prior uncommitted Phase 4 work was backed up before this task in ignored
`.local/pin4-baseline-20261027-090427/`. Branch remains
`feature/order-management`; no commit, push, merge or future-phase work.

## Phase 4 implementation snapshot - 2026-10-25

**Phases 1-4 are implemented locally. Phase 5 has not started.** This section
supersedes the earlier planning-only snapshot preserved below.

### Git and preservation

- Workspace remains `C:\Users\anil gc\Desktop\rms-final`.
- Current branch: `feature/order-management`, created from fetched
  `origin/main` at `2a13d1819347e67da23f4b3b4c72fd2c92d0d94d`.
- Local `main` did not exist. Remote `main` contains Phase 3, and its tracked
  tree was identical to the starting Phase 3 branch (`5d9ffc0`). No pull,
  merge, rebase or reset was needed. The feature branch has no upstream set.
- The three existing modified docs were backed up byte-for-byte in ignored
  `.local/phase4-docs-baseline-20261025-151531/` before switching; hashes were
  checked after switching. Planning content is retained and updated locally,
  with the prior status report kept below. No stash/pop or overwrite from Git.
- All work remains unstaged/uncommitted. No push, PR or merge was performed.
  Authentication, user schema/IDs, old migrations, dependencies, the old
  `.env` files and the previous preview database were not modified.

Changed Git-visible files (31; all unstaged):

```text
README.md
backend/README.md
backend/apps/orders/admin.py
backend/apps/orders/migrations/0001_initial.py
backend/apps/orders/models.py
backend/apps/orders/serializers.py
backend/apps/orders/services.py
backend/apps/orders/urls.py
backend/apps/orders/views.py
backend/apps/restaurants/serializers.py
backend/apps/restaurants/views.py
backend/config/api_urls.py
backend/tests/test_health.py
backend/tests/test_orders.py
docs/ARCHITECTURE.md
docs/PHASE_4.md
docs/PROJECT_STATUS.md
docs/ROADMAP.md
frontend/README.md
frontend/src/App.tsx
frontend/src/components/AppLayout.tsx
frontend/src/features/orders/BatchCard.tsx
frontend/src/features/orders/CashierOrdersPage.tsx
frontend/src/features/orders/OrdersAccess.tsx
frontend/src/features/orders/WaiterOrdersPage.tsx
frontend/src/features/orders/api.test.ts
frontend/src/features/orders/api.ts
frontend/src/features/orders/orders.css
frontend/src/features/orders/orders.test.tsx
frontend/src/lib/workspace.ts
frontend/src/pages/TablesPage.tsx
```

### Backend and frontend delivered

`orders` now owns DiningSession, Order, OrderBatch, OrderLine and OrderEvent.
The additive `orders/0001_initial.py` adds their tables/indexes/constraints.
Existing physical tables, menu items and users remain their source records.
Server pricing is snapshotted at submission; later price/name edits cannot
rewrite submitted lines. Each new submission has a separate pending decision.
Batch review is terminal and Cashier-only; rejection requires a reason.

Domain services open/reuse a visit, submit with scoped UUID idempotency,
review under row locks, write audit events atomically, and expose approved
lines for future kitchen use. There is no cancellation, kitchen, payment,
closure or settlement service. Owner/Manager can read orders without gaining
Waiter or Cashier mutation privileges; Chef has no Phase 4 API access.

REST routes under `/api/v1/orders/` cover open order lists/details, active
table order, session opening, batch submission, paginated queue/history,
batch detail and approve/reject actions. See the exact [API contract](PHASE_4.md).
Existing table PATCH uses the same table lock as opening/submission and rejects
release/archive while an open visit exists. Table responses add read-only
`has_active_session`; UI occupancy/archive controls follow it.

`frontend/src/features/orders/` supplies typed API contracts, exact integer
minor-unit display arithmetic, shared batch cards, Waiter composition/history,
and Cashier queue/confirmation/history. Routes are `/orders/waiter` and
`/orders/cashier`, with role-appropriate navigation and the existing protected
route/session/CSRF layer. Unknown submission outcomes freeze the composer and
retain a user/order-scoped retry key plus item IDs/quantities in tab storage
(memory fallback); nothing is automatically replayed.

### Current quality gates

| Check | Result |
| --- | --- |
| PostgreSQL pytest | 260 passed: 201 baseline cases plus 59 order cases |
| Frontend Vitest | 44 passed across 7 files: original 22 plus 22 new cases |
| Backend Ruff lint/format | Passed; 96 Python files formatted |
| Frontend ESLint, TypeScript and Vite build | Passed |
| Python dependency consistency | Passed |
| npm installed dependency check and production audit | Passed; 0 production vulnerabilities |
| Django system/database checks | Passed |
| Migration SQL review/application/pending/drift | Passed against isolated Phase 4 development/test databases |
| Production configuration checks | Passed with strong generated secrets and required TLS; no deployment |
| Documentation/scope/security review | Passed: 33 local links/anchors across seven docs, eleven phases, clean Git whitespace; no generated credentials in Git-visible files |

The original foundation route-absence test now checks `/api/v1/kitchen/`
instead of `/api/v1/orders/`, since orders is intentionally implemented.
No regression case was removed. Actual PostgreSQL transaction tests use two
threads and separate connections for concurrent session opening, identical/
conflicting duplicate submissions, distinct submission sequencing, two
approvals and approve/reject races. Audit-failure tests verify rollback;
migration tests verify existing account IDs/credential hashes, menu and table
records survive applying orders schema. No sequential mocks are presented as
concurrency evidence.

### Isolated local preview

The new private development database is `rms_phase4_dev` on
`127.0.0.1:55444`. A separate disposable test database is created by pytest.
Generated Owner/Waiter/Cashier/Manager/Chef accounts and clearly labeled review
tables/menu exist only in that new development database. Their credentials
are in ignored `.local/phase4-preview-credentials.json`; no old credential was
reset or reused. Neither tests nor preview load the old preview's `.env`.

Frontend: `http://localhost:5175/`. Backend readiness:
`http://127.0.0.1:8004/api/v1/health/ready/`. Both readiness paths (direct and
through Vite) returned 200. These are local previews, not hosted deployments.
Startup commands and the exact isolated PostgreSQL restart path are in the
[frontend guide](../frontend/README.md#current-isolated-phase-4-preview-2026-10-25).
Do not launch another process if the corresponding port is already running.

Real Chromium verification through the Playwright CLI passed:

- Staff PIN login, Waiter navigation, table selection and explicit opening;
  the table changed to occupied without a second visit/order.
- Unavailable menu selection disabled; two Vegetable momo and one Milk tea
  submitted at exact total NPR 460.60, then composer cleared.
- Separate Cashier session received/confirmed Batch 1 approval and displayed
  attribution/time in reviewed history.
- Waiter added two Milk tea as Batch 2 (NPR 121.00) on that same visit;
  Batch 1 remained approved and unchanged while Batch 2 remained pending.
- Cashier rejection required a reason. After rejection and Waiter refresh,
  Batch 2 was rejected with attribution/reason and Batch 1 stayed approved.
- Both screens had no horizontal overflow at 320, 390, 768 and 1440px.
  Mobile Waiter and Cashier dialog screenshots were visually inspected in
  ignored `output/playwright/`.
- A read-only database assertion confirmed one visit/order, exactly two
  batches, intact original line snapshots, six audit events, two approved
  lines for future kitchen integration and occupied table state.

Expected anonymous `/accounts/me/` 403s and development-server reconnection
messages occurred during browser setup/rebuilds; they are not business-flow
success evidence. The documented scenarios use real browser requests and
PostgreSQL, not the frontend mocks. Browser checks did not simulate physical
printing, payment or production deployment.

### Remaining limits and next phase

No Phase 5-11 business feature was added. Sessions intentionally remain open
and tables occupied until a future approved settlement implementation;
Phase 4 alone cannot operate a complete production restaurant shift.
Legacy manually occupied tables need management reconciliation. Lists/queues
use manual refresh, with 20-row order/batch lists and unpaginated per-visit
history. Unsent drafts are memory-only. If uncertain-attempt tab storage is
cleared/unavailable, inspect order history before creating a replacement.
Application immutability/read-only admin does not constrain privileged direct
SQL maintenance. Frontend CI, production hosting/security/load/restore checks
and actual printers remain future work.

Phase 5 can consume `orders.services.approved_lines()` for approved open-visit
lines and add its own preparation/service transitions after separate approval.
It must preserve approval metadata, snapshots, role boundaries and the table-
first locking protocol. Stop after this Phase 4 review; no publication or
next-phase work is authorized.

## Preserved planning-only review (historical)

Verified review date: 2026-10-25 (Asia/Kathmandu).
Scope of this session: inspect the existing workspace and update planning only.
**Phases 1-3 are implemented; Phase 4 and later modules are not implemented.**
The expanded roadmap is approved for planning, not permission to implement,
publish or deploy future phases.

## Workspace and Git evidence

- Workspace: `C:\Users\anil gc\Desktop\rms-final`.
- Branch: `feature/restaurant-menu-tables`.
- HEAD: `5d9ffc013ec855f30d1ace328d6f9b043ee9c9c4`.
- Origin: `https://github.com/anil-gc/rms-final.git`.
- Initial working tree: clean, with no non-ignored untracked files.
- Live `git ls-remote --heads origin` and a metadata-only `git fetch origin`
  confirmed HEAD equals `origin/feature/restaurant-menu-tables` (0 ahead/behind).
- Remote frontend is now `df9eea0`, one merge commit ahead of HEAD, with the
  same tracked file tree. Its merge commit records PR #2.
- Remote `main` is `2a13d18`, four merge commits ahead of HEAD; its history
  contains Phase 3. This supersedes the older open/unmerged stacked-PR notes.
  No checkout, pull, merge or history rewrite was performed in this session.
- Local frontend/accounts/foundation branches retain their original tips;
  after fetch they are behind their corresponding remote refs by 2/2/7 commits.
  They were not moved.

The current branch's Phases 1-3 content is therefore already incorporated in
the fetched remote history. This is Git graph/tree evidence, not a fresh
GitHub PR API or Actions result. Remote CI/deployment state was not checked.

Only `docs/ROADMAP.md`, `docs/ARCHITECTURE.md` and this status file are changed
by this task. Changes remain unstaged and uncommitted. No push or merge.
Ignored local credentials, environments, preview records and existing database
directories were preserved. Verification creates only isolated ignored test
artifacts. No applicable `AGENTS.md` was found in the repository or ancestor
directories checked.

## Existing application structure and reusable features

Backend: `backend/config`, `backend/apps`, `backend/tests`, and pinned
`backend/requirements`. The service is Django/DRF with PostgreSQL, v1 REST
routing and an apps-based modular monolith.

| App | Verified implementation |
| --- | --- |
| `core` | Liveness/readiness probes; strict workspace input, role-based reads/writes, no-store responses and transactional updates |
| `accounts` | Custom User, Owner password/staff PINs, five roles, secure sessions and CSRF, login budgets, PIN/password lifecycle, Owner-only staff management and read-only admin |
| `restaurants` | One NPR restaurant profile, validated protected logo uploads, daily hours, physical tables with manual occupancy and archiving |
| `menu` | Categories/items, exact two-place Decimal prices, effective availability, protected relationships and archiving |
| `orders`, `kitchen`, `billing`, `inventory` | Registered AppConfigs with placeholder models/admin; no domain models, concrete migrations, APIs or screens |

Concrete domain migration files present in code: `accounts/0001_initial.py`,
`accounts/0002_loginratelimit_user_auth_version_and_more.py`,
`restaurants/0001_initial.py` and `menu/0001_initial.py`.
No migration file was changed. The current preview database's applied migration
state could not be queried; file presence does not establish database state.

Frontend: React/TypeScript, Vite, Tailwind, shared cookie/CSRF API transport,
session provider and protected routes, shared UI/dialogs, resource/mutation
hooks and typed workspace contracts. Screens cover Owner/staff login, required
PIN change, profile/credential change, account/team overview, Owner staff
management, restaurant profile, menu and tables. The overview uses real staff
records; it is not the Phase 10 sales/operations dashboard.

All provisioned PIN-ready staff can read permitted workspace records;
Owner/Manager mutate restaurant/menu/tables. Cashier, Waiter and Chef role
permission classes exist but their business workflows do not. Authentication,
existing app boundaries and working UI can be reused without replacement.

## Incomplete modules and expanded planning

Orders/approvals, kitchen preparation/service, invoices/payments/thermal
printing, inventory movements, hotel rooms/reservations/stays/folios, room QR
guest access, business reporting and final deployment readiness remain future
work. `rooms` and `room_ordering` do not exist and were not registered.

- [Roadmap](ROADMAP.md): eleven phases, current evidence-based states,
  restaurant approval flow, later-phase acceptance boundaries and a concrete
  eight-step Phase 4 plan.
- [Architecture](ARCHITECTURE.md): future service dependencies, room and folio
  ownership, Owner hotel ON/OFF behavior, room-only QR authorization, stale
  session/duplicate/checkout protection and sourced thermal-printer research.
- Phase 4 recommendation: order/batch/line/event records, one open table visit,
  server price snapshots, separate approval for additions, explicit role/object
  permissions, row locks/constraints and idempotent submit/decision services;
  then Waiter/Cashier screens and PostgreSQL/UI regressions. No future module
  was implemented.

## Checks performed in this review

| Check | Current result |
| --- | --- |
| Git status, branches, log/ancestry, live remote refs and fetched tree comparison | Passed; initial tree clean, active branch matches its remote |
| Django system check | Passed; no issues |
| Ruff lint and format check | Passed; 90 Python files formatted |
| Python dependency consistency | Passed |
| Frontend Vitest | 22 tests passed across 5 files |
| Frontend ESLint | Passed |
| TypeScript and Vite production build | Passed |
| Backend pytest against isolated PostgreSQL 18.4 | 201 tests passed in 38.09 seconds |
| Isolated Django database check and migration drift check | Passed; no system issues or migration changes detected |
| Production configuration check (`check --deploy --fail-level WARNING`) | Passed with generated secrets and TLS-required settings; no deployment |
| Documentation review | 10 local links/anchors checked; phases 1-11, Markdown fences/whitespace and three-file unstaged scope passed; `git diff --check` passed |

The configured development database is local `rms_frontend_development` at
`127.0.0.1:55440`. A read-only connection attempt returned `OperationalError`;
the existing preview cluster was not started or migrated. Its applied
migrations/data and frontend/backend preview availability are not verified in
this review. See the setup guides for historical local addresses; they are
computer-local development addresses, not a public deployment.

The fresh backend checks used a new ignored local PostgreSQL cluster on
`127.0.0.1:55442` with generated credentials and a disposable test database.
The suite exercised migrations in that isolated database; it was not run
against preview/production records. An initial test-runner output-capture
stall was corrected by logging to a file; the rerun passed all checks. Both
review-only clusters were stopped and the stalled runner was terminated.

The previous 2026-10-20 status recorded 201 backend tests, 22 frontend tests,
isolated migrations and desktop/mobile browser flows. Those browser,
identity-digest, HTTP preview and security dependency-audit results are historical;
they were not rerun here. Current checks above take precedence. No production
data, migrations or deployment were changed.

## Decisions, risks and next step

Keep the single-installation modular monolith and existing authentication.
Use new additive migrations only when a phase is authorized. Manual table
occupancy/PATCH must be reconciled with open orders; current Owner/Manager
workspace write permissions must not leak into Waiter/Cashier workflows.
Snapshot mutable prices and receipt details, and add audit/idempotency records
with their owning phase.

Hotel OFF needs API/service enforcement, preserved data and a safe policy for
active stays/unsettled folios. Reception is not a current role; Manager can
initially perform reception duties subject to explicit permissions. A copied
permanent QR cannot be secured by session revocation alone: the recommended
per-stay QR rotation requires a refreshed in-room card/display. No guest PIN
or table QR ordering is planned. Exactly-once food charges require a unique
delivery source reference and atomic delivery/folio posting.

Physical 80mm printer model/interface/driver testing is still required; vendor
SDKs and local bridges are conditional options, not installed integrations.
Production media, backup/restore, monitoring, load/security review and hosting
remain Phase 11 work. Existing backend CI is configured; frontend CI is absent.

Next step: review the [Phase 4 plan](ROADMAP.md#recommended-phase-4-implementation-plan-approval-required)
and authorize that phase separately. Stop here; no Phase 4 code, new app,
schema/authentication change, commit, push or merge is part of this session.
