# Phase 4: table ordering and batch approval

Implementation contract, 2026-10-25. Single restaurant; existing session/CSRF
authentication and five roles remain unchanged. This document is maintained
alongside implementation; final verification is in PROJECT_STATUS.md.

## Domain design

- DiningSession owns one table visit. A partial unique PostgreSQL constraint
  permits one open session per table. Only future billing may close it.
- Order is one-to-one with that session; it does not duplicate table ownership.
- OrderBatch owns a waiter submission, sequential within its order, initially
  pending, then approved OR rejected by Cashier. Rejection requires a reason.
- OrderLine holds immutable server-resolved item name, Decimal unit price,
  integer quantity (1-99), and exact Decimal total. A batch has 1-50 distinct
  menu items; duplicate item IDs are rejected rather than silently combined.
- OrderEvent records session/order creation, submission and review with actor
  and time; read-only through all ordinary application workflows.

Waiters share active restaurant sessions and their order histories so shifts
can collaborate. Only Waiter can open/join/submit; only Cashier can review.
Owner/Manager may read order history for oversight but cannot submit/review.
Chef receives no new order API access; future kitchen uses an approved-lines
query service, never the pending queue. No cancellation/closure is implemented.

Lock the table before opening/joining a session or submitting. Reuse the open
session; legacy manually occupied tables without sessions require an explicit
Owner/Manager reconciliation to available before opening. Submission locks the
order and menu rows, validates effective availability and snapshots current
prices server-side. Later menu changes do not reprice pending or reviewed
batches; Cashier approves the displayed submitted amounts or rejects the batch.
Review locks the batch; a second decision returns HTTP 409 and creates no event.
Submission and audit writes are atomic. Table status changes lock the same
table and reject release/archive if an open session exists.

Submission idempotency is scoped to order plus submitting user plus UUID key.
A canonical payload fingerprint detects conflicting reuse (409). Identical
retries return the original immutable batch, including after a lost response
or subsequent menu edits. A key is not a secret or authentication credential.
The composer retains a frozen uncertain submission and its key until an
explicit retry succeeds; it never automatically replays unsafe requests.
Tab-local sessionStorage holds only item IDs, quantities and the key, scoped
to user/order, to recover after reload. Storage failure falls back to memory.
No credential, guest data, price or item name is persisted there. Account
changes remount order screens. Definite 4xx failures allow correction; network
or server failures keep the submission frozen for an identical-key retry.

No kitchen preparation, payment, settlement, inventory or hotel operations
belong to this phase. Additive orders migrations must leave all prior tables,
IDs and migrations intact. New frontend code stays under features/orders.

## Implemented REST contract

All paths below are relative to `/api/v1/orders/`. Existing session cookies,
CSRF and completed-PIN checks apply. Responses and errors are no-store.

| Method/path | Roles | Result |
| --- | --- | --- |
| GET `/` | Waiter, Cashier, Owner, Manager | Open order summaries, paginated |
| GET `tables/<table_id>/active/` | Same read roles | `{"order": null}` or nested full order |
| POST `tables/<table_id>/open/` | Waiter | `{}`; 201 for new visit/order or 200 for the existing visit/order |
| GET `<order_uuid>/` | Read roles | Session/table identity, immutable batches/lines, review history, events and separate pending/approved/rejected totals |
| POST `<order_uuid>/batches/` | Waiter | UUID `idempotency_key` and `lines: [{menu_item: integer, quantity: integer}]`; 201 created, 200 identical retry |
| GET `batches/?status=pending&page=1` | Read roles | Queue/history; status is pending (default), approved, rejected or all |
| GET `batches/<batch_uuid>/` | Read roles | Submitted lines, exact total and review details |
| POST `batches/<batch_uuid>/approve/` | Cashier | `{}`; 200 terminal approved decision |
| POST `batches/<batch_uuid>/reject/` | Cashier | `{"reason": "..."}`; 1-500 non-whitespace characters, 200 rejected decision |

