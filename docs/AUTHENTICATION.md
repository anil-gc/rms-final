# Authentication contract (four-digit staff PIN update, 2026-10-27)

Base path: `/api/v1/accounts/`. JSON only. All credentials are strings. No
public registration, Owner-creation endpoint, JWT, bearer-token, or membership
endpoint exists. The React client uses this contract. Username identifies a staff account; a PIN
alone is deliberately insufficient.

## Provisioning

Configure independent `DJANGO_SECRET_KEY`, `DJANGO_PIN_PEPPER` (at least 32
characters), and PostgreSQL credentials in an ignored `.env` or process
environment. In production the pepper must be diverse and separate from the
Django key. Generate it with `secrets.token_urlsafe(48)`; keep it out of Git,
logs, and the database. A pepper change requires staff PIN resets.

After migrations, run `python manage.py bootstrap_owner --username owner`.
It prompts twice for a password, validates Django's password policy (minimum
15 characters plus common/numeric/similarity checks), and never prints it.
It refuses a duplicate Owner/username instead of promoting/replacing an
existing user. The Owner is a Django staff user for read-only account admin,
not a superuser. Trusted local operator recovery uses `changepassword`.

Owner creates staff through the API and communicates a temporary PIN privately.
Choose exactly four ASCII digits, including any leading zeros, without
repeated or sequential patterns (`0000`, `1111`, `1234`, `4321` and cyclic
sequences are rejected). PINs must be JSON strings, never numbers. The API
stores a salted Argon2 hash of the HMAC-peppered PIN and an unusable password.
The new account must change its temporary PIN before using normal protected
APIs. Owner reset has the same forced-change behavior.

## Existing six-digit credentials: compatible transition

Every newly assigned credential (staff creation, Owner reset and self-service
PIN change) must be exactly four digits. Existing hashes cannot reveal PIN
length. They are not truncated, rehashed on sign-in, bulk-reset or marked for
forced change by this code update. Existing sessions and staff IDs remain valid.

Staff Login defaults to four digits and offers **I still use an existing
6-digit PIN** for an account that has not transitioned. The profile and
temporary-PIN form offer the same explicit choice for the *current* PIN;
their new/confirmation fields always require four digits. Toggling length
clears input rather than truncating it. Both input paths submit the full string
to the existing rate-limited verifier. A legacy credential succeeds only when
its complete original hash verifies; this does not permit assigning new
six-digit PINs.

Safe transition options:

1. Staff sign in with their unchanged six-digit PIN, open My profile, select
   the six-digit current-PIN option, and choose a different four-digit PIN.
   The current session is kept; all their other sessions are invalidated.
2. Owner resets that account to a privately communicated four-digit temporary
   PIN using password confirmation. Existing sessions are invalidated and staff
   must choose a different four-digit PIN before normal APIs become available.
   This also handles forgotten legacy PINs.

No automatic cutoff is imposed. Operators must track completed resets/changes
before a separately approved removal of legacy verification; do not infer
length from Argon2 hashes or try to guess every account's PIN. The login and
current-PIN APIs retain bounded string input and generic credential-error
behavior; numeric JSON values are rejected. New PIN fields have strict
four-digit validation in both serializers and `User.set_pin()`.

There is **no schema or data migration** for this change. The pepper, HMAC
derivation, Argon2 hashing, user model, session hash, roles and CSRF contract
remain intact. Only explicitly changed credentials receive a new hash through
the normal credential lifecycle.

The four known staff accounts in the isolated Phase 4 preview were transitioned
on 2026-10-27 through the normal PIN-change API. Generated four-digit values
are in ignored `.local/phase4-preview-credentials.json`, never source/Git.
Owner credentials, user IDs and menu/table/order/audit records were checked
for preservation. The older preview database/environment was not opened or
modified. Existing Phase 4 staff browser sessions must sign in again because
their preview PINs were explicitly changed.

## Client sequence

