## Business Logic & Field Explanation Guide

**Complete field-by-field explanation of how Smart Replenishment works**

This document explains every field, calculation, and business rule in the system—focused on **why** each exists, **what impact** it has, and **how** data flows through the system.

---

## 📊 Table of Contents

1. [Item Master Fields](#item-master-fields)
2. [Item Reorder Table Fields](#item-reorder-table-fields)
3. [Replenishment Recommendation Fields](#replenishment-recommendation-fields)
4. [Calculation Logic Flow](#calculation-logic-flow)
5. [Status Workflow](#status-workflow)
6. [Priority Determination](#priority-determination)
7. [Business Rules](#business-rules)
8. [Summary](#summary)

---

## 🏷️ Item Master Fields

These fields extend the standard ERPNext `Item` DocType with pharmacy-specific data that drives Smart Replenishment.

### Pharmacy Inventory Management

#### Average Daily Consumption

- **Type:** Float (read-only)  
- **Formula:** `total consumed (period) ÷ period days`
- **Purpose:** Baseline for reorder calculations based on stock ledger history.

**How it works**
1. Look back `consumption_calculation_period` days (default 30).
2. Sum negative Stock Ledger Entries (delivery, sales, stock issue).
3. Divide by period days.

**Business impact**
- Higher consumption → reorders sooner.
- Lower consumption → longer reorder cycles.
- Zero consumption → fallback to item group average or default `1.0`.

**Updates**
- Daily scheduled job (2 AM).
- Item save hook when consumption data available.
- Manual execution via `calculate_reorder_points_all_items`.

#### Consumption Period (Days)

- **Type:** Integer (default 30).
- **Purpose:** Sliding window length for consumption averaging.

| Scenario | Recommended Days | Note |
| --- | --- | --- |
| New item | 7–14 | Not enough history |
| Seasonal | 60–90 | Capture high/low swings |
| Stable item | 30 | Balanced |
| Promotional | 14 | React quickly |
| Slow mover | 60 | Smooth noise |

Shorter periods react faster but are noisy; longer periods are stable but slower to respond.

#### Last Calculation Date

- **Type:** Date (read-only).
- **Purpose:** Audit trail for when consumption/reorder values were last refreshed.
- **Action:** If stale (>7 days) ensure scheduler runs or recalc manually.

#### Global Reorder Point

- **Type:** Float (read-only).  
- **Formula:** `(average daily × lead time) + (average daily × safety days)`.

Acts as default trigger level when warehouse overrides are absent. Balances demand during lead time with buffer for uncertainty.

#### Maximum Stock Level

- **Type:** Float (user input).  
- **Purpose:** Upper bound for inventory to avoid overstocking/expiry.

Determine via capacity, shelf life, budget, and demand ceilings. Recommended order quantity uses this target.

#### Safety Stock Days

- **Type:** Integer (default 7).  
- **Purpose:** Buffer days beyond lead time consumption.

Increase for critical meds or unreliable suppliers; decrease for high-value low-risk SKUs.

### Pharmacy Requirements

#### Requires Prescription

Checkbox indicating regulatory control. Displayed on recommendations so planners account for compliance.

#### Controlled Substance / Schedule

Checkbox plus Schedule (I–V). Controlled items gain urgency adjustments, higher approvals, and potentially longer effective lead times.

#### Storage Temperature

Select: Room, Controlled Room, Refrigerated (2–8°C), Frozen (-20°C). Impacts capacity planning and whether recommended quantity is feasible.

#### Drug Category

Therapeutic category for reporting and seasonal planning (e.g., respiratory spikes in winter).

### Preferred Supplier

#### Preferred Supplier

Primary vendor auto-filled in recommendations. Choose based on price, reliability, terms.

#### Supplier Reliability Score

Calculated KPI combining on-time rate, lead time accuracy, order completeness, and quality issues. High score lets you reduce safety stock; low score suggests finding alternatives.

---

## 📋 Item Reorder Table Fields

Child table per warehouse, accessible under Item → Auto Reorder.

### Warehouse

Identifies location. Separate rules per warehouse for varying demand, capacity, and sourcing.

### Warehouse Reorder Level

Warehouse-specific trigger (consumption × lead time + safety). Overrides global reorder point to prevent both stockouts and overstock.

### Warehouse Reorder Qty

Target replenishment quantity per warehouse, considering max capacity and fulfillment method.

### Material Request Type

Select: Purchase, Material Transfer, Material Issue, Manufacture. Determines downstream workflow: buying from suppliers vs. transfers vs. internal consumption vs. production.

---

## 📝 Replenishment Recommendation Fields

Primary transactional DocType produced by the scheduler. Key sections:

### Basic Details

- **Naming Series**: `REPR-.YYYY.-`, etc.
- **Status**: Draft → Pending Review → Approved → PO Created → Completed/Cancelled/Rejected. Only valid transitions allowed.
- **Priority**: Critical/High/Medium/Low decided by stock vs reorder vs lead time (see [Priority Determination](#priority-determination)).
- **Urgency Score**: 0–100 numeric severity; includes adjustments for controlled substances and projected stockouts.

### Stock Information

- **Current Stock**: Real-time Bin quantity.
- **Average Daily Consumption**: Carried over from Item.
- **Days Until Stockout**: `current ÷ average daily`.
- **Consumption During Lead Time**: `average daily × lead time`.
- **Stock When Order Arrives**: `current - consumption during lead time`. Negative value = guaranteed outage before delivery.
- **Days Coverage After Delivery**: `stock when delivered ÷ average daily`.
- **Will Stockout Before Delivery**: Boolean flag if stock when delivered ≤ 0.
- **Critical – Order Immediately**: Boolean if `days until stockout ≤ lead time`.

### Recommendation Details

- **Recommended Quantity**: `maximum - current + consumption during lead time`, with minimum equal to one week of demand. Ensures inventory returns to max after delivery.
- **Adjusted Quantity / Reason**: Manual override plus mandatory justification, stored for audits and tuning.
- **Material Request Type / Supplier / Lead Time / Expected Delivery**: Carries forward to Purchase Orders or Stock Transfers.
- **Estimated Unit/Total Cost**: Based on last purchase or standard rate.

### Supplier Information

Preferred supplier (editable) plus derived lead time and expected delivery date.

### Lead Time Analysis (New)

Fields introduced to model in-transit consumption, survival, and coverage to ensure proactive action:

- Consumption During Lead Time
- Stock When Order Arrives
- Days Coverage After Delivery
- Will Stockout Before Delivery
- Critical – Order Immediately

---

## 🔄 Calculation Logic Flow

### Daily (2 AM) Consumption + Reorder Calculation
1. Fetch active stock items.
2. Compute average consumption over configured period.
3. Calculate global reorder point.
4. Update item fields.
5. For each warehouse with history, compute warehouse consumption, reorder level, and reorder quantity (`Item Reorder` table).

### Hourly Recommendation Generation
1. Fetch items with reorder rows.
2. For each item-warehouse pair:
   - Evaluate current stock vs reorder level.
   - Compute lead-time metrics and priority.
   - Build payload (quantity, supplier, urgency, reasoning).
3. Upsert `Replenishment Recommendation` (update existing open docs, avoid duplicates).
4. Set status to `Pending Review`.

### User Actions
- **Approve**: Valid only from `Pending Review`; records approver.
- **Create Purchase Order**: Requires status `Approved`, supplier set, no existing PO. Supports batch creation and records PO number/status.
- **Completion**: When stock received, recommendations move to `Completed`.

---

## 📋 Status Workflow

Valid transitions:

```
Draft → Pending Review → Approved → PO Created → Completed
   ↘ Cancelled                   ↘ Cancelled
Pending Review → Rejected → Draft (optional)
```

Rules ensure linear progression and require reasons for cancellations/rejections.

---

## ⚖️ Priority Determination

Decision tree:

1. `current_stock = 0` → Critical.
2. `days_until_stockout ≤ lead_time` → Critical.
3. `stock when order arrives ≤ 0` → Critical.
4. `days_until_stockout ≤ lead_time + safety_days` → High.
5. Else compare `current_stock / reorder_level`:
   - ≤ 0.5 → Critical
   - ≤ 0.75 → High
   - ≤ 1.0 → Medium
   - > 1.0 → Low

---

## 📜 Business Rules

1. **No duplicate open recommendations**: update existing `Draft/Pending/Approved` docs instead of creating new ones.
2. **Supplier required for PO creation**.
3. **Minimum order quantity**: at least seven days of supply.
4. **Status validation**: only allowed transitions.
5. **Adjustment requires reason** when overriding recommended quantity.
6. **Lead time must be positive**: defaults to 3 days if missing.
7. **Maximum stock must exceed reorder point**: warnings issued otherwise.
8. **Critical items boost urgency** based on control/prescription flags and projected stockout.

---

## 🎓 Summary

Smart Replenishment combines consumption analytics, lead-time modeling, and workflow enforcement to keep pharmacies stocked without tying up excess capital. Key takeaways:

- Consumption fields measure demand accurately.
- Reorder fields translate demand into triggers and quantities.
- Lead-time fields expose whether you survive until delivery.
- Priority/urgency fields help triage work.
- Supplier/cost fields support procurement execution.
- Business rules and workflows ensure compliance, auditability, and consistent operations.

For API specifics, see `README.md` and any dedicated API documentation. For testing procedures, refer to `TESTING.md`.