List responses use `{count, next, previous, results}`, 20 rows per page with
stable timestamp/UUID ordering. Clients construct page URLs from validated
filter/page state rather than following arbitrary links. Per-visit detail
contains all its batches/events. Actors expose only user IDs and usernames;
credentials, session secrets and internal request fingerprints are excluded.
Decimal money is serialized as two-place strings; IDs for sessions/orders/
batches are UUIDs, menu/table/user/line/event IDs keep their established types.

Validation errors use 400, authentication/role/CSRF denials 403 under the
existing session contract, missing resources/pages 404, invalid HTTP methods
405, and conflicting idempotency reuse/already-reviewed batches/legacy manual
occupancy/closed-session writes 409 with a `detail` message. Unknown or
read-only input fields are rejected. There is no PUT/PATCH/DELETE API for
orders, batches, lines or events. Browser retries of a Cashier decision receive
409 after a lost success response; refresh reveals the authoritative decision.

## Transactions, migration and immutability

`orders/0001_initial.py` adds only five order-domain tables, indexes and
constraints. It depends on existing menu, restaurants and swappable User
migrations and neither copies nor edits those domain records. Generated SQL
was reviewed before applying it to the new isolated Phase 4 development DB.
Tests also unapply/reapply only the orders migration in a disposable test DB
and check existing IDs, credentials, menu prices and table state survive.

All service writes include their audit event in `transaction.atomic()`;
simulated audit failures roll back the entire operation. Table/session opening
and submissions lock the table first; submissions then lock order/session,
menu items in ID order, categories in ID order, and restaurant activity.
Cashier reviews lock the batch. Future settlement must join this locking
protocol; no settlement service exists now.

The database enforces one open session per table, one order per session,
unique batch sequence/idempotency scope, coherent review metadata, bounded
positive prices/quantities, exact line totals and unique event kinds.
Line/event instance updates/deletes and queryset update/delete/bulk-update
are rejected; model inserts force INSERT. Admin is read-only. These controls
protect normal application workflows, not privileged direct SQL. Do not add
future bulk-upsert or maintenance paths that bypass the immutable contract.

`approved_lines()` is the future kitchen query boundary: only approved lines
of open visits. It exposes no Chef endpoint, preparation state or dispatch
side effect. No kitchen/billing/inventory models or migrations were added.

## Frontend and verification

- `/orders/waiter`: table cards, explicit session opening, shared active order,
  category/search menu browser, quantities/removal, exact integer-minor-unit
  subtotal, explicit submission and retry, batch history, status totals and
  manual table/menu/order refresh.
- `/orders/cashier`: paginated pending queue and reviewed history, table/waiter
  attribution, full immutable amounts, confirmation dialogs, required rejection
  reason and conflict refresh. Manual refresh avoids unnecessary polling.
- Existing shared session/CSRF transport, components, layout and PIN routing
  remain in use. Role-specific links and route guards complement API rules.
  Table management displays/locks occupancy and archive controls for open
  sessions, while server validation remains authoritative.

See [current results](PROJECT_STATUS.md) for exact counts and browser evidence.
New PostgreSQL cases include real two-thread/separate-connection races for
opening, duplicate/conflicting submissions, unique sequencing, two approvals,
and approve/reject contention. Functional tests cover permissions (including
superuser bypass attempts), CSRF, PIN restrictions, validation, immutable price/
name history, additional batches, audit rollback, constraints and migration
preservation. Frontend tests cover composition, snapshots, additional batches,
pending state, duplicate clicks, lost-response recovery/remount, approvals,
rejection, history, role navigation, PIN guards, errors and exact totals.

## Limits

No cancellation/withdrawal, closure, bill, payment, preparation or hotel API is
implemented. Open visits intentionally keep tables occupied until future
Phase 6 settlement; do not use Phase 4 for a production service requiring
table turnover. Empty visits cannot be closed through this phase's UI.
Legacy manually occupied tables need management reconciliation before opening.
Per-visit history pagination and collaborative composer merging are deferred.
An unsent draft is memory-only; an uncertain submitted request can recover in
the same tab when storage is available. If storage is cleared/unavailable,
inspect authoritative order history before recreating a lost request.
