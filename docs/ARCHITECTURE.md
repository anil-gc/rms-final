# Architecture

Current scope: accounts, authentication, a single restaurant profile, menu
catalogue, and physical tables for one location in Nepal, with a React client.
Phase 4 adds table dining sessions, submitted batches and Cashier approval.
Kitchen, billing, and inventory remain empty app boundaries.

Planning review: 2026-10-25 (Asia/Kathmandu). The sections describing Phases
1-3 below reflect implemented code. Sections marked planned describe future
contracts only. The expanded eleven-phase sequence is in [the roadmap](ROADMAP.md).

Phase 4 implementation now follows [PHASE_4.md](PHASE_4.md): separate dining
sessions and one-to-one orders, immutable batches/lines, attributable audit
events, explicit Waiter/Cashier actions, submission idempotency and PostgreSQL
row locks/constraints. Future-module sections below remain plans. The earlier
order-boundary proposal is retained as design history; cancellation, kitchen,
settlement, payments and room operations were not implemented in Phase 4.

## Module boundaries

| Module | Responsibility | Implemented |
| --- | --- | --- |
| `config` | Environment-specific settings and central v1 routing | Yes |
| `core` | Operational probes and shared authenticated API behavior | Yes |
| `accounts` | Users, credentials, sessions, account access rules | Yes |
| `restaurants` | Singleton profile, bounded logo uploads, physical tables/occupancy | Phase 3 |
| `menu` | Categories, decimal prices, availability, archiving | Phase 3 |
| `orders` | Dining sessions, orders, immutable submissions, audit and Cashier approval | Phase 4 |
| `kitchen` | One Chef's preparation/ready status in Phase 5 | Skeleton |
| `billing` | Invoices, payment records, cashier printing in Phase 6 | Skeleton |
| `inventory` | Stock and movements in Phase 7 | Skeleton |
| `rooms` | Optional hotel rooms, reservations, stays and folios in Phase 8 | Planned; app absent |
| `room_ordering` | Hotel-room QR credentials, guest sessions and intake in Phase 9 | Planned; app absent |

This is a modular monolith: one Django service, one PostgreSQL database.
Serializers validate API inputs, views enforce permissions and HTTP behavior,
services coordinate credential mutations, and models own stored identity and
hash behavior. No generic repository, microservice, or tenant abstraction is
introduced. Use `settings.AUTH_USER_MODEL` for future model relationships.

## Identity storage

`accounts.User` retains Django's existing User table and identifiers. Phase 2
adds `role`, `pin_hash`, `must_change_pin`, and `auth_version`. Allowed roles are
Owner, Manager, Cashier, Waiter, and Chef. An empty legacy role is retained so
old accounts are not silently promoted. Empty-role users receive no account
API privileges, even if they are Django superusers. A conditional PostgreSQL
unique constraint permits one Owner per deployment; a check constraint rejects
unknown roles. No restaurant/membership foreign key is introduced.

`accounts.LoginRateLimit` stores an HMAC bucket key, attempts, and window start.
It never stores raw usernames/IPs or credentials. Its unique key plus
`select_for_update()` inside a transaction serializes budget admission across
workers. Successful checks refund only their account attempt in the same
window; earlier failures remain counted and network attempts are not refunded.
Cleanup removes old buckets using `purge_login_limits`.

`django_session` is the existing Django session store. The browser/native client
holds only an opaque session cookie. Sessions expire server-side and are
deleted on logout. Password/PIN, role, active-state, forced-change-state, and
version changes alter the session authentication hash. Self-service credential
changes preserve only the current session via Django's built-in helper;
other sessions become invalid on their next request.

## Authentication and authorization

Owner uses a validated password of at least 15 characters. Staff use username
and newly assigned four-digit PINs. PINs must be strings so leading zeros are
preserved; obvious
repeated/sequential choices are rejected. They are HMAC-peppered with a
separate environment secret before salted Argon2 hashing. Staff have unusable
Django passwords and cannot use password login. Owner cannot use PIN login.