1. `GET csrf/` and retain the `csrftoken` cookie. Read `csrf_token` from JSON;
   the cookie is HttpOnly, so do not read it from JavaScript.
2. POST the appropriate login body with `X-CSRFToken: <csrf_token>` and cookies.
3. Retain `sessionid` and use the **new** `csrf_token` in the successful login
   response; Django rotates the CSRF secret and session at login.
4. If `user.must_change_pin` is true, POST `pin/change/` before normal API use.
5. Send cookies on subsequent calls, and the CSRF header on POST/PATCH/DELETE.
   POST `logout/` to delete the current server-side session.

React can use `fetch(..., {credentials: "include"})` with these JSON APIs.
Flutter native must retain cookies in a cookie jar and use the same CSRF
bootstrap/header sequence. No client should store PIN/password after login or
try to extract the HttpOnly session cookie from browser JavaScript.

For separate browser origins, explicitly set
`DJANGO_CORS_ALLOW_CREDENTIALS=True`, `DJANGO_CORS_ALLOWED_ORIGINS`, and
`DJANGO_CSRF_TRUSTED_ORIGINS` to trusted scheme/host/port values. Use the same
site for frontend and API; SameSite=Lax intentionally remains enabled. Native
Flutter is not subject to browser CORS. The React frontend instead uses a
same-origin Vite `/api` proxy in development. Add its exact origin to
`DJANGO_CSRF_TRUSTED_ORIGINS`, for example `http://localhost:5173` (or
`http://localhost:5174` when explicitly using that port). CORS credentials are
not needed for this proxy arrangement. Use the frontend origin consistently
in the browser; localhost and 127.0.0.1 have different cookie scopes.

The React integration has been exercised against Django/PostgreSQL in a real
browser, including login CSRF rotation, stale-CSRF rejection/manual recovery,
Owner staff management, temporary/reset PIN enforcement, session revocation,
role denial, refresh persistence, and logout. UI/API test details and local
commands are in [frontend/README.md](../frontend/README.md). Backend account
behavior and production cookie settings are unchanged.

Phase 3 extends the same session and CSRF contract to restaurant, menu, and
table APIs. Owner/Manager may manage workspace records; other provisioned
users have read-only access. Temporary-PIN sessions are denied all Phase 3
endpoints, including logo delivery. No new authentication workflow or token
type was introduced. See [the Phase 3 contract](PHASE_3.md).

## Endpoints

| Method and relative path | Body | Access/result |
| --- | --- | --- |
| `GET csrf/` | None | Public; `{csrf_token}`; no session login |
| `POST login/owner/` | `username`, `password` | Public + CSRF; Owner password only |
| `POST login/staff/` | `username`, `pin` | Public + CSRF; Manager/Cashier/Waiter/Chef |
| `GET me/` | None | Active provisioned account; returns own profile and forced-change state |
| `POST logout/` | `{}` | Active provisioned account, including temporary-PIN sessions; 204 |
| `POST pin/change/` | `current_pin`, `new_pin` | Staff changes only their own PIN, including temporary PIN |
| `POST password/change/` | `current_password`, `new_password` | Owner only; validates password policy |
| `GET staff/` | None | Owner only; list staff profiles, including inactive accounts |
| `POST staff/` | `username`, `role`, `pin`, `owner_password`; optional `first_name`, `last_name` | Owner only; 201 with temporary-PIN staff profile |
| `PATCH staff/<id>/` | `is_active`, `owner_password` | Owner only; deactivate/reactivate staff |
| `POST staff/<id>/pin/reset/` | `new_pin`, `owner_password` | Owner only; reset a staff PIN and require change |

Login succeeds with `{user: <profile>, csrf_token: <new token>}`. Profile fields
are `id`, `username`, `first_name`, `last_name`, `role`, `is_active`, and
`must_change_pin`. No raw credentials, hashes, privilege flags, or session key
are returned. Other successful profile operations return the profile itself.
Owner cannot be targeted by staff mutation routes. Unknown fields, including
privilege flags or restaurant IDs, are rejected rather than ignored.

