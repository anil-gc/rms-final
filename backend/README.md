# RMS backend — foundation, accounts, and restaurant workspace

Python 3.12+, Django 5.2 LTS, Django REST Framework, and PostgreSQL. Python 3.12
is the team's recommended baseline and the CI version. The frontend uses
React, Vite, TypeScript, and Tailwind CSS. No ordering, kitchen, POS, payment, inventory, or business dashboard features
are implemented. Phase 2 adds Owner password login, staff PIN login, secure
sessions, Owner-only staff provisioning, and role permissions. There is no
public registration or bearer-token/JWT issuance.

Phase 3 adds the singleton restaurant profile, validated logo upload/delivery,
menu categories/items with decimal NPR pricing and availability, and physical
tables with manual occupancy. Owner/Manager manage these records; other ready
staff have read-only access. See [the Phase 3 API contract](../docs/PHASE_3.md).

## Architecture

A **modular monolith**: one Django deployment, one PostgreSQL database, and
domain modules with standard `AppConfig` registrations. No microservices,
generic repositories, tenant middleware, or speculative service layers.

```text
backend/
├── config/
│   ├── settings/{__init__,base,development,production}.py
│   ├── api_urls.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── core/
│   ├── accounts/
│   ├── restaurants/
│   ├── menu/
│   ├── orders/
│   ├── kitchen/
│   ├── billing/
│   └── inventory/
├── tests/
├── requirements/{base,development,production}.txt
├── manage.py
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

Each app contains `__init__.py`, `apps.py`, `models.py`, `admin.py`, and a
`migrations/` package. Accounts also contains credential services, serializers,
views, permissions, login limits, and management commands. Core contains
operational probes and shared authenticated API behavior. Restaurants and menu
contain Phase 3 models, serializers, routes, read-only admin, and migrations.
Orders, kitchen, billing, and inventory remain empty foundations.

| App | Responsibility when developed | Current content |
| --- | --- | --- |
| core | Small, genuinely shared infrastructure and operational probes | Health endpoints |
| accounts | Identity, credentials, and permissions | Role-aware User, sessions, PINs, rate limits, read-only account admin |
| restaurants | Single restaurant profile and physical tables | Profile/logo and table/occupancy APIs |
| menu | Menu catalogue and availability | Categories, decimal prices, availability and archiving |
| orders | Orders, line items, and order lifecycle | App skeleton |
| kitchen | Preparation and kitchen state | App skeleton |
| billing | Invoices, taxes, and payment records | App skeleton |
| inventory | Stock and stock movements | App skeleton |

Keep domain validation close to its models and use focused serializers/views
when APIs are added. Introduce services for concrete transactional operations
when needed. Core must not become a container for unrelated business logic.
Reference users with `settings.AUTH_USER_MODEL` in model relationships and
`get_user_model()` in runtime code. Do not import Django's built-in User model.

### Single-location scope

The target is one restaurant at one location per deployment. Branches, tenancy,
subscriptions, and memberships are outside the current roadmap. Module
boundaries permit a separately approved future design without implementing
those tables, identifiers, or request context now.

## Local setup

Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Set-Location backend
python -m pip install -r requirements/development.txt
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Put the first generated value into `DJANGO_SECRET_KEY` and the second into
`DJANGO_PIN_PEPPER` in `.env`, enclosed in single quotes. Use separate values.
Set a separate database password below. All three values are required;
blank or missing values stop startup. Never paste secrets into a PR or commit.
If activation is blocked, invoke `..\.venv\Scripts\python.exe` directly.

Linux/macOS equivalents from the repository root:

```sh
python3.12 -m venv .venv
. .venv/bin/activate
cd backend
python -m pip install -r requirements/development.txt
cp .env.example .env
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
python -c 'import secrets; print(secrets.token_urlsafe(48))'
```

Pins in `requirements/` cover direct and transitive dependencies. Upgrade them
together in a reviewed PR and rerun all checks. Use the project virtual
environment, not the prototype's environment.

### PostgreSQL

Install/start PostgreSQL 17 or 18 (Django 5.2 supports 14+). Connect as your
local PostgreSQL administrator using `psql -U postgres -d postgres`. Create a
**new** role/database; never reuse the prototype's database:

```sql
CREATE ROLE rms_app LOGIN CREATEDB NOSUPERUSER NOCREATEROLE;
\password rms_app
CREATE DATABASE rms_development OWNER rms_app;
```

`\password` prompts without putting a real password into this guide or your
SQL command history. Set `DB_PASSWORD` in `.env` to that value, single-quoted.
The example's database name, user, host, and port match these instructions.
On Windows, `psql` may be under `C:\Program Files\PostgreSQL\18\bin\psql.exe`.

`CREATEDB` is for **local tests only**: pytest-django creates and destroys
`test_rms_development`, using the committed migrations. Do not put valuable
data in a database with that name. Never grant `CREATEDB`, superuser, or role
administration to a production application role. Production schema migrations
should run through a separately authorized deployment role.

### Start Django

From `backend/` with the virtual environment active:

```powershell
python manage.py check --database default
python manage.py migrate
python manage.py bootstrap_owner --username owner
python manage.py runserver 127.0.0.1:8000
```

`bootstrap_owner` prompts for a password of at least 15 characters and refuses
to overwrite existing accounts. It creates the single business Owner with
read-only account admin access and no superuser flag. No default account is
created. `createsuperuser` remains an operator recovery tool; unassigned
superusers receive no business API role. Django's admin is at
`http://127.0.0.1:8000/admin/`. This is a
computer-local development address, not a public deployment.

