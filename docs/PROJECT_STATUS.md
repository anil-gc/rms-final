# Project status

Date: 2026-10-19 (Asia/Kathmandu).
Current phase: **Phase 2 - Accounts and Authentication**.
State: **complete and verified; awaiting the project owner's review**.

## Completed implementation

- Phase 1 inspected and freshly verified before Phase 2 began: 37 tests passed.
- Five roles with no automatic privileges for legacy/unassigned accounts.
- One initial Owner created by a non-overwriting, password-prompting command.
- Owner-only staff creation, list, PIN reset, and deactivation/reactivation;
  writes require Owner password confirmation.
- Staff username/PIN login, Owner password login, current identity, and logout.
- Separate pepper plus salted Argon2 PIN hashing; Argon2 password hashing.
- Required temporary/reset PIN change, self-service PIN and Owner password
  change, and revocation of other/affected sessions.
- Database-backed rate limits shared across workers and admin/API login.
- The built-in admin self-password-change form shares credential limits too;
  it cannot bypass protection by checking passwords outside the auth backend.
- Reusable role permissions; no implicit Owner/superuser bypass.
- CSRF protection including anonymous login, no-store account responses, and
  read-only account admin excluding credentials.

## Models, migrations, and routes

`User` keeps its existing table and adds role, PIN hash, forced-change flag,
and authentication version. `LoginRateLimit` holds HMAC budget identifiers.
Django's existing Session table stores sessions. New migration:
`accounts/0002_loginratelimit_user_auth_version_and_more.py`. The original
`0001_initial.py` remains unchanged; there is no data migration that assigns
roles or replaces existing users. New constraints enforce valid roles and a
single Owner. Migration preservation is covered by an automated test.

Operational probes remain `/api/v1/health/` and `/api/v1/health/ready/`.
Account routes live under `/api/v1/accounts/`; see
[the full endpoint/permission contract](AUTHENTICATION.md).

## Verification

Phase 2 verification: **135 tests passed against isolated PostgreSQL 18**,
using Python 3.12.7 and the project's pinned dependencies.
All of the following passed:

- Django system checks including the PostgreSQL configuration.
- `makemigrations --check --dry-run`, migration application, and `migrate --check`.
- Ruff lint and formatting; `pip check`.
- Production `check --deploy --fail-level WARNING` and static collection.
- Real HTTP liveness, PostgreSQL readiness, and admin login-page checks.
- Real HTTP CSRF bootstrap, Owner login/read-only admin access, Owner-created
  staff, staff PIN login, forced PIN change, identity, logout, and rejection
  after logout.
- Credential/file-hygiene scan, blank example secrets, resolved local docs links.

The initial 126-test run passed. Two later regression tests needed corrected
fixtures (a role within the column length and deterministic window advancement);
the final full suite includes those fixes and the admin security regressions.
No failed checks remain. Temporary verification services were stopped.

Tests cover CSRF, Owner-only writes, credential validation, role matrix, legacy
permissions, secure hashing, temporary PIN flow, session expiry/replay/revocation,
database-enforced single Owner, bootstrap safety, generic failures, budgets,
forwarded-IP spoofing, concurrent budget admission, and migration preservation.
No restaurant/business data or existing prototype database was used.

## Git and review

Files changed: **14 existing files updated and 22 new files added**. Changes are
limited to accounts models/admin/backend/middleware/validators/permissions,
serializers/services/views/URLs, two account management commands, one migration,
settings/routing/environment/dependencies/CI, authentication tests, and docs.
The restaurants app change only updates its scope docstring; it adds no model.
No tracked files were deleted. Architecture, roadmap, project status, and
authentication contracts are maintained under `docs/`.

Branch: `feature/accounts-authentication`, based on Phase 1 commit
`551ac051ccd2706da325ad57ac45c5cef5201cb2`. Origin is
`https://github.com/anil-gc/rms-final.git`. The project owner has authorized
committing and pushing Phase 2 on this feature branch for review. Merging and
Phase 3 require separate approval. The separate prototype is untouched.

## Limits and next action

No frontend, restaurant profile, menu, tables, orders, kitchen, billing,
printing, inventory, dashboards, branches, tenancy, subscription, or membership
features are implemented. Shared/prototype databases have not been migrated.
The new pepper is required configuration; changing it requires staff PIN resets.
Old Phase 1 sessions need a new login. MFA/public recovery, token issuance,
hosting, production TLS traffic, and actual React/Flutter integration are not
implemented or verified. GitHub Actions has not been run for these local changes.

After final Phase 2 review, stop and wait for explicit approval. Recommended
next phase is Phase 3: single restaurant profile/settings, menu, and tables.
Publishing/merging and starting Phase 3 require separate explicit authorization.
