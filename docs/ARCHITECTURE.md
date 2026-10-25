# Architecture

Current scope: accounts and authentication for a single restaurant operating
from one location in Nepal, with a React client for those existing APIs.
Phase 1 is complete. All later business modules remain empty app boundaries.

## Module boundaries

| Module | Responsibility | Implemented |
| --- | --- | --- |
| `config` | Environment-specific settings and central v1 routing | Yes |
| `core` | Operational liveness/readiness | Yes |
| `accounts` | Users, credentials, sessions, account access rules | Yes |
| `restaurants` | Single restaurant profile/settings; tables in Phase 3 | Skeleton |
| `menu` | Categories, prices, availability in Phase 3 | Skeleton |
| `orders` | Table orders and cashier approval in Phase 4 | Skeleton |
| `kitchen` | One Chef's preparation/ready status in Phase 5 | Skeleton |
| `billing` | Invoices, payment records, cashier printing in Phase 6 | Skeleton |
| `inventory` | Stock and movements in Phase 7 | Skeleton |

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
and six-digit PIN. PINs must be strings so leading zeros are preserved; obvious
repeated/sequential choices are rejected. They are HMAC-peppered with a
separate environment secret before salted Argon2 hashing. Staff have unusable
Django passwords and cannot use password login. Owner cannot use PIN login.

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
classes are foundations for later phases; no printing, kitchen, ordering, or
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
`/api/v1/accounts/` contract. `src/auth/` owns session discovery, role guards,
and temporary-PIN routing. `src/pages/` contains login, overview, staff,
profile, and required-PIN screens; `src/components/` supplies shared controls,
dialogs, and responsive navigation. Hooks coordinate mutations, cooldowns,
and staff reads. No business API or backend schema was added.

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
after login. Neither localStorage nor sessionStorage is used. Mutations are
never automatically replayed after CSRF or network errors. A required PIN
change allows only identity, PIN change, and logout in the client and backend.

During development the browser calls relative `/api` paths through Vite's
proxy. Django must trust the exact browser origin for CSRF (the Origin header
is retained). Production should serve the built SPA with history fallback
and reverse-proxy `/api/` to Django on the same origin; Vite is not the
production application server. See [frontend setup](../frontend/README.md).