## API and settings

| Route | Behavior |
| --- | --- |
| `GET /api/v1/health/` | Public liveness, no database query; `200 {"status":"ok","version":"v1"}` |
| `GET /api/v1/health/ready/` | Public database readiness; `SELECT 1`, returns 200 or generic 503 |
| `/admin/` | Built-in staff-only Django admin |
| `/api/v1/accounts/` | Authentication and Owner-only staff management; see the API contract |

See [the authentication API contract](../docs/AUTHENTICATION.md) for all account
routes, request bodies, role rules, and the React/Flutter cookie flow. No
restaurant business endpoints, unversioned aliases, or v2 routes exist.
Readiness confirms connectivity, not migration freshness; run `migrate --check`
as part of release verification. Both probes support HEAD and OPTIONS and
reject writes. Database exception details are omitted from responses and logs.

`config.urls` owns the `/api/v1/` namespace. `config.api_urls` is the central
registry for future app URLs. DRF uses `NamespaceVersioning`, JSON responses
and request bodies. Default permissions require an active, provisioned user
whose temporary PIN has been changed. Only probes, CSRF bootstrap, and login
explicitly allow anonymous access. Database-backed Django sessions and explicit
CSRF checks protect authentication and writes. Browser credential sharing stays
disabled unless `DJANGO_CORS_ALLOW_CREDENTIALS=True` is explicitly set together
with enumerated trusted frontend origins.

Settings:

- `base.py`: installed apps, middleware, PostgreSQL, custom user, DRF, CORS,
  timezone-aware timestamps, password validators, and console logging.
- `development.py`: local hosts and environment-controlled debug mode.
- `production.py`: debug forced off, strong secret and explicit hosts required,
  database TLS required, HTTPS redirects, secure cookies, HSTS, and compressed
  static files for Django admin via WhiteNoise.

Process environment variables override `backend/.env`. Set
`DJANGO_READ_DOT_ENV_FILE=False` in CI/hosting to ignore local dotenv files.
`manage.py` defaults to development; WSGI and ASGI default to production.
Choose a settings module using the process `DJANGO_SETTINGS_MODULE` variable
or management command `--settings` option. A `DJANGO_SETTINGS_MODULE` value
inside `.env` cannot choose the settings module during import.

The `.env.example` documents database, CORS, CSRF, and logging variables.
Allowed CORS origins include scheme/port, without trailing slashes. CORS only
controls browser access; it does not replace authentication or authorization.
Flutter native clients are not governed by browser CORS. The timezone is
`Asia/Kathmandu`; timezone-aware timestamps are stored consistently by Django.
Console logs intentionally omit request bodies and credentials. Do not add
private data to log messages.

Keep `DJANGO_PIN_PEPPER` separate from the database and from the Django secret.
PINs are HMAC-peppered then salted and hashed using Argon2; passwords also use
Argon2. Existing Django PBKDF2 password hashes remain readable. Changing the
pepper makes existing staff PINs unusable: coordinate Owner resets and back up
the pepper securely. Owner recovery uses the trusted operator command
`python manage.py changepassword owner`, which prompts without accepting a
password argument. It revokes old sessions through Django's session hash.

Schedule `python manage.py clearsessions` and
`python manage.py purge_login_limits` daily. Login budgets use PostgreSQL row
locks shared by all workers. They trust `REMOTE_ADDR`, never a client-supplied
forwarded-IP header. Configure any trusted production proxy accordingly.

### Production configuration smoke checks

Use a separate environment with `DJANGO_SETTINGS_MODULE=config.settings.production`,
a unique strong secret, real `DJANGO_ALLOWED_HOSTS`, explicit frontend origins,
and a production database. **Do not use the development `.env` unchanged**:
it sets `DB_SSLMODE=prefer`, which production deliberately rejects. Production
defaults to `require` if unset; prefer `verify-full` and configure a trusted
PostgreSQL certificate using libpq's `PGSSLROOTCERT` environment variable.

