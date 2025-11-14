## API Documentation

RESTful API endpoints for integrating external systems with Smart Replenishment.

---

## 🔐 Authentication

- **Required**: ERPNext token-based authentication.
- **Header Format**: `Authorization: token {API_KEY}:{API_SECRET}`.

Generate keys from **User Profile → API Access → Generate Keys**.

---

## 📡 Endpoint 1: Get Recommendations

Retrieve recommendations with filtering and pagination.

```
GET/POST /api/method/smart_replenishment.api.get_replenishment_recommendations
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filters` | JSON | No | Filter criteria object |
| `page` | Integer | No | Page number (default: 1) |
| `page_size` | Integer | No | Items per page (default: 20, max: 200) |
| `order_by` | String | No | Sort order (default: `"urgency_score desc"`) |

#### Filter Example

```json
{
  "status": "Pending Review",
  "priority": "Critical",
  "warehouse": "Stores - Company",
  "item_code": "ASPIRIN-100MG",
  "supplier": "ABC Pharma",
  "stockout_during_lead_time": 1,
  "critical_reorder_required": 1
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | String | Recommendation ID |
| `item_code` | String | Item identifier |
| `item_name` | String | Item description |
| `warehouse` | String | Warehouse |
| `status` | String | Workflow status |
| `priority` | String | Critical/High/Medium/Low |
| `urgency_score` | Float | 0–100 urgency metric |
| `current_stock` | Float | Current quantity |
| `reorder_point` | Float | Trigger level |
| `recommended_quantity` | Float | Suggested order amount |
| `days_until_stockout` | Float | Days before running out |
| `stock_after_delivery` | Float | Stock level when order arrives |
| `stockout_during_lead_time` | Boolean | Will run out before delivery |
| `critical_reorder_required` | Boolean | Must order immediately |
| `supplier` | String | Preferred supplier |
| `estimated_total_cost` | Currency | Total order cost |

---

## 📡 Endpoint 2: Generate Recommendations

Trigger manual recommendation generation.

```
POST /api/method/smart_replenishment.api.generate_replenishment_recommendations
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `warehouse` | String | No | Specific warehouse (omit for all) |
| `auto_approve` | Boolean | No | Auto-approve generated records (default: false) |

**Response**

```json
{
  "message": {
    "status": "success",
    "created": 15,
    "updated": 8,
    "skipped": 3
  }
}
```

---

## 📡 Endpoint 3: Create Purchase Order

Convert an approved recommendation into a Purchase Order.

```
POST /api/method/smart_replenishment.api.create_purchase_order_from_recommendation
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recommendation_name` | String | Yes | Recommendation document ID |
| `batch_names` | Array/String | No | Additional recommendation names for a batched PO |

**Requirements**
- Recommendation status must be `Approved`.
- Supplier must be set.
- Recommendation must not already have a linked Purchase Order.

**Response**

```json
{
  "message": {
    "status": "success",
    "purchase_order": "PO-2025-00045"
  }
}
```

---

## 📡 Endpoint 4: Bulk Approve

Approve multiple recommendations in one call.

```
POST /api/method/smart_replenishment.api.bulk_approve_recommendations
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `recommendation_names` | Array/String | Yes | List of recommendation IDs |

**Response**

```json
{
  "message": {
    "status": "success",
    "approved": 12,
    "failed": []
  }
}
```

---

## 🔒 Permissions

| Endpoint | Required Role |
|----------|---------------|
| Get Recommendations | Stock User (read) |
| Generate Recommendations | Stock Manager (write) |
| Bulk Approve / Create PO | Purchase Manager |

---

## ⚠️ Error Responses

| Code | Meaning |
|------|---------|
| 401 | Unauthorized – invalid credentials |
| 403 | Forbidden – insufficient permissions |
| 400 | Bad Request – invalid parameters |
| 404 | Not Found – document missing |

---

## ⚡ Rate Limits

- 100 requests per hour per API key.
- Burst allowance: 20 requests per minute.

---

For business logic and field breakdowns, see `BUSINESS_LOGIC.md`.