The 2026-10-27 update leaves legacy six-digit hashes/sessions untouched and
offers explicit legacy login/current-PIN inputs until users change or Owner
resets those credentials. New credentials are always four digits. PIN checks
are limited to three attempts per account per 15 minutes; Owner passwords
retain five, with the existing shared bucket and IP limits. No migration or
hashing change is required. See [transition details](AUTHENTICATION.md).

`AccountBackend` protects both API authentication and standard Django admin
password login with shared database budgets. No fallback unthrottled backend
is enabled. Login errors are generic. Unknown/disabled identities also perform
an expensive hash. PINs are passed to Django's authentication signals under
the redacted `password` key. Credentials are write-only API fields.

Admin's built-in self-password-change form checks passwords directly rather
than calling `authenticate()`. A small account middleware reserves the same
database budget before that form executes and refunds successful changes.
Its position after authentication and CSRF middleware preserves both checks.

DRF defaults require a provisioned, active user with a completed temporary PIN
change. Only CSRF bootstrap, login, and health probes are public. All unsafe
account requests require CSRF even before login. Authentication responses and
account records use `Cache-Control: no-store`.

| Permission | Allowed roles after PIN change |
| --- | --- |
| `IsOwner` | Owner |
| `IsOwnerOrManager` | Owner, Manager |
| `IsCashier` | Cashier only |
| `IsWaiter` | Waiter only |
| `IsChef` | Chef only |

Owner has no implicit override for cashier-only permissions. Role permission
classes support action-specific Phase 4 ordering; no printing, kitchen or
inventory endpoint exists yet. Only Owner may list/create staff, reset staff
PINs, or deactivate/reactivate staff. These writes require Owner password
confirmation. No API can create an Owner, change roles, set Django privilege
flags, delete users, or register publicly. Account admin is read-only and
excludes both credential hashes, preventing a second staff-creation path.

## Security and deployment boundaries

The API contract is cookie/session based for both React and Flutter. There is
no token issuance. Production requires HTTPS, secure cookies,
explicit hosts, strong separate secrets, and PostgreSQL TLS. SameSite=Lax is
retained; plan same-site frontend/API hosting. Browser cross-origin cookie use
requires explicit CORS credentials and origins. Do not trust arbitrary
forwarded-IP headers. MFA, public account recovery, deployment monitoring, and
edge abuse controls are not implemented in this phase.

The existing `0001_initial` migration is unchanged. New migration `0002` adds
fields/constraints and the rate-limit table without replacing or deleting
existing users. Old sessions are invalidated by the new backend/session hash;
operators should expect to sign in again. Verify migrations on a copy of any
shared database before a separately approved deployment. Local verification
uses a dedicated PostgreSQL cluster and generated test credentials.

Future extensibility comes from app boundaries and explicit permissions.
Multiple branches, tenancy, subscriptions, and memberships are out of scope;
they require a separate approved architecture rather than dormant tables now.

## React frontend

`frontend/` is an independent React/TypeScript application built with Vite,
Tailwind CSS, and React Router. `src/lib/api.ts` centralizes the existing
`/api/v1/` transport, with account methods and `src/lib/workspace.ts` for
Phase 3 contracts. `src/auth/` owns session discovery, role guards,
and temporary-PIN routing. `src/pages/` contains login, overview, staff,
profile, required-PIN, restaurant, menu, and table screens; `src/components/` supplies shared controls,
dialogs, and responsive navigation. Hooks coordinate mutations, cooldowns,
and workspace reads. Phase 3 adds domain tables without changing the account
models, authentication backend, credential lifecycle, or existing migrations.

The server remains the authority for permissions. Route guards prevent
accidental navigation, while every API operation uses Django's existing
session/CSRF enforcement. A 403 triggers an identity recheck rather than an
assumption that a role/CSRF denial means logout. Network failures have a
reconnect state. An in-memory request revision prevents an older identity
response from replacing a newer login/logout result. Session checks run on
focus, visibility, and a one-minute interval; BroadcastChannel announces
changes across tabs without sending credentials.

