# Phase 2 authentication contract

Base path: `/api/v1/accounts/`. JSON only. All credentials are strings. No
public registration, Owner-creation endpoint, JWT, bearer-token, membership, or
frontend implementation exists. Username identifies a staff account; a PIN
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
Choose six ASCII digits without obvious repeated/sequential patterns. The API
stores a salted Argon2 hash of the HMAC-peppered PIN and an unusable password.
The new account must change its temporary PIN before using normal protected
APIs. Owner reset has the same forced-change behavior.

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
Flutter is not subject to browser CORS. No frontend integration is claimed as
tested in this phase.

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

Defaults: five failed/in-flight checks per case-insensitive username per 15
minutes, plus 30 total checks per source IP per minute. Correct credentials
refund only that account attempt; existing failures stay counted. IP attempts
are never refunded. Password confirmation shares the login budget. Current-PIN
changes use a separate account/IP scope with the same limits. Login budgets
protect Django admin too; admin displays its normal generic failed-login form
when blocked rather than issuing API JSON.

The admin self-password-change form at `/admin/password_change/` also uses
the shared budget; exhausted attempts return 429 with `Retry-After`. Successful
changes refund only their account attempt and invalidate other sessions using
Django's standard password/session handling. Staff and PIN management in the
account-record admin remains read-only. Active login limits still apply after
an Owner resets a staff PIN; honor the remaining cooldown.

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
