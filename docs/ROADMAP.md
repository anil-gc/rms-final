# Development roadmap

Reviewed: 2026-10-25 (Asia/Kathmandu). Source of truth: the existing local
workspace at commit `5d9ffc0`. This is one standalone restaurant installation,
optionally extended with hotel rooms in the same deployment. Keep Django/DRF,
PostgreSQL, React/TypeScript, Vite, and Tailwind; use an apps-based modular
monolith. Multiple restaurant locations, multi-tenancy, SaaS billing, and table
QR ordering are out of scope.

## Approved sequence and verified state

| Phase | Scope | Local implementation state |
| --- | --- | --- |
| 1 | Project Foundation | Implemented: settings, PostgreSQL, modular apps, v1 routing, probes, tests and backend CI configuration |
| 2 | Authentication & Staff Management | Implemented: Owner password, staff PINs, five roles, sessions/CSRF, rate limits, Owner staff management; React integration also implemented |
| 3 | Restaurant, Menu & Tables | Implemented: singleton profile/logo, categories/items, decimal NPR prices, availability, manual occupancy and archiving; backend and React tests exist |
| 4 | Waiter Orders & Cashier Approval | Implemented locally: dining sessions, immutable submissions, Cashier decisions, audit, idempotency and Waiter/Cashier screens; see PHASE_4.md |
| 5 | Kitchen Management | Not started; `kitchen` is a registered skeleton |
| 6 | Billing & Thermal Receipt Printing | Not started; `billing` is a registered skeleton |
| 7 | Inventory Management | Not started; `inventory` is a registered skeleton |
| 8 | Optional Hotel Room Management | Not started; future `rooms` app does not exist |
| 9 | Room QR Ordering | Not started; future `room_ordering` app does not exist; depends on Phase 8 being enabled |
| 10 | Owner Dashboard & Reports | Not started; existing account/team overview is not business reporting |
| 11 | Final Testing, Security & Deployment | Not started as a release phase; foundation security/configuration and CI checks already exist |

These states come from local models, routes, migrations, screens, and tests,
not phase names or remote branch labels. See [current verification](PROJECT_STATUS.md).
The former Phase 8 reports and Phase 9 deployment work move to Phases 10 and 11.
Security, audit records, and tests belong in each phase, not only at release.

## Restaurant workflow across Phases 4-6

1. Waiter selects an active restaurant table, selects available menu items,
   and submits an order batch.
2. Cashier receives the batch and approves or rejects it. Pending/rejected
   lines are never visible in kitchen work queries.
3. Approved lines reach the kitchen in Phase 5. Chef marks preparation/ready
   status; Waiter records service.
4. Additional items join the same active table visit/order as a new batch.
   Only those new lines require approval; previous decisions remain intact.
5. Cashier generates the final bill in Phase 6, prints an itemized receipt,
   records payment, and closes the table visit transactionally.

Keep approval, preparation, service, billing, and payment states separate.
Approval is not payment or table closure. Role rules are enforced server-side;
Owner has no implicit bypass of Cashier, Waiter, or Chef actions.

## Recommended Phase 4 implementation plan (approval required)

This earlier proposal is retained as design history. Phase 4 has since been
authorized and implemented; [the final contract](PHASE_4.md) takes precedence
where details differ. Cancellation/withdrawal is not implemented: batches are
pending, approved or rejected. DiningSession is separate from its one-to-one
Order. Phase 5 is not authorized.

1. **Confirm the contract.** Define permitted transitions, ownership/read scope,
   whole-batch approval/rejection, cancellation reasons, quantity limits, and
   stale-client conflict responses before implementation. Recommend Waiter
   submit/add and withdraw pending batches; Cashier decide pending batches and
   authorize cancellations of approved lines before preparation. Phase 5 must
   reject simple cancellation once preparation starts and define its own flow.
2. **Add order-owned records.** Propose `Order` for one table visit,
   `OrderBatch` for each submission/decision, `OrderLine` for item, quantity,
   name/unit-price snapshots and notes, and immutable `OrderEvent` records for
   actor, timestamp, decision and reason. Names are provisional. Use protected
   references to existing tables/menu/users, with additive migrations only.
3. **Protect submission.** Within `transaction.atomic()`, lock the table and
   active order, validate restaurant/table/category/item availability and bounded
   quantities, and obtain prices from the server. Use a partial unique constraint
   for one open order per table. Mark occupancy through the same business service.
   Existing occupied tables without orders require explicit staff reconciliation;
   do not fabricate historical orders or silently clear their status.