PINs/passwords exist only in submitted form state and are cleared after API
attempts. The masked CSRF token stays in memory, including its rotated value
after login. No credentials are persisted in browser storage. Phase 4 uses
sessionStorage only for an uncertain submission's item IDs, quantities and
idempotency key, scoped to user and order, with in-memory fallback. Mutations are
never automatically replayed after CSRF or network errors. A required PIN
change allows only identity, PIN change, and logout in the client and backend.

During development the browser calls relative `/api` paths through Vite's
proxy. Django must trust the exact browser origin for CSRF (the Origin header
is retained). Production should serve the built SPA with history fallback
and reverse-proxy `/api/` to Django on the same origin; Vite is not the
production application server. See [frontend setup](../frontend/README.md).

## Phase 3 domain boundaries

`restaurants.Restaurant` uses a fixed primary key and database check constraint
to permit exactly one configured profile. Setup uses an INSERT, so repeated
or racing setup requests cannot overwrite existing data. It can be inactive
without locking administrators out of sign-in or profile editing. Currency
is constrained to NPR; daily hours use Nepal local time and can cross midnight.
No profile is seeded automatically and no user membership/restaurant key was added.

`restaurants.DiningTable` belongs to that profile. Capacity is 1–50, and manual
occupancy is available/occupied. An inactive table must be available. There are
no reservations. Phase 4 now marks a table occupied when opening a session and
guards manual release/archive while that session is open.

`menu.Category` belongs to the profile; `menu.MenuItem` belongs to a category.
Foreign keys use PROTECT. Names are case-insensitively unique (items within
their category); archival retains names and identifiers. Prices are positive,
bounded two-place decimals. Effective availability combines item active/
available, category active, and restaurant active, without rewriting any price.

All provisioned users with completed PIN changes can read the workspace.
Owner and Manager can create/edit/archive records and manage the logo. Other
staff only receive active tables/categories/items; unavailable active items
remain visible, and an archived category hides its items. There is no hard
delete API for domain records. Account staff management remains Owner-only.
Workspace mutations preserve the existing cookie/CSRF enforcement and use
row locks for updates; database constraints reject conflicting writes. Form
edits use the latest submitted values; collaborative draft merging/live updates
are not implemented. Refresh to read another administrator's changes.

`core/api.py` supplies strict model input, no-store responses, read/write role
selection, and common list/create/retrieve/PATCH behavior. App serializers own
field validation; model constraints enforce stored invariants. The small
restaurant service enforces the setup prerequisite for categories and tables.
Domain admin registrations are read-only so validation is not duplicated in
an alternative writable admin path.

Logo uploads use a dedicated multipart endpoint, leaving authentication JSON
parsers unchanged. A 2 MB / 2048px bound and raster decode/re-encode accept PNG,
JPEG, or WebP and store generated PNG names with metadata stripped. Delivery
uses the protected API, not a public media URL. Replaced files are deleted
after commit. Persistent shared media storage and edge request limits are
deployment concerns for a later approved phase. See [the API contract](PHASE_3.md).

## Order and settlement boundaries (planned)

Keep one Django process boundary and one PostgreSQL database. Cross-app
business operations call explicit domain services inside transactions; no
message broker, microservice, generic repository, tenancy or SaaS layer is
needed. Establish a consistent lock order (table/stay, order, batch/line,
folio/payment as applicable) and database uniqueness constraints for races.

| App | Owns | Uses through defined services/contracts |
| --- | --- | --- |
| `orders` (Phase 4) | Table visits/orders, submission batches, immutable line snapshots, approval/cancellation and order events | Existing `restaurants`, `menu`, `accounts`; later approved-line query for kitchen |
| `kitchen` (Phase 5) | Preparation transitions and Chef work queries; service/delivery event contract | Approved `orders` lines only; never decides cashier approval |
| `billing` (Phase 6) | Invoice snapshots, Decimal totals/rounding, unique numbers, payment ledger, receipts and print/reprint attempts | Approved non-cancelled order amounts; later typed room-folio settlement input |
| `inventory` (Phase 7) | Stock units, movements and adjustments | Explicit order/recipe consumption contracts added when approved; no stock logic in menu serializers |
| `rooms` (Phase 8) | Feature setting, rooms, availability, reservations, stays and folio charge allocations | Billing payment/receipt services; later accepts delivered-food posting references |
| `room_ordering` (Phase 9) | Room QR credential lifecycle, guest sessions, rate limits and intake authorization | Rooms' active-stay validation, menu reads, order submission/approval, kitchen and folio services |

