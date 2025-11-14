## Smart Replenishment

Smart Replenishment is an ERPNext/Frappe app designed for pharmacy supply-chain teams that need automated replenishment signals instead of spreadsheet-driven reorder planning. The app enriches the core `Item` DocType with pharmacy-specific fields, keeps average consumption data fresh, produces warehouse-level reorder points, and surfaces actionable `Replenishment Recommendation` documents that can be approved or converted into Purchase Orders.

### Highlights
- **Consumption-aware reorder points** – scheduled jobs recalculate global and warehouse consumption from Stock Ledger history and update `Item Reorder` rows.
- **Recommendation workflow** – hourly jobs create/update `Replenishment Recommendation` docs with urgency, priority, safety stock days, and supplier metadata; approvals and Purchase Order creation are handled from the same record.
- **Pharmacy-specific context** – fixtures add fields like storage temperature, controlled substance schedules, prescription requirements, and supplier reliability scores so planners see everything they need in one place.
- **External access** – an authenticated API (`/api/method/smart_replenishment.api.get_replenishment_recommendations`) exposes paginated recommendation data for downstream systems.

### Installation
```bash
bench get-app smart_replenishment https://github.com/Osalama1/smart_replenishment.git
bench --site your.site install-app smart_replenishment
```

> The app expects ERPNext (for stock-related DocTypes) and the bench scheduler to be enabled.

### Post-install Setup
- **Custom fields** – the fixtures declared in `hooks.py` automatically create the `Item-*` custom fields listed under `fixtures`. If you add more fields later, export fixtures again before deploying.
- **Scheduler** – ensure `bench enable-scheduler` is active for each site. The app registers:
  - `daily`: `smart_replenishment.api.calculate_reorder_points_all_items`
  - `hourly`: `smart_replenishment.api.generate_replenishment_recommendations`
- **Permissions** – grant access to the `Replenishment Recommendation` DocType (and to supplier/purchase roles) for the planners who will triage recommendations.

### Operations & Usage
- **On every Item save** (`doc_events` hook) the app recalculates that item’s reorder data via `calculate_item_reorder_levels`.
- **Manual recalculation** can be triggered anytime:
  ```bash
  bench --site your.site execute smart_replenishment.api.calculate_reorder_points_all_items
  bench --site your.site execute smart_replenishment.api.generate_replenishment_recommendations
  ```
- **Recommendation lifecycle**
  1. Scheduler (or manual command) creates/updates `Replenishment Recommendation` documents when on-hand stock is at/below `warehouse_reorder_level`.
  2. Planners review urgency, supplier, estimated costs, and safety-stock context before approving.
  3. Use `bulk_approve_recommendations` or the document action buttons to approve and optionally call `create_purchase_order_from_recommendation` to raise a Purchase Order.

### External API
- Endpoint: `POST /api/method/smart_replenishment.api.get_replenishment_recommendations`
- Query/body params:
  - `filters`: JSON dict or query string (e.g., `{"warehouse": "Pharmacy - WH"}`)
  - `page`, `page_size` (max 200), `order_by`
- Response payload contains pagination metadata plus the requested fields (status, priority, urgency score, quantities, supplier, estimated total cost, etc.).
- Authenticate using a valid ERPNext API key/secret pair or a logged-in session cookie.

### Development Notes
- Source lives in `apps/smart_replenishment/smart_replenishment/`.
- Primary logic is inside `smart_replenishment/api.py`; hooks/configuration live in `smart_replenishment/hooks.py`.
- When adding DocTypes or fixtures, run `bench --site your.site export-fixtures` to keep the repo in sync.
- Use the standard Frappe test runner: `bench --site your.site run-tests --app smart_replenishment`.

### License
MIT