# Phase 5: Kitchen Display System (KDS)

Implementation contract. Single restaurant; existing session/CSRF authentication and five roles remain unchanged.

## Domain design

- `KitchenTicket`: Maps 1:1 to an `OrderLine`. Only approved order lines can have kitchen tickets. Tracks the state of the line as it goes through the kitchen. Statuses: `preparing`, `ready`, `served`. The pending state is implicit (the lack of a `KitchenTicket` for an approved `OrderLine` implies it is pending).
- `KitchenEvent`: Tracks actors and timestamps for when a ticket transitioned into a particular state (`marked_preparing`, `marked_ready`, `marked_served`).

The system protects transitions:
- Waiters cannot start preparing items.
- Chefs cannot serve items.
- A ticket must be preparing to be ready, and ready to be served.
- Concurrent requests safely use `select_for_update` row locks in transaction atomic blocks.

## Implemented REST contract

Paths relative to `/api/v1/kitchen/`:

| Method/path | Roles | Result |
| --- | --- | --- |
| GET `tickets/?status=...` | Chef, Waiter, Manager, Owner | Fetches approved order lines. Optionally filtered by `pending`, `preparing`, `ready`, or `served`.
| POST `tickets/<line_id>/preparing/` | Chef | Marks the line as preparing. 200 OK.
| POST `tickets/<line_id>/ready/` | Chef | Marks the line as ready. 200 OK.
| POST `tickets/<line_id>/served/` | Waiter | Marks the line as served. 200 OK.

## Frontend

- `/kitchen`: Chef dashboard showing pending, preparing, ready, and served tickets grouped by sequence, allowing transitions.
- Waiter UI `/orders/waiter`: Augmented with a queue of "Ready for Service" items, allowing the waiter to see what the chef has finished and mark them as served.

## Phase 6 Integration Boundary

Phase 6 (Billing) can fetch the final state of the Order Lines by referencing `kitchen_ticket` for lines that have reached the `served` state. Unserved items shouldn't be billed yet.