Keep dependencies explicit and avoid circular module imports. Order services
must not depend on `room_ordering`. In Phase 4, keep table-specific validation
at the table entry point, separate from batch/approval services. When Phase 9
is authorized, add an explicit room origin and constraint requiring exactly
one table visit or room stay; do not create fake dining tables for rooms or
speculatively register hotel apps now. A narrow orchestration service can
coordinate delivery and folio posting in the same database transaction.
Billing owns payments and receipts; rooms owns stay charge allocation.
Neither keeps a competing payment balance.

Approval belongs to each submission batch/line, not a boolean on the whole
order. Additions and quantity increases create new pending lines. Approved
lines retain their price/name snapshots and decision history when menu data
changes. Preparation, served/delivered, payment and closure states are
independent. Use `settings.AUTH_USER_MODEL` for actors and retain attributable
audit events. Audit credential/token values must never be stored.

The current workspace mixin grants writes to Owner/Manager. New order actions
need explicit Waiter/Cashier permissions and object-level scope; do not reuse
that write policy. Phase 4 must also guard existing table PATCH/archive routes:
a manual available-state edit must not bypass an open order or paid closure.
Preserve Phase 3 validation for tables without order involvement and add
regression tests for the changed interaction. See the [Phase 4 plan](ROADMAP.md#recommended-phase-4-implementation-plan-approval-required).

## Phase 6 receipts and local printing (planned)

Receipt content: restaurant name/contact/address and snapshotted information,
unique receipt number, itemized quantities/unit prices/amounts in NPR,
subtotal, applicable tax and discount breakdown, total, payment status and
method, Nepal-local date/time, and Cashier identity. Keep server Decimal
calculation and rounding authoritative; browser number formatting is display
only. Confirm tax/fiscal requirements separately before implementation; no
rate or compliance claim is assumed here.

Generate browser print and, where practical, PDF output from the same
immutable invoice snapshot. A reprint reuses the original number, amounts and
payment record, identifies itself as a copy, and records actor/time/reason.
Only Cashier may generate/print/reprint restaurant bills. Creating or retrying
a print job never creates another invoice/payment or closes a table twice.
A print-dialog return or spool acceptance is not proof that paper printed;
record attempted/queued/confirmed/failed/unknown as the integration permits.

Practical options researched on 2026-10-25:

| Integration option | Fit and limits | Planned decision |
| --- | --- | --- |
| Browser print via installed OS driver | `window.print()` opens a dialog; paper size, margins and printer choice depend on browser/driver | Start with an 80mm print stylesheet and PDF fallback; verify on the actual cashier workstation |
| Local bridge such as QZ Tray | Installed workstation component can send raw printer commands and PDF/HTML; silent operations need signed messages | Evaluate only if one-click/raw printing is required; review installation, certificate/licensing and maintenance costs |
| Vendor network/browser SDK | Epson ePOS and Star WebPRNT support specific models/interfaces, not every USB/LAN printer | Optional adapter after exact hardware/firmware and HTTPS/LAN compatibility testing |
| Direct WebUSB | Limited browser availability, secure-context and device permissions | Not the universal baseline for deployment |

Recommendation is an architectural choice based on those documented options,
not a tested hardware integration. Keep rendering separate from printer
adapters. Before selecting an adapter, record exact model, USB/Ethernet/
Bluetooth interface, OS/driver, ESC/POS or vendor command language, printable
width (80mm roll is not necessarily 80mm of print area), DPI, cutter support
and fonts/encoding. Test long menus, totals, Nepali glyphs or raster fallback,
margins, disconnect/paper-out, lost acknowledgements, repeated clicks, safe
reprints and the PDF fallback. Do not install a bridge or add a printing
dependency in this documentation task.

For a bridge, keep signing keys server-side, allowlist the configured
printer/origin, and authorize invoice-bound jobs. Never expose a generic
raw-command signing endpoint. A hosted Django service cannot directly reach
a USB printer attached to a cashier's computer; choose an installed local
component or an appropriately supported network path when needed.

Sources reviewed (vendor/browser documentation):

- [MDN: Window.print](https://developer.mozilla.org/en-US/docs/Web/API/Window/print)
  documents the browser print dialog.
- [QZ Tray: getting started](https://qz.io/docs/getting-started) documents the
  installed bridge and printing options; [message signing](https://qz.io/docs/signing)
  explains the requirement for removing approval pop-ups.
- [Epson ePOS SDK for JavaScript](https://download4.epson.biz/sec_pubs/pos/reference_en/epos_js/index.html)
  documents the vendor API; check its supported model/interface list.
- [Star WebPRNT interface table](https://star-m.jp/products/s_print/sdk/webprnt/manual/en/_interfaceTable.htm)
  distinguishes LAN, Bluetooth and USB support by model.
- [MDN: WebUSB](https://developer.mozilla.org/en-US/docs/Web/API/WebUSB_API)
  describes browser availability and HTTPS constraints.

## Optional hotel app boundaries (planned)

Phase 8 creates a separate `apps.rooms` app with additive migrations. Keep the
feature's stored settings in that app (a singleton linked to the existing
restaurant is a suitable design), default Hotel Room Management to OFF, and
allow only Owner to change it. Return a server-derived capability to the
client so OFF hides hotel navigation and management screens; both the API
entry point and the service layer must also reject disabled operations.
Hiding links alone does not protect APIs. Preserve all rooms/stays/folios
when OFF; re-enable in the same software installation.

Recommend rejecting a switch to OFF while active stays, unresolved orders,
or unsettled folios exist, with clear reasons. Define an explicit operational
reconciliation path before implementing any override; never strand financial
records or delete data to disable the module. Serialize setting changes with
check-in, guest ordering and checkout so a concurrent request cannot bypass
the disabled state. Invalidate guest sessions on disable; enabling does not
resurrect revoked sessions.

Room status values are Available, Reserved, Occupied, Cleaning, Maintenance.
A current status is not the reservation calendar: store dated reservations
separately and enforce non-overlap for each room (PostgreSQL exclusion
constraints or a locking/constraint design reviewed in Phase 8). Check-in
creates one active stay and folio; checkout validates outstanding activity,
settles combined charges through billing, closes the stay, revokes guest
access and normally moves the room to Cleaning. Use explicit services for
availability and transitions. Room charges and food charges remain separately
traceable within the same folio.

## Room QR access and ordering (planned)

Phase 9 creates `apps.room_ordering`. QR ordering applies only to hotel rooms;
there is no table QR endpoint or menu entry. Keep staff session/PIN
authentication unchanged. Guest access is a separate, narrowly scoped
room-ordering capability; do not make the entire existing staff API public.

Approved guest sequence:

1. Each room has a unique QR credential. Check-in activates ordering for the
   active stay automatically; the guest supplies no PIN.
2. Scan opens the browser menu. A validated room/stay credential exchanges for
   a short-lived, scoped guest session; subsequent writes use CSRF protection.
3. Guest selects available items and submits a batch. Server binds it to the
   active room/stay and determines prices; client room IDs, prices and roles
   are never trusted.
4. Reception/Manager receives and accepts or rejects the batch. Acceptance
   reuses order approval services with an explicit room-origin permission;
   the table Cashier approval rule remains intact. Only accepted items enter
   kitchen work.
5. Kitchen prepares food; authorized staff record delivery. Delivered food
   posts to that active stay's folio exactly once.
6. Checkout collects combined room and food charges through billing and
   disables ordering/revokes all guest sessions for that stay atomically.

Currently the only roles are Owner, Manager, Cashier, Waiter and Chef.
Reception is not implemented. Recommend Manager handles reception initially.
Any dedicated Reception role requires separately reviewed additive role/
constraint migration, staff validation, permission matrix and frontend changes
in a later approved phase; do not silently grant reception powers to all staff.

Protections and unresolved product choices:

- **Copied QR credentials:** a permanent printed bearer QR can be copied.
  Recommend a per-room credential version rotated for each stay and revoked
  on checkout; refresh the in-room QR display/card for the next guest. Store
  only a verifier/hash for opaque high-entropy credentials. Rotating guest
  sessions alone cannot stop an old QR copy creating a new session for a later
  stay. If permanent printed cards are required, review that residual risk
  explicitly before Phase 9; no mandatory guest PIN is introduced.
- **Stale access:** bind every session to room, active stay, credential version,
  expiry and enabled setting, checked again on menu/order writes. Checkout,
  disable, transfer or early termination revokes it. Tokens must not appear
  in logs, analytics or referrers; exchange the bootstrap token and clear it
  from the visible URL. Use HTTPS, secure cookies, no-store and restricted
  guest responses without guest identity, folio or staff account exposure.
- **Abuse:** rate-limit bootstrap and submissions, bound quantities/order size,
  reject inactive stays and guessed/forged credentials, and leave guest batches
  pending until an authorized acceptance. QR possession is a bearer capability,
  not proof of physical presence; approval and abuse controls remain necessary.
- **Duplicate submissions:** store stay-scoped idempotency keys and request
  fingerprints; identical retries return the original batch, while key reuse
  for a different payload conflicts. Additional batches need new acceptance.
- **Exactly-once charges:** rooms' posting service uses a database unique source
  reference per delivered line (or delivery event for partial deliveries).
  Lock the active stay, delivery and folio; create the delivery event and charge
  in one transaction. Repeated delivery callbacks return the original posting.
  Do not call this exactly-once network delivery; it is a constrained database
  effect, with explicit reversals instead of destructive charge edits.
- **Checkout races:** ordering, acceptance, delivery and checkout share stay/
  order locks and revalidate state. Checkout must resolve pending/preparing/
  undelivered orders and all charges before closing; a late event cannot post
  to a closed folio or attach to the next guest's stay.

## Compatibility risks and implementation standards

The modular monolith fits the expanded requirements without replacing
authentication or existing models. Remaining risks require deliberate work:

- Manual occupancy and Owner/Manager table PATCH can conflict with order
  lifecycle; Phase 4 now locks/validates both paths. Future closure must use
  the same table-first locking discipline.
- Current prices are mutable catalogue values. Snapshot order and invoice
  data so later edits/archiving cannot change history or receipt reprints.
- Workspace permissions are broader for reads and different for writes than
  order, kitchen, guest, folio and report rules. Use action/object permissions,
  not frontend visibility or inherited generic CRUD.
- Phase 4 now has an order audit ledger, submission idempotency and tested
  concurrency rules. Payment idempotency, reservations and guest capabilities
  remain future work with their owning phases.
- Workspace lists remain unpaginated. Phase 4 queues use 20-row pages; a
  single visit's full history is returned together. Other-device changes use
  manual refresh. Review history pagination before high-volume operation.
- Hotel OFF semantics, reception permissions, partial delivery/cancellation,
  reservation intervals and QR display rotation need contract review in their
  relevant phases. Avoid speculative hotels/guest tables in Phase 4.
- Production settings exist, but hosting, restore-tested backups, persistent
  protected media, monitoring, load tests and physical printer verification
  remain release work. Backend CI exists; frontend CI is not configured.

Use domain services, Decimal money, stable v1 schemas, consistent validation/
conflict errors, backend authorization, additive data-preserving migrations,
auditable important actions, bounded responsive feature screens and automated
tests for business invariants. Preserve existing React/session infrastructure;
organize new frontend modules by feature without moving working screens
unnecessarily. No new infrastructure/dependency is approved by this plan.
