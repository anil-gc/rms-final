# Development roadmap

Target: a small restaurant with a single location. Backend: Django/DRF and
PostgreSQL. Frontend undecided; build REST APIs independently. No branches,
multi-tenancy, subscriptions, or membership features are included.

| Phase | Scope | State |
| --- | --- | --- |
| 1 | Modular Django foundation, PostgreSQL, settings, v1 API, health, lint/tests | Complete and verified |
| 2 | Roles, Owner provisioning, staff PINs, secure sessions, rate limits, backend permissions | Complete and verified; awaiting approval |
| 3 | Single restaurant profile/settings, menu categories/items/prices/availability, tables/occupancy | Not started; requires approval |
| 4 | Waiter orders, table association, cashier approval for new/additional items, cancellations, transactional lifecycle | Not started |
| 5 | Single Chef display, approved items only, preparing/ready per item, waiter status, served tracking | Not started |
| 6 | Consolidated table bill, totals/discount/tax, payments, unique numbers, 80mm printing, PDFs, reprinting | Not started |
| 7 | Inventory, stock in/out/adjustments/history, validation, Owner/Manager only | Not started |
| 8 | Dashboards/reports, audit logs, integration/security/performance review | Not started |
| 9 | Deployment hardening, backups, monitoring, operations docs, pilot readiness | Not started |

Every phase starts with repository inspection and a small plan, implements
only that phase, adds relevant tests, runs checks, updates docs, and ends with
a completion report. Stop after the phase and wait for explicit approval.
Never automatically proceed to the next phase, push, or merge.

Business rules to enforce when their phase is authorized:

- Only Owner creates staff; staff PINs are securely hashed and protected.
- Waiter enters orders; Cashier approval is required before kitchen visibility.
- Additional items stay on the same table/order/bill and need new approval.
- One Chef marks individual approved items preparing/ready.
- Only Cashier prints or reprints bills, including thermal and PDF output.
- Only Owner/Manager access or adjust inventory.
- All access rules are enforced by backend APIs, not only by a frontend.