## Errors and limits

- 400: invalid input, weak/newly reused PIN, password policy failure, duplicate
  username, or an unknown field.
- 401: generic `{"detail":"Invalid credentials."}` for an invalid login or
  credential confirmation. Disabled/unknown users get the same login error.
- 403: absent/invalid session, role denied, required PIN change, or failed CSRF.
  Session authentication intentionally follows DRF's 403 convention.
- 404: staff target not found, including Owner IDs on staff-management routes.
- 429: shared login/credential attempt budget exhausted; honor `Retry-After`.

Defaults: **three failed/in-flight PIN checks** per case-insensitive username
per 15 minutes (`ACCOUNTS_PIN_ACCOUNT_LIMIT=3`); Owner passwords retain five.
A lower shared account limit also applies to PINs. Both credential types use
the same account bucket, so another route cannot clear prior failures or
produce a fresh identity budget. There are also 30 total checks per source IP
per minute. Correct credentials
refund only that account attempt; existing failures stay counted. IP attempts
are never refunded. Password confirmation shares the login budget. Current-PIN
changes use a separate account/IP scope with the stricter three-attempt PIN
cap. Login budgets
protect Django admin too; admin displays its normal generic failed-login form
when blocked rather than issuing API JSON.

The admin self-password-change form at `/admin/password_change/` also uses
the shared budget; exhausted attempts return 429 with `Retry-After`. Successful
changes refund only their account attempt and invalidate other sessions using
Django's standard password/session handling. Staff and PIN management in the
account-record admin remains read-only. Active login limits still apply after
an Owner resets a staff PIN; honor the remaining cooldown.

Four-digit PINs have at most 10,000 combinations, 100 times fewer than six-digit
PINs. The stricter cap is this application's tradeoff between guessing resistance
and temporary denial of service; it is not a guarantee against sustained attacks
or a claim of password/MFA compliance. Keep account-based admission across
workers/IPs, timed cooldowns, Retry-After and generic errors. Successful login
never clears earlier failures. Production still requires HTTPS and appropriate
network/edge access controls. This review follows [OWASP's account-based login
throttling guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html#login-throttling);
OWASP does not prescribe this project's exact three-attempt setting.

Malformed inputs/CSRF failures do not reach credential hashing. Requests never
trust `X-Forwarded-For`; the deployment must supply trustworthy `REMOTE_ADDR`.
Use `purge_login_limits` daily; HMAC bucket records older than a day are removed.

## Session and credential lifecycle

Owner sessions last at most one hour; staff sessions last at most eight hours
from login/session renewal. Normal reads do not extend expiry. Sessions are
server-side with HttpOnly, SameSite=Lax cookies; production adds Secure.
Credential responses use `no-store`. A PIN/password change keeps the caller's
current session but invalidates their other sessions. Owner PIN reset and
deactivation/reactivation invalidate all affected staff sessions. Old cookies
cannot be restored by reactivating an account. Role and credential state also
participate in Django's session authentication hash.

Phase 2 changes the configured backend and session hash, so pre-existing
Phase 1 admin sessions must sign in again. No existing users, password hashes,
or identifiers are replaced. Legacy blank-role accounts receive no API role.
MFA, public Owner recovery, role changes/Owner transfer, and token-based
authentication are not implemented; they require an explicit future decision.

Implementation references: [Django sessions](https://docs.djangoproject.com/en/5.2/topics/http/sessions/),
[Django password hashing](https://docs.djangoproject.com/en/5.2/topics/auth/passwords/),
and [DRF session authentication](https://www.django-rest-framework.org/api-guide/authentication/#sessionauthentication).
Login has explicit CSRF protection because DRF's session CSRF behavior alone
does not protect anonymous login. Database admission locks address the
[concurrency limits of cache-based DRF throttling](https://www.django-rest-framework.org/api-guide/throttling/#a-note-on-concurrency).
