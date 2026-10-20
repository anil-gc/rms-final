# Phase 3 — Restaurant, menu, and tables

One restaurant per deployment. JSON APIs under `/api/v1/`, except logo upload
which uses multipart. All endpoints require a valid, active, provisioned
Django session with the temporary PIN change completed. Use the existing
[CSRF bootstrap and cookie sequence](AUTHENTICATION.md); the React client
shares that transport. Unknown/read-only input fields are rejected.

## Access and lifecycle

| Action | Owner | Manager | Cashier / Waiter / Chef |
| --- | --- | --- | --- |
| Read profile / logo | Yes | Yes | Yes |
| Read active catalogue / tables | Yes | Yes | Yes |
| Read archived records | Yes | Yes | No |
| Create/edit/archive/reactivate profile, categories, items, tables | Yes | Yes | No |
| Upload/remove logo | Yes | Yes | No |
| Manage staff accounts | Existing Owner-only API | No | No |

Anonymous, inactive, legacy blank-role, and temporary-PIN users cannot read or
write Phase 3 resources. Superuser/staff flags do not grant role overrides.
Workspace writes use normal session/CSRF protection; unlike sensitive account
credential operations, they do not require Owner password re-confirmation.

Archiving is `PATCH {"is_active": false}`; reactivate with true. Category/item/
table records have no DELETE or PUT API. Archived names remain reserved, and
related records are protected by foreign keys. No user data or previous
migration is replaced. The restaurant profile cannot be deleted or archived
as a different row; changing its active flag keeps the singleton and its data.

## Routes

Paths below are relative to `/api/v1/`.

| Method | Path | Result |
| --- | --- | --- |
| GET | `restaurant/` | Profile, or 404 until configured |
| POST | `restaurant/` | Create once, 201; existing profile returns 400 without overwrite |
| PATCH | `restaurant/` | Edit profile, 200 |
| GET | `restaurant/logo/` | Authenticated PNG response, or 404 if unset |
| POST | `restaurant/logo/` | Multipart `logo` file; returns updated profile, 200 |
| DELETE | `restaurant/logo/` | Remove current logo, 204; profile remains |
| GET / POST | `menu/categories/` | List / create (201) |
| GET / PATCH | `menu/categories/<id>/` | Retrieve / update (200) |
| GET / POST | `menu/items/` | List / create (201) |
| GET / PATCH | `menu/items/<id>/` | Retrieve / update (200) |
| GET / POST | `tables/` | List / create (201) |
| GET / PATCH | `tables/<id>/` | Retrieve / update (200) |

Lists are ordered JSON arrays. Search/status/category filtering in the current
React UI filters these returned records locally. There is no pagination,
push update stream, order lookup, reservation, or business-report endpoint.
Refresh to read changes made on another device. Updates are serialized by row
locks and database invariants, but stale form drafts are not merged.

Create the profile before categories/tables. The server assigns their restaurant
foreign key; clients cannot select a restaurant ID. Items require an existing
category. Non-management reads exclude inactive tables and inactive categories/
items; an inactive category hides all its items. Direct reads of hidden records
return 404. Unavailable active items are still visible to staff.

## Fields and validation

Restaurant inputs: `name` (required, 150), `description` (optional, 2000),
`address` (optional, 500), `contact_phone` (optional, 30 characters; 7–15 digits
with common phone punctuation), `email` (optional, valid email), `currency`
(`NPR` only, defaults to NPR), `opening_time`, `closing_time`, `is_active`.
Times accept local `HH:MM[:SS]` in Asia/Kathmandu. Set both to different values
or clear both with null. A closing time earlier than opening represents an
overnight schedule; this is one daily interval, not a weekly/holiday scheduler.
The response adds read-only `id`, `logo_url` (protected relative API URL or
null), and `updated_at`. Logo management is separate from the JSON profile.

