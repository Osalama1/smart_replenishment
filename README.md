## Smart Replenishment System

**Automated Inventory Replenishment for Pharmacy Supply Chains**

Smart Replenishment eliminates manual spreadsheet tracking by automatically analyzing inventory consumption patterns and generating intelligent purchase recommendations. The system monitors stock levels continuously, calculates optimal reorder points, and alerts you before stockouts occur—with special consideration for delivery lead times.

---

## 🎯 What Problem Does This Solve?

### Before Smart Replenishment
- ❌ Manual spreadsheet tracking of inventory levels
- ❌ Reactive ordering—discover shortages too late
- ❌ No consideration for supplier delivery times
- ❌ Overstocking or emergency rush orders
- ❌ Multiple people checking stock daily
- ❌ Missed sales due to stockouts
- ❌ No historical consumption analysis

### After Smart Replenishment
- ✅ Automated monitoring of all inventory items
- ✅ Proactive alerts before stockouts occur
- ✅ Lead-time-aware ordering (knows if you’ll run out during delivery)
- ✅ Optimal stock levels—not too much, not too little
- ✅ System works 24/7 in the background
- ✅ Never miss a sale due to stockout
- ✅ Data-driven decisions based on real consumption

---

## 💡 How It Works

```
1. MONITOR → 2. CALCULATE → 3. RECOMMEND → 4. ORDER
```

### Step 1: Continuous Monitoring
The system watches every stock movement: sales, deliveries, internal consumption, warehouse transfers. Result: real-time understanding of actual consumption patterns.

### Step 2: Intelligent Calculation
Daily analysis of consumption, supplier lead time, and safety buffers generates item-level reorder points per warehouse.

### Step 3: Smart Recommendations
Hourly checks determine whether stock is below reorder levels, whether you’ll run out before delivery, urgency level, supplier choice, and cost impact.

### Step 4: Streamlined Ordering
Approve recommendations, auto-create Purchase Orders (single or batched), and track through fulfillment.

---

## 🎪 Key Features

### 1. Lead-Time-Aware Intelligence 🆕
Determines if you’ll run out before delivery by computing days until stockout, consumption during lead time, remaining stock when the order arrives, and days of coverage after delivery. Flags include:
- 🚨 Critical – Order Immediately
- ⚠️ Will Stockout Before Delivery
- 📊 Stock When Delivered

### 2. Warehouse-Specific Intelligence
Each warehouse receives its own consumption-based reorder point and quantity. High-traffic and low-traffic locations are handled appropriately.

### 3. Priority-Based Recommendations
Critical, High, Medium, Low priorities ensure planners act on the most urgent items first.

### 4. Pharmacy Compliance Tracking
Tracks prescription requirements, controlled substances (Schedules I–V), and storage temperatures to keep operations compliant.

### 5. Cost Visibility
Shows estimated unit and total costs before ordering to support budget control.

### 6. Batch Purchase Orders
Combine multiple recommendations for the same supplier to reduce shipping costs and streamline receiving.

---

## 👥 Who Uses What?

| Role | Responsibilities |
| --- | --- |
| Pharmacy / Inventory Manager | Review pending recommendations, approve priorities, monitor trends |
| Procurement Team | Create Purchase Orders, batch supplier orders, coordinate deliveries |
| Pharmacy Staff | View incoming orders, understand low-stock reasons |
| Finance Team | Monitor estimated costs, budget impact, spending trends |

---

## 📊 Understanding the Dashboard

Each recommendation card contains:
- **Header**: Item code/name, warehouse, status, priority
- **Stock Information**: Current stock, reorder point, average daily consumption, days until stockout
- **Lead Time Analysis**: Consumption during lead time, stock when delivered, days coverage after delivery, “Will Stockout Before Delivery”, “Critical – Order Immediately”
- **Recommendation Details**: Recommended quantity, material request type, reason text
- **Supplier Information**: Preferred/alternate supplier, lead time, costs, expected delivery date
- **Compliance**: Prescription required, controlled substance (schedule), storage temperature, drug category

---

## 🔄 Complete Workflow

### Daily Routine (10 minutes)
1. Filter for `Pending Review` + `Critical` recommendations.
2. Approve, adjust, or reject with reasons.
3. Create Purchase Orders (batch by supplier).

### Weekly Review (30 minutes)
Inspect stockout prevention success, consumption trends, supplier performance, and cost analysis.

### Monthly Planning (1 hour)
Adjust reorder parameters, evaluate suppliers, and optimize inventory levels.

---

## ⚙️ Configuration Guide

### Item Setup
- **Consumption Period**: 7–90 days depending on item lifecycle.
- **Safety Stock Days**: 3–14 days based on criticality.
- **Lead Time Days**: Supplier-specific, must be accurate.
- **Maximum Stock Level**: Based on capacity, shelf life, and cash flow.
- **Preferred Supplier**: Sets default vendor for recommendations.

### Warehouse Setup
- Override reorder levels and quantities per warehouse if needed.
- Set `Material Request Type` (Purchase, Transfer, Manufacture) per location.

---

## 📈 Success Metrics

| Metric | Before | After |
| --- | --- | --- |
| Daily stock review time | 2–3 hrs | <30 mins |
| Monthly stockouts | 5–8 | 0–1 |
| Emergency rush orders | 3–4 | 0–1 |
| Overstocked items | 20–30% | 5–10% |
| Staff time monitoring | 2 FTE | 0.5 FTE |

Operational KPIs: stockout rate <1%, order fulfillment >99%, inventory turnover 12–15x/year.

---

## 🎓 Training Recommendations

Week-one onboarding covers system overview, dashboard navigation, business logic, special scenarios, and hands-on practice. Monthly refreshers reinforce best practices.

---

## 🤝 Support & Help

**FAQ**
- *Why critical with stock on hand?* Because you’ll run out before delivery; check lead-time fields.
- *Can I order less?* Yes—set adjusted quantity and provide reason.
- *Supplier out of stock?* Select alternate supplier before PO creation.
- *Seasonal items?* Adjust safety stock days and maximum levels ahead of the season.

Escalation path: documentation → peer → Pharmacy Manager → IT Support.

---

## 💼 Business Value

### ROI Highlights
- 90% reduction in emergency orders.
- 15–20 weekly labor hours saved.
- 2–5% revenue increase via avoided stockouts.
- 20–30% reduction in excess inventory.

### Risk Mitigation
Prevents stockouts during health events, protects compliance, smooths cash flow, and reduces staff stress.

---

## 🔮 Future Enhancements

- Machine learning forecasting for seasonal demand.
- Supplier reliability scoring and analytics.
- Mobile approvals and critical alerts.
- Advanced dashboards and multi-currency support.
- Expiry-aware replenishment logic.

---

## 📋 Glossary

- **Reorder Point**: Trigger level including lead time demand + safety stock.
- **Lead Time**: Days from order to receipt.
- **Safety Stock**: Buffer for demand spikes or delays.
- **Consumption During Lead Time**: Units used while waiting for delivery.
- **Stock After Delivery**: Inventory remaining when new stock arrives.
- **Material Request Type**: Purchase, Transfer, or Manufacture route.
- **Urgency Score**: 0–100 severity rating.
- **Batch Purchase Order**: Single PO for multiple recommendations per supplier.

---

Built for modern pharmacy supply chain management  
Version 1.1.0 | January 2025

For API integration details, see `docs/API.md`. For field-level logic, refer to `docs/business_logic.md`.