```sh
python -m pip install -r requirements/production.txt
python manage.py check --deploy --fail-level WARNING --settings=config.settings.production
python manage.py migrate --settings=config.settings.production
python manage.py migrate --check --settings=config.settings.production
python manage.py collectstatic --noinput --settings=config.settings.production
gunicorn config.wsgi:application --bind 127.0.0.1:8000
```

Gunicorn is for Linux/Unix; it is not a Windows server. ASGI is provided as an
entry point, but no ASGI server or websocket stack is selected in Phase 1.
Configure HTTPS termination before production use. Set
`DJANGO_BEHIND_HTTPS_PROXY=True` only for a trusted proxy that strips incoming
`X-Forwarded-Proto` and replaces it with the actual client scheme. Review the
one-year HSTS policy, including subdomains/preload, before exposing the domain.
Do not submit the domain to preload lists automatically. Admin/API password
login share failed-attempt protection. Network restrictions, backups,
monitoring, hosting, and deployment
hardening remain release work. This foundation is not a deployed product.

## Verification

From `backend/`, with your local PostgreSQL role/database and `.env` ready:

```powershell
python -m pip check
ruff check .
ruff format --check .
python manage.py check --database default
python manage.py makemigrations --check --dry-run
python manage.py migrate --noinput
python manage.py migrate --check
pytest -q
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health/ready/
```

The last two commands require the development server to be running. On Unix,
use `curl` instead of `Invoke-RestMethod`. Tests use PostgreSQL, not SQLite.
They cover foundation configuration and probes plus Owner/staff authentication,
CSRF, role enforcement, credential and session invalidation, migration
preservation, and concurrent PostgreSQL login budgets. See
[current verification evidence](../docs/PROJECT_STATUS.md).

`.github/workflows/backend.yml` provides the same core checks on GitHub with
an isolated PostgreSQL service, an ephemeral Django secret, and a clearly
disposable CI database password. It also checks production configuration and
static collection. No production credentials are stored in the workflow.

## Three-developer GitHub workflow

This workspace was initially empty. Phase 2 is prepared on
`feature/accounts-authentication`, based on the published Phase 1 branch, with
`origin` pointing to
`https://github.com/anil-gc/rms-final.git`. The separate prototype repository
and its remote remain unchanged.

Use the team's agreed default branch (`main` is recommended) and short-lived
branches such as `feat/accounts-foundation` or `fix/settings-validation`.
For each task:

1. Update from the default branch and create a focused branch.
2. Agree on ownership of cross-cutting settings, User, and migrations before
   overlapping work; never change another developer's public API silently.
3. Commit code, relevant tests, and migrations together. Never commit `.env`,
   virtual environments, database files, logs, credentials, or generated assets.
4. Open a PR describing the behavior, scope, migrations, and checks run.
5. Require passing backend CI and at least one teammate's review. Configure
   protected `main` in GitHub; the repository cannot enforce that locally.
6. Resolve migration conflicts together. Never delete or edit a migration
   already applied in a shared environment; add a follow-up migration instead.

Do not commit directly to shared `main`, force-push shared branches, commit
large unrelated refactors, or commit private restaurant/customer data.

## Adding a future Django app

Keep apps under `backend/apps`, and use a unique plural domain name when
appropriate. Example commands, to run **only in a later approved phase**:

```powershell
New-Item -ItemType Directory apps/reservations
python manage.py startapp reservations apps/reservations
```

Set the generated AppConfig's `name = "apps.reservations"` and
`default_auto_field = "django.db.models.BigAutoField"`, then register
`apps.reservations.apps.ReservationsConfig` in `base.py`. Use absolute imports
from `apps.reservations` or app-local relative imports; do not modify `sys.path`.
Add an app `urls.py` only when it has real endpoints, then register it in
`config/api_urls.py`, for example:

```python
path("reservations/", include("apps.reservations.urls"))
```

If that app defines its own URL namespace, DRF's `NamespaceVersioning` still
uses the final namespace component as the API version: keep the v1 URL setup
and version tests consistent, or explicitly design a different versioning
scheme before adding nested namespaces. The simplest Phase 1 convention is
app-local URL names prefixed by the module name without another namespace.
Add tests under `backend/tests/`, create migrations with
`python manage.py makemigrations reservations`, and run all verification checks.

## Recommended next phase

Review Phase 2 first. After explicit approval, Phase 3 can add a single
restaurant profile, menu catalogue, and tables. Do not add branches, tenancy,
subscriptions, memberships, a frontend, or later-phase workflows. Publishing
or merging also requires explicit approval.
