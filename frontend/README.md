# RMS React frontend

React + TypeScript + Vite, Tailwind CSS, and React Router. This client implements
only the existing accounts/authentication APIs. It contains no restaurant,
menu, orders, kitchen, billing, or inventory workflows.

## Setup

Use Node.js 22.12+ (verified locally with Node 22.13.0) and npm. Start the
backend following [backend/README.md](../backend/README.md): configure PostgreSQL,
`DJANGO_SECRET_KEY`, and `DJANGO_PIN_PEPPER` in the ignored `backend/.env`,
run migrations, then provision the initial Owner using `bootstrap_owner`.
There are no default credentials or public signup.

From the repository root, in one PowerShell terminal:

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py bootstrap_owner --username owner
..\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Run `bootstrap_owner` only for a new database; it refuses to overwrite an
existing Owner. It prompts privately for a password.

Add the frontend's exact origin to the backend environment before starting
Django:

```dotenv
DJANGO_CSRF_TRUSTED_ORIGINS=http://localhost:5173,http://localhost:5174
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Default frontend: `http://localhost:5173/`. Backend:
`http://127.0.0.1:8000/`; its root intentionally has no page. Check
`http://127.0.0.1:8000/api/v1/health/ready/` for database readiness.
Vite uses `strictPort`; it reports a busy port instead of silently moving.
If 5173 is occupied, preserve that service and run:

```powershell
npm run dev -- --port 5174
```

The current verified local preview uses **http://localhost:5174/** because
5173 belongs to another application. The backend runs on port 8000 against an
isolated local PostgreSQL database, `rms_frontend_development`, on port 55440.
Its generated preview credentials are in the ignored local file
`../.local/preview-credentials.txt`. This is development data, separate from
the prototype and any shared restaurant database. It is not a deployed site.

After a computer restart, this preview's dedicated PostgreSQL cluster may
need starting before Django. From the repository root, using the installed
PostgreSQL 18 tools (only when port 55440 is not already listening):

```powershell
& 'C:\Program Files\PostgreSQL\18\bin\pg_ctl.exe' -D "$PWD\.local\frontend-postgres" -l "$PWD\.local\frontend-postgres\server.log" -o '-h 127.0.0.1 -p 55440' -w start
```

Other developers should use their own database and environment as described
in the backend guide; the private preview cluster is not part of Git.

## API and session configuration

The browser requests relative `/api/v1/accounts/` URLs. Vite proxies `/api`
to `http://127.0.0.1:8000`; optionally copy `.env.example` to `.env.local` and
set `DEV_BACKEND_URL` to another local backend. This server-only setting is
not a credential. Never put secrets in `VITE_*` variables: those are browser
configuration. No frontend environment file is necessary for the default proxy.

The proxy keeps requests same-origin to the browser, so no Django CORS change
is needed. Django still validates the original browser Origin against the
explicit CSRF trusted origins. Do not enable wildcard origins or disable
CSRF. Keep using `localhost` for the frontend rather than mixing host names.

The client bootstraps CSRF from JSON, sends cookies and `X-CSRFToken` on
mutations, and adopts the rotated token after login. It does not read
HttpOnly cookies or persist credentials in browser storage. Failed mutations
require manual resubmission; rate-limit responses disable submission for the
server's Retry-After period. Logout waits for server confirmation.

## Structure and actual API coverage

```text
src/
  auth/          Session provider/context and protected routes
  components/    Shared controls, native dialogs, responsive layout
  hooks/         Mutation/cooldown and staff-list state
  lib/           Central accounts API client
  pages/         Login, overview, staff, profile, required PIN change
  test/          Shared test setup
  App.tsx        Route tree
  styles.css     Tailwind theme and responsive application styles
  types.ts       Account/role contracts
```

| Screen                        | Client route     | Implemented backend endpoints                    |
| ----------------------------- | ---------------- | ------------------------------------------------ |
| Owner sign-in                 | `/login/owner`   | `csrf/`, `login/owner/`                          |
| Staff sign-in                 | `/login/staff`   | `csrf/`, `login/staff/`                          |
| Account overview              | `/`              | `me/`; Owner also reads `staff/`                 |
| Staff management              | `/staff`         | `staff/`, `staff/<id>/`, `staff/<id>/pin/reset/` |
| Required temporary PIN change | `/change-pin`    | `me/`, `pin/change/`, `logout/`                  |
| Profile / credential change   | `/profile`       | `me/`, `pin/change/`, `password/change/`         |
| Sign out                      | Confirmed dialog | `logout/`                                        |

Endpoint paths in this table are relative to `/api/v1/accounts/`. Owner can
create staff, search/filter the returned list, reset PINs, and deactivate or
reactivate accounts, with password confirmation for writes. Role changes,
account deletion, and profile editing have no API and are not offered.
Dashboard counts come from real staff records; a failed request shows an
unavailable/error state rather than invented zero values. Staff only see
their own identity and permitted navigation. Backend permissions remain
authoritative; required PIN sessions cannot enter normal protected screens.

## Verification and production boundary

```powershell
npm run lint
npm run test
npm run build
```

Vitest covers the CSRF/API client, permission and temporary-PIN guards, and
session races/revalidation. Separate real-browser verification covers Django
integration and desktop/mobile flows; browser artifacts and generated test
credentials remain ignored. See [project status](../docs/PROJECT_STATUS.md).

When automating navigation between Owner and Staff login, wait for the
destination form's unique control before filling shared fields: wait for the
`PIN` input after selecting Staff login, and for `Password` after selecting
Owner login. A changed URL or the shared welcome heading does not prove React
has mounted the new form. Filling the outgoing username field can otherwise
be lost on remount, leaving native required-field validation to block the
submit before any API request. Assert form validity and observe the actual
login response; keep request bodies, cookies, and credentials out of reports.

`npm run build` type-checks and produces `dist/`. For production, configure a
static host to serve `index.html` for SPA routes and proxy `/api/` to Django
on the same origin, preserving cookies and HTTPS. Apply the backend's
production security settings. `npm run preview` serves the compiled assets
on 4173 for visual inspection; it has no API proxy configured. Production
hosting, TLS, and deployment are not included or verified in this work.

Review changes on `feature/react-frontend`. Do not commit secrets, `.env`,
dependencies, build output, browser state, or `.local/`. The owner has authorized
publication as a PR targeting `feature/accounts-authentication`; merging and
Phase 3 work require separate approval.