4. **Protect decisions and retries.** Lock batch/lines, allow only legal state
   transitions, and make an approved batch immutable to ordinary edits. New items
   or increased quantities create a new pending batch. Store scoped idempotency
   keys plus request fingerprints for submission and decisions: the same request
   returns its original result; a changed payload using the same key conflicts.
   Concurrent approve/reject requests must produce one decision/event.
5. **Preserve amounts.** Snapshot server menu prices at submission using Decimal
   and decimal-string API values. Show price/availability changes to the Cashier
   at approval; do not silently reprice or edit previously approved lines.
   Recommend rejecting and resubmitting if a new price must be used. Tax,
   discount, invoice, and payment calculations remain Phase 6 work.
6. **Expose narrow APIs.** Add versioned list/detail/submit/append/approve/reject/
   cancel contracts under `/api/v1/`; specify schemas, status/error codes,
   permissions and object access. Reuse existing sessions, CSRF, PIN readiness,
   validation conventions and no-store behavior. Do not inherit the workspace
   mixin's Owner/Manager mutation policy for ordering actions.
7. **Add React order features.** Reuse the transport and protected layout; group
   new work under `src/features/orders/`. Provide a mobile Waiter table/cart flow
   and Cashier pending queue, line/batch status, empty/loading/error states,
   deliberate retry and refresh. Start with bounded polling and visibility
   refresh; no websocket infrastructure is required. Preserve draft/idempotency
   identity across uncertain submission outcomes without storing credentials.
8. **Verify and review.** Test all five roles, anonymous/inactive/temporary-PIN
   denial, CSRF, object access, validation, price snapshots, separate additional
   approvals, retries, concurrent decisions/submissions and table edit/archive
   bypasses against PostgreSQL. Run existing backend/frontend regressions and
   meaningful desktop/mobile flows with isolated records. Update the API contract
   and status, report results, then stop for review.

Phase 4 must expose a service/query boundary for approved lines so Phase 5 can
consume them later. It must not implement preparation, printing, billing,
payments, inventory, rooms, guest endpoints, or business reports. Until Phase 6,
do not represent a manual table-status edit as a paid/closed order.

## Later-phase delivery boundaries

- **Phase 5:** Chef sees approved items only, moves individual lines through
  preparing/ready, and Waiter records served status. Record actors and guard
  transitions and cancellation races. Retain approval history.
- **Phase 6:** Consolidate approved, non-cancelled lines for a table visit;
  define Decimal rounding, discounts and applicable tax configuration, unique
  receipt numbers, payments and atomic settlement/closure. Tax rates and fiscal
  requirements need separate current verification before implementation. Plan
  80mm printing, safe reprints and printable PDF from one immutable bill snapshot.
  See [printer research and selection criteria](ARCHITECTURE.md#phase-6-receipts-and-local-printing-planned).
- **Phase 7:** Owner/Manager stock intake, consumption, adjustments and movement
  history with explicit units, negative-stock policy, transaction constraints
  and audited reasons. Do not silently equate menu availability with stock.
- **Phase 8:** Separate `rooms` app for rooms, availability, reservations,
  check-in/out, stays and folios. Room statuses: Available, Reserved, Occupied,
  Cleaning, Maintenance. Owner-only Hotel Room Management ON/OFF setting; OFF
  hides hotel UI, rejects disabled hotel operations server-side and preserves
  data. Re-enabling uses the same installation. Resolve active-stay/folio
  obligations before disabling. See [app boundaries](ARCHITECTURE.md#optional-hotel-app-boundaries-planned).
- **Phase 9:** Separate `room_ordering` app for hotel-room QR credentials, guest
  sessions and order intake, reusing menu/order/kitchen/billing services.
  Check-in activates ordering; no guest PIN. Reception/Manager accepts new
  submissions, approved lines reach kitchen, delivered food posts to the active
  stay folio exactly once, and checkout settles combined charges and revokes
  access. Address QR copying, stale sessions, duplicate submission/posting and
  checkout races as specified in the architecture. No table QR ordering.
- **Phase 10:** Owner operational dashboard and reports derived from real order,
  payment, inventory and optional hotel records. Enforce report permissions,
  Nepal-local date boundaries, reconciliation and bounded/exportable queries;
  never fabricate statistics.
- **Phase 11:** End-to-end, permission, security, concurrency, performance and
  accessibility review; migration rehearsal, persistent media, HTTPS, backups
  and restore tests, monitoring, operations docs and deployment/pilot checks.
  No commercial-readiness claim until these checks are verified.

Each phase starts with inspection and a small plan, preserves working features
and data, documents stable contracts, tests its business invariants, and stops
for review. Do not automatically begin another phase, push, merge, rewrite
history or change applied migrations. The earlier documentation-only session
ended before implementation. A later explicit request authorized Phase 4
locally; it does not authorize Phases 5-11, commits, publication or merging.