Category inputs: `name` (required, 100), `description` (optional, 500),
`sort_order` (0–32767, default 0), `is_active` (default true). Smaller sort
orders appear first, then name/ID. Category names are unique ignoring case
and surrounding whitespace, including archived records.

Item inputs: `name` (required, 150), `description` (optional, 1000), `category`
(existing category ID), `price` (positive decimal, at most 99,999,999.99 NPR,
two decimal places), `is_available` and `is_active` (default true). Send price
as a decimal string, e.g. `"240.75"`; it is stored and returned as a decimal,
not a binary float. Item names are case-insensitively unique within a category.
The response includes read-only `category_name`, `effective_available`, `id`,
and `updated_at`. Effective availability requires the item, category, and
restaurant to be active and the item's own availability enabled. Disabling
the restaurant changes effective availability without disabling account login.

Table inputs: `name` (required, 40; case-insensitively unique), `capacity`
(integer 1–50, default 2), `status` (`available` or `occupied`, default
available), `is_active` (default true). Response adds `id` and `updated_at`.
Mark an occupied table available before archiving; inactive tables cannot
be occupied. Occupancy is a manual Owner/Manager status with no order coupling.

Names are trimmed and cannot be blank. Database constraints enforce singleton,
currency, names, numeric ranges, and valid table states, including writes
outside the serializer. Duplicate/conflicting data produces 400. Related
deletions are protected. Django admin provides read-only inspection.

## Logo uploads

Only PNG, JPEG, and WebP raster images, at most 2 MB and at most 2048 pixels
on either side. Pillow verifies/decodes the actual content, applies orientation,
strips metadata, and writes a fresh PNG with a generated filename. SVG, invalid
images, oversized dimensions/files, and additional form fields are rejected.
The browser supplies the multipart boundary; do not set Content-Type manually.

Logos live in the ignored `backend/media/` directory. There is no public media
route: session/PIN permissions apply to delivery, which uses `image/png`,
no-store responses, and Django's nosniff middleware. Old files are removed after
a replacement/removal transaction commits. Deployment must provide persistent
storage shared by app workers and appropriate proxy upload limits. Original
uploads are never served. There is no generic attachment or remote-URL fetch API.

Implementation references: [DRF multipart parsing](https://www.django-rest-framework.org/api-guide/parsers/#multipartparser),
[Django constraints](https://docs.djangoproject.com/en/5.2/ref/models/constraints/),
and [Django uploaded-content guidance](https://docs.djangoproject.com/en/5.2/topics/security/#user-uploaded-content).

## Errors and development

- 400: invalid input, duplicate name, occupied-table archive, or missing setup.
- 403: missing/revoked session, role/PIN restriction, or failed CSRF.
- 404: unconfigured profile/logo, missing record, or staff-hidden archived record.
- 405: unsupported PUT or domain-record DELETE.
- 415: incorrect upload content type.

Account credential rate limits remain unchanged. All API records/responses use
no-store. Ordinary workspace reads/writes do not issue tokens or bypass session
expiry. Phase 3 does not add rate limits to general catalogue operations.

Install backend requirements (adds `Pillow==13.0.0`), run `python manage.py
migrate`, and use the existing frontend `npm ci` / Vite workflow. Only two new
initial migrations are needed: `restaurants/0001_initial.py` and
`menu/0001_initial.py`. Run the backend pytest suite, Ruff, Django checks and
migration checks; frontend lint, Vitest, and production build. See
[current verification and preview URLs](PROJECT_STATUS.md).

The Phase 3 branch is `feature/restaurant-menu-tables`, based on frontend commit
`64d0debd98652c411293795508935c2962cba140`, which already includes Phase 2.
The owner authorized publication as a stacked PR targeting
`feature/react-frontend`, while PR #1 remains open and unmerged. Merging either
PR, retargeting after parent integration, and Phase 4 need separate review and
authorization. No merge or Phase 4 work is part of this publication.
