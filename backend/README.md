# RMS backend — Phase 1 foundation

Python 3.12+, Django 5.2 LTS, Django REST Framework, and PostgreSQL. Python 3.12
is the team's recommended baseline and the CI version. Frontend selection is
deferred. No ordering, kitchen, POS, payment, inventory, or dashboard features
are implemented. There are no registration, token, or API login workflows.

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
`migrations/` package. Only accounts has a model and initial migration. Core
also contains operational views and URLs. Other modules are empty foundations.

| App | Responsibility when developed | Phase 1 content |
| --- | --- | --- |
| core | Small, genuinely shared infrastructure and operational probes | Health endpoints |
| accounts | User identity and future account policies | `User(AbstractUser)` and standard Django admin |
| restaurants | Restaurant profiles, branches, and future memberships | App skeleton |
| menu | Menu catalogue and availability | App skeleton |
| orders | Orders, line items, and order lifecycle | App skeleton |
| kitchen | Preparation and kitchen state | App skeleton |
| billing | Invoices, taxes, and payment records | App skeleton |
| inventory | Stock and stock movements | App skeleton |

Keep domain validation close to its models and use focused serializers/views
when APIs are added. Introduce services for concrete transactional operations
when needed. Core must not become a container for unrelated business logic.
Reference users with `settings.AUTH_USER_MODEL` in model relationships and
`get_user_model()` in runtime code. Do not import Django's built-in User model.

### Future multi-restaurant support

A later design phase should decide restaurant ownership, branches, membership,
and access policy. A shared-schema design could put explicit restaurant foreign
keys on business records, scope every queryset and write to an authorized
restaurant, and use restaurant-scoped uniqueness constraints. Users can then
belong to multiple restaurants through memberships instead of a single user
restaurant field. Cross-restaurant isolation must be tested on API reads,
writes, admin actions, tasks, and reports. Request-provided restaurant IDs alone
must never grant access. No tenant schema, filtering, membership, roles, or
restaurant models are implemented in this phase.

## Local setup

Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Set-Location backend
python -m pip install -r requirements/development.txt
Copy-Item .env.example .env
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated value into `DJANGO_SECRET_KEY` in `.env`, enclosed in single
quotes. Set a separate database password below. Both values are required;
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
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8000
```

`createsuperuser` is optional for local admin access; no default account is
created. Django's admin is at `http://127.0.0.1:8000/admin/`. This is a
computer-local development address, not a public deployment.

## API and settings

| Route | Behavior |
| --- | --- |
| `GET /api/v1/health/` | Public liveness, no database query; `200 {"status":"ok","version":"v1"}` |
| `GET /api/v1/health/ready/` | Public database readiness; `SELECT 1`, returns 200 or generic 503 |
| `/admin/` | Built-in staff-only Django admin |

No business endpoints, unversioned aliases, API login, or v2 routes exist.
Readiness confirms connectivity, not migration freshness; run `migrate --check`
as part of release verification. Both probes support HEAD and OPTIONS and
reject writes. Database exception details are omitted from responses and logs.

`config.urls` owns the `/api/v1/` namespace. `config.api_urls` is the central
registry for future app URLs. DRF uses `NamespaceVersioning`, JSON responses
and request bodies, and `IsAuthenticated` by default. Only health probes
explicitly allow anonymous access. The standard session authentication class
is a foundation, not a selected React/Flutter authentication design. Browser
credential sharing is disabled until that design is agreed and tested.

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
Do not submit the domain to preload lists automatically. Admin login rate
limiting/access restrictions, backups, monitoring, hosting, and deployment
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
They cover custom user persistence/admin registration, module configuration,
secret validation, production security, API routing/versioning/permissions,
database readiness failure, liveness independence, and browser CORS/preflight.

`.github/workflows/backend.yml` provides the same core checks on GitHub with
an isolated PostgreSQL service, an ephemeral Django secret, and a clearly
disposable CI database password. It also checks production configuration and
static collection. No production credentials are stored in the workflow.

## Three-developer GitHub workflow

This workspace was empty. Phase 1 is prepared on
`feature/django-backend-boilerplate`, with `origin` pointing to
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

Review and merge this foundation first. Then design accounts, restaurant
membership/ownership, authorization boundaries, and the frontend authentication
contract with all three developers. Approve that design before implementing
authentication or restaurant business features.
