# Project status

Date: 2026-10-19 (Asia/Kathmandu).
Current scope: **React frontend integration for the completed accounts APIs**.
State: **complete and verified; ready for pull-request review**.
The owner authorized feature-branch publication with a PR targeting
`feature/accounts-authentication`. Merging and Phase 3 remain unauthorized.
Phase 3 has not started.

## Preserved backend baseline

Phase 1 supplied the modular Django/PostgreSQL foundation and passed 37 tests.
Phase 2 added five roles, secure Owner/password and staff/PIN authentication,
Owner-only staff management, temporary/reset PIN enforcement, session
revocation, shared database rate limits, and role permissions. Its published
commit is `2006becdb1222132b7b9fa3f0b06a9c971ab2477` on
`feature/accounts-authentication`, following Phase 1 commit
`551ac051ccd2706da325ad57ac45c5cef5201cb2`.

No backend source, migration, dependency, production setting, or existing test
has changed for this frontend work. All business apps remain skeletons. The
separate restaurant prototype and its database remain untouched. The existing
user table, initial migration, and account security model remain intact.
See [architecture](ARCHITECTURE.md) and [authentication contract](AUTHENTICATION.md).

## Frontend implementation

- Independent `frontend/`: React, TypeScript, Vite, Tailwind CSS, React Router.
- Responsive forest/sage workspace with sidebar, mobile navigation, reusable
  controls/dialogs, and loading, empty, success, failure, and cooldown states.
- Owner password login and staff username/PIN login using real Django sessions.
- Account overview with actual identity, role, and Owner staff counts.
- Owner staff creation, filtering, PIN reset, deactivation/reactivation, with
  password confirmation on every mutation.
- Required temporary/reset PIN change before normal protected navigation.
- Read-only profile, self-service PIN/Owner password change, confirmed logout.
- Memory-only CSRF bootstrap/rotation; no localStorage/sessionStorage or token
  authentication. Server permissions remain authoritative.
- Session refresh on focus/visibility/interval and cross-tab change notification;
  network outages do not masquerade as successful logout. Stale identity reads
  cannot overwrite a more recent login or logout.
- Updated architecture, API integration, setup, status, and roadmap documents.

## Current verification

All final commands are run locally; GitHub Actions and hosted deployment have
not been run for the frontend changes.

| Check | Result |
| --- | --- |
| Frontend ESLint | Passed |
| Frontend Vitest | 15 tests passed across 3 files |
| TypeScript and Vite production build | Passed |
| Django `check --database default` | Passed, no issues |
| Django `makemigrations --check --dry-run` | Passed, no model drift |
| Backend pytest on isolated PostgreSQL 18 | 135 tests passed |
| Backend Ruff | Passed |
| Pre-publication browser integration recheck | Passed after correcting browser automation synchronization |

Frontend tests cover CSRF bootstrap/rotation, cookie request options,
manual recovery without mutation replay, structured/rate-limit/network errors,
protected/Owner/PIN guards, and session reconciliation races.

Real-browser checks against Django/PostgreSQL cover Owner and staff login,
CSRF rejection/manual recovery without false logout, staff creation/search/
filters/deactivation/reactivation/reset, forced PIN change and direct-URL
restriction, backend role denial, refresh persistence, Owner password change,
session revocation, and logout. Mobile navigation and small-screen layouts are
checked alongside desktop views. A 320px staff-header overflow found during
verification was corrected by wrapping heading actions; dialogs now explicitly
restore focus to their trigger on close. Both fixes passed browser rechecks.
Expected anonymous, role-denial, and deliberate CSRF 403 responses are part of
these checks. Before publication, frontend lint, all 15 frontend tests,
TypeScript/build, and all 135 backend tests were rerun successfully, together
with Django database checks, migration drift/pending checks, and Ruff lint and
format checks. The production-dependency npm audit reported no vulnerabilities.

The staff-login timeout was reproduced and diagnosed as a browser automation
race. Immediately after selecting Staff login, the URL had changed while the
DOM still contained the outgoing Owner password form. Automation filled its
shared username input; React then mounted the Staff form with an empty
username. Native required-field validation blocked submission before the
React submit handler, explaining the absent staff-login POST in both browser
network events and Django logs. No application defect was confirmed, and no
frontend/backend authentication source was changed for this diagnosis.

Waiting for the destination's unique PIN input before filling either field
corrected the browser check. Repeated verification then confirmed both logins,
identity/staff data, Owner password-confirmation dialog, refresh persistence,
backend/route role denial, mobile navigation, HttpOnly/Lax cookie flags, empty
browser storage, and server-confirmed logout. A further browser run reset the
isolated preview staff PIN through the Owner UI, signed in with that temporary
PIN, checked that `/`, `/profile`, and `/staff` redirected to `/change-pin`,
completed the required PIN change, verified normal profile access and Owner
route denial, and logged out. Django recorded 200 for staff login/PIN change
and 204 for logout, followed by the expected unauthenticated identity 403.
The preview's original private staff PIN was restored through the supported
change-PIN flow. No JavaScript runtime errors occurred in that run; expected
anonymous/forbidden-resource 403 console messages remain part of the checks.

Historical Phase 2 verification also covered production Django deploy checks,
static collection, migration preservation, and dependency checks; those are
backend baseline evidence, not a claim of a production frontend deployment.

## Working local preview

- Frontend: **http://localhost:5174/**. Port 5173 is occupied by another existing
  application, which was preserved. Vite has an explicit, strict port.
- Backend: **http://127.0.0.1:8000/**; root has no page. Readiness:
  **http://127.0.0.1:8000/api/v1/health/ready/**.
- Isolated database: `rms_frontend_development`, PostgreSQL 18 on 127.0.0.1:55440.
  Browser checks used real preview Owner and Waiter accounts in that database.
- Generated credentials are private in `.local/preview-credentials.txt`.
  The ignored `backend/.env` has separate generated Django key, PIN pepper,
  database credentials, and explicit localhost CSRF trusted origins.
- Servers remain running for local review. This is computer-local, not a hosted
  or production deployment. Startup instructions are in
  [frontend/README.md](../frontend/README.md).

## Git and boundaries

Branch: `feature/react-frontend`, based on the published Phase 2
commit above. Origin: `https://github.com/anil-gc/rms-final.git`.
Changes are the new frontend, root ignore rules, and documentation. The owner
authorized committing and pushing this branch and opening a pull request.
All publication verification gates now pass. The earlier browser timeout and
its automation-only correction are documented above.
The PR targets `feature/accounts-authentication`, the direct parent containing
the APIs this frontend requires; the repository has no `main`/`develop` branch.
No merge is authorized. The commit message is
`feat(frontend): add React authentication interface`.
Credentials, environment files, dependencies, build output, browser state,
logs, and local PostgreSQL data are ignored.

No restaurant profile, menu, tables, orders, kitchen, billing, payment,
printing, inventory, business dashboards, multi-tenancy, or frontend-hosting
features were added. Account overview cards reflect implemented identity and
staff APIs only. Stop after publication for the owner's PR review; merging
and any Phase 3 development require separate explicit approval.
