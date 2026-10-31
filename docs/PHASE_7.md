# Phase 7: Inventory & Stock Management

## Overview
Phase 7 introduces a secure, concurrent, and transaction-safe inventory and stock management module to the Restaurant Management System (RMS). This phase allows the Owner and Manager to register ingredients, record purchase receipts, make manual stock adjustments, map menu items to ingredient recipes, and view a complete history of stock movements. Most importantly, it securely integrates with the existing Kitchen workflow so that configured recipes automatically consume inventory when items are marked "Served".

## Domain Models
The Inventory domain resides in `backend/apps/inventory/models.py`:

- **InventoryItem**: Represents a tracked ingredient or physical item (e.g., Rice, Cooking Oil). It includes fields for Name, Category, Minimum Stock Threshold, and Base Unit (kg, g, L, ml, pcs, pkt).
- **StockMovement**: Acts as the immutable stock movement ledger. Every stock-changing operation creates a record here (types: Opening Balance, Receipt, Stock In, Stock Out, Waste, Adjustment, Consumption).
- **RecipeIngredient**: Maps `MenuItem`s to `InventoryItem`s, specifying the exact quantity and unit required per serving of the menu item.

### Stock Balance Strategy
The system maintains the `current_quantity` on the `InventoryItem` model. This balance is protected via strict atomic updates (`F()` expressions) and pessimistic locking (`select_for_update()`) in standard stock movement services. An immutable `StockMovement` is recorded synchronously within the same transaction to guarantee the historical ledger matches the physical balance.

## Unit Conversions
The inventory system supports dimensional measurement units.
Valid conversions include:
- Mass: `kg` <-> `g` (1 kg = 1000 g)
- Volume: `L` <-> `ml` (1 L = 1000 ml)
- Count: `pcs`, `pkt` (no cross-conversions allowed).

All arithmetic uses `decimal.Decimal` with explicit rounding contexts. Conversion failures due to dimension mismatches result in transactional validation errors (`ValueError` / `ValidationError`).

## Recipe Management & Kitchen Integration
Menu Items can be mapped to one or more `RecipeIngredient`s. When an order line is transitioned to "Served" via the Kitchen workflow (`apps.kitchen.services.mark_served`):
1. The service checks if the `MenuItem` has tracked recipe ingredients.
2. For each tracked ingredient, it calculates the required deduction (`quantity * line.quantity`).
3. It validates compatibility, converts units, and deducts from `InventoryItem.current_quantity`.
4. It records a "Consumption" `StockMovement` tied to the specific OrderLine.

### Consumption Rules
- **No Early Deduction**: Stock is never consumed at Ordering, Cashier Approval, or Preparing stages.
- **Strict Stock Policy**: If the system lacks sufficient recorded inventory to serve an item, the transaction halts and rejects the "Served" status. This prevents silent corruption of stock and prevents negative inventory states. Managers must physically count and correct the stock via an Adjustment to proceed.
- **Exactly Once Guarantee**: Order lines record a unique consumption signature, preventing duplicate ledger deductions if `mark_served` is invoked repeatedly.
- **Untracked items**: Menu items without configured recipes bypass inventory logic and are served immediately.

## API Endpoints
Hosted under `/api/v1/inventory/`:
- `GET /items/`: List active inventory items (with low-stock filters).
- `POST /items/`: Create a new inventory item.
- `GET /items/{id}/`: Retrieve details and current balance.
- `POST /items/{id}/receive/`: Record a purchase receipt (Stock In).
- `POST /items/{id}/adjust/`: Record a physical count adjustment or manual out.
- `GET /movements/`: View the paginated, immutable stock ledger.
- `GET /recipes/`: View all configured menu recipes.
- `POST /recipes/`: Create a recipe ingredient mapping.
- `DELETE /recipes/{id}/`: Remove a recipe mapping.

## Permissions & Role Access
Security enforcement uses DRF class-based permission rules (`IsOwnerOrManager`):
- **Owner / Manager**: Can create, edit, receive, and adjust inventory, as well as configure recipes and view the ledger.
- **Waiter / Cashier / Chef**: Denied direct access to inventory mutations. (Chefs deduct inventory implicitly only through the validated `mark_served` Kitchen workflow).

## Testing and Quality Assurance
### Backend
- Extensive `pytest` suite testing all CRUD operations, permission boundaries, and decimal unit conversion edge cases.
- **Concurrency**: PostgreSQL isolation is verified with simulated concurrent consumption tests and `select_for_update()` integration on overlapping `mark_served` triggers. Transactions correctly rollback upon partial failures or insufficient stock conflicts.
- Applied migrations are safe and additive.

### Frontend
- Implemented responsive React views: `InventoryDashboard`, `InventoryItems`, `StockReceiving`, `StockAdjustments`, `RecipeManagement`, and `MovementHistory`.
- `vitest` tests cover the core components.
- CSRF issues in Playwright testing were resolved safely by assigning appropriate `DJANGO_CSRF_TRUSTED_ORIGINS`.

## Limitations & Future Considerations
- **No retroactive consumption**: Activating a recipe will not deduct stock for historically served orders.
- **Strict-Stock operational blocker**: Because negative stock is rejected, a restaurant that neglects to register a stock purchase might find Chefs unable to mark items "Served" in the system, even if the physical food was given to the customer. Future phases could introduce a "reconciliation allowance" if required.
- **Procurement**: Purchase receipts act only as operational inventory events. Supplier payables/invoicing and full accounting are not covered in this phase.
