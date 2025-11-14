from __future__ import annotations

import json
import logging
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, now

logger = logging.getLogger(__name__)

OPEN_RECOMMENDATION_STATUSES: Tuple[str, ...] = ("Draft", "Pending Review", "Approved")
DEFAULT_RECOMMENDATION_STATUS = "Pending Review"
DEFAULT_CALCULATION_METHOD = "Consumption-Based"
DEFAULT_MIN_CONSUMPTION = 1.0


@frappe.whitelist()
def calculate_reorder_points_all_items() -> Dict[str, object]:
    """Recalculate reorder information for all active stock items."""

    items = frappe.get_all(
        "Item",
        filters={"is_stock_item": 1, "disabled": 0},
        fields=["name", "item_code"],
    )

    updated = 0
    for item in items:
        try:
            calculate_item_reorder_levels(item.item_code)
            updated += 1
        except Exception:  # noqa: BLE001
            logger.exception("Failed calculating reorder for item %s", item.item_code)
            frappe.log_error(
                title="Reorder Calculation Error",
                message=f"Failed to calculate reorder for {item.item_code}",
            )

    return {"status": "success", "items_processed": updated}


def calculate_item_reorder_levels(
    item: Union[Document, str], method: Optional[str] = None
) -> None:
    """Calculate global and warehouse-specific reorder values for an item.

    Supports being called directly with an ``item_code`` string (scheduler/CLI)
    or via DocType hooks that pass the `Item` document.
    """

    item_code = item
    if isinstance(item, Document):
        item_code = item.name or item.get("item_code")

    if not item_code:
        frappe.throw(_("Unable to determine Item code for reorder calculation."))

    item_doc = frappe.get_doc("Item", item_code)

    calculation_days = flt(item_doc.get("consumption_calculation_period") or 30)
    if calculation_days <= 0:
        calculation_days = 30

    global_consumption = calculate_global_consumption(item_code, days=int(calculation_days))

    warehouses = get_warehouses_with_stock_history(item_code)
    for warehouse_row in warehouses:
        warehouse = warehouse_row.get("warehouse") if isinstance(warehouse_row, dict) else warehouse_row
        warehouse_consumption = calculate_warehouse_consumption(
            item_code, warehouse, days=int(calculation_days)
        )
        if warehouse_consumption > 0:
            update_warehouse_reorder_level(
                item_doc=item_doc,
                warehouse=warehouse,
                consumption=warehouse_consumption,
                lead_time=int(item_doc.get("lead_time_days") or 3),
                safety_days=int(item_doc.get("safety_stock_days") or 7),
            )

    global_reorder_point = calculate_global_reorder_point(
        avg_consumption=global_consumption,
        lead_time=int(item_doc.get("lead_time_days") or 3),
        safety_days=int(item_doc.get("safety_stock_days") or 7),
    )

    frappe.db.set_value(
        "Item",
        item_code,
        {
            "average_daily_consumption": global_consumption,
            "global_reorder_point": global_reorder_point,
            "last_consumption_update": getdate(),
        },
    )


def calculate_warehouse_consumption(item_code: str, warehouse: str, *, days: int = 30) -> float:
    """Average daily consumption for an item in a warehouse using Stock Ledger entries."""

    if days <= 0:
        days = 30

    from_date = add_days(getdate(), -days)
    consumption_data = frappe.db.sql(
        """
        SELECT ABS(SUM(actual_qty)) as total_consumed
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND warehouse = %s
          AND posting_date >= %s
          AND actual_qty < 0
          AND voucher_type IN ('Delivery Note', 'Sales Invoice', 'Stock Entry')
    """,
        (item_code, warehouse, from_date),
        as_dict=True,
    )

    total_consumed = consumption_data[0].get("total_consumed") if consumption_data else 0
    if not total_consumed:
        return 0.0

    return flt(total_consumed) / float(days)


def get_warehouses_with_stock_history(item_code: str) -> List[Dict[str, object]]:
    """Return warehouses that have stock activity for the given item in the last 90 days."""

    return frappe.db.sql(
        """
        SELECT DISTINCT warehouse
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
    """,
        (item_code,),
        as_dict=True,
    )


def update_warehouse_reorder_level(
    *,
    item_doc: Document,
    warehouse: str,
    consumption: float,
    lead_time: int,
    safety_days: int,
) -> None:
    """Create or update an Item Reorder entry for the given warehouse."""

    if lead_time <= 0:
        lead_time = 3
    if safety_days < 0:
        safety_days = 0

    safety_stock = consumption * safety_days
    reorder_level = (consumption * lead_time) + safety_stock

    max_stock_level = item_doc.get("maximum_stock_level")
    if not max_stock_level:
        max_stock_level = consumption * 30  # fallback to 30 days supply

    reorder_qty = max_stock_level - reorder_level + (consumption * lead_time)
    reorder_qty = max(reorder_qty, consumption * lead_time)

    existing_row = None
    for row in item_doc.get("reorder_levels") or []:
        if row.warehouse == warehouse:
            existing_row = row
            break

    material_request_type = (
        existing_row.material_request_type if existing_row and existing_row.material_request_type else "Purchase"
    )

    reorder_data = {
        "warehouse_reorder_level": flt(reorder_level, 2),
        "warehouse_reorder_qty": flt(reorder_qty, 2),
        "material_request_type": material_request_type,
    }

    if existing_row:
        frappe.db.set_value("Item Reorder", existing_row.name, reorder_data)
    else:
        reorder_doc = frappe.get_doc(
            {
                "doctype": "Item Reorder",
                "parent": item_doc.name,
                "parenttype": "Item",
                "parentfield": "reorder_levels",
                "warehouse": warehouse,
                **reorder_data,
            }
        )
        reorder_doc.insert(ignore_permissions=True)


def calculate_global_reorder_point(*, avg_consumption: float, lead_time: int, safety_days: int) -> float:
    safety_days = max(safety_days, 0)
    lead_time = max(lead_time, 1)
    safety_stock = avg_consumption * safety_days
    reorder_point = (avg_consumption * lead_time) + safety_stock
    return flt(reorder_point, 2)


def calculate_global_consumption(item_code: str, *, days: int = 30) -> float:
    if days <= 0:
        days = 30

    from_date = add_days(getdate(), -days)
    consumption_data = frappe.db.sql(
        """
        SELECT ABS(SUM(actual_qty)) as total_consumed
        FROM `tabStock Ledger Entry`
        WHERE item_code = %s
          AND posting_date >= %s
          AND actual_qty < 0
          AND voucher_type IN ('Delivery Note', 'Sales Invoice', 'Stock Entry')
    """,
        (item_code, from_date),
        as_dict=True,
    )

    total_consumed = consumption_data[0].get("total_consumed") if consumption_data else 0
    if not total_consumed:
        return get_default_consumption_estimate(item_code)

    return flt(total_consumed) / float(days)


def get_default_consumption_estimate(item_code: str) -> float:
    item_group = frappe.db.get_value("Item", item_code, "item_group")
    if not item_group:
        return DEFAULT_MIN_CONSUMPTION

    avg_group = frappe.db.sql(
        """
        SELECT AVG(average_daily_consumption) as avg_consumption
        FROM `tabItem`
        WHERE item_group = %s
          AND average_daily_consumption > 0
    """,
        (item_group,),
        as_dict=True,
    )

    avg_consumption = avg_group[0].get("avg_consumption") if avg_group else None
    if avg_consumption:
        return flt(avg_consumption)

    return DEFAULT_MIN_CONSUMPTION


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


@frappe.whitelist()
def generate_replenishment_recommendations(
    warehouse: Optional[str] = None,
    *,
    auto_approve: bool = False,
) -> Dict[str, object]:
    """Generate or refresh `Replenishment Recommendation` documents."""

    items = (
        get_items_with_reorder_level(warehouse=warehouse)
        if warehouse
        else get_all_items_with_reorder_levels()
    )

    created = 0
    updated = 0
    skipped = 0

    for item_row in items:
        try:
            if _create_or_update_recommendation(item_row, auto_approve=auto_approve):
                created += 1
            else:
                updated += 1
        except RecommendationSkipped:
            skipped += 1
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed processing recommendation for %s/%s",
                item_row.get("item_code"),
                item_row.get("warehouse"),
            )
            frappe.log_error(
                title="Recommendation Generation Error",
                message=f"Failed to generate recommendation for {item_row.get('item_code')}",
            )

    return {
        "status": "success",
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


class RecommendationSkipped(Exception):
    """Raised when recommendation should be skipped."""


def get_items_with_reorder_level(*, warehouse: str) -> List[Dict[str, object]]:
    return frappe.db.sql(
        """
        SELECT
            ir.name AS reorder_row_name,
            ir.parent AS item_code,
            ir.warehouse,
            ir.warehouse_reorder_level,
            ir.warehouse_reorder_qty,
            ir.material_request_type,
            i.item_name,
            i.preferred_supplier,
            i.lead_time_days,
            i.average_daily_consumption,
            i.maximum_stock_level,
            i.global_reorder_point,
            i.safety_stock_days,
            i.requires_prescription,
            i.is_controlled_substance,
            i.controlled_substance_schedule,
            i.storage_temperature,
            i.drug_category
        FROM `tabItem Reorder` ir
        INNER JOIN `tabItem` i ON ir.parent = i.name
        WHERE ir.warehouse = %s
          AND i.is_stock_item = 1
          AND i.disabled = 0
    """,
        (warehouse,),
        as_dict=True,
    )


def get_all_items_with_reorder_levels() -> List[Dict[str, object]]:
    return frappe.db.sql(
        """
        SELECT
            ir.name AS reorder_row_name,
            ir.parent AS item_code,
            ir.warehouse,
            ir.warehouse_reorder_level,
            ir.warehouse_reorder_qty,
            ir.material_request_type,
            i.item_name,
            i.preferred_supplier,
            i.lead_time_days,
            i.average_daily_consumption,
            i.maximum_stock_level,
            i.global_reorder_point,
            i.safety_stock_days,
            i.requires_prescription,
            i.is_controlled_substance,
            i.controlled_substance_schedule,
            i.storage_temperature,
            i.drug_category
        FROM `tabItem Reorder` ir
        INNER JOIN `tabItem` i ON ir.parent = i.name
        WHERE i.is_stock_item = 1
          AND i.disabled = 0
        ORDER BY i.item_code, ir.warehouse
    """,
        as_dict=True,
    )


def _create_or_update_recommendation(
    item_row: Dict[str, object],
    *,
    auto_approve: bool = False,
) -> bool:
    """Create or update a recommendation. Returns True when new doc created."""

    item_code = item_row.get("item_code")
    warehouse = item_row.get("warehouse")
    reorder_level = flt(item_row.get("warehouse_reorder_level") or 0)

    if not item_code or not warehouse or reorder_level <= 0:
        raise RecommendationSkipped

    current_stock = get_current_stock(item_code, warehouse)
    if current_stock > reorder_level:
        raise RecommendationSkipped

    recommendation_data = build_recommendation(item_row, current_stock)

    existing_name = frappe.db.get_value(
        "Replenishment Recommendation",
        {
            "item_code": item_code,
            "warehouse": warehouse,
            "status": ["in", list(OPEN_RECOMMENDATION_STATUSES)],
        },
        "name",
    )

    if existing_name:
        doc = frappe.get_doc("Replenishment Recommendation", existing_name)
        _apply_recommendation_values(doc, recommendation_data, auto_approve)
        doc.save(ignore_permissions=True)
        return False

    doc = frappe.get_doc({"doctype": "Replenishment Recommendation", **recommendation_data})
    doc.insert(ignore_permissions=True)

    if auto_approve and doc.status == "Pending Review":
        doc.approve_recommendation()

    return True


def build_recommendation(item_row: Dict[str, object], current_stock: float) -> Dict[str, object]:
    """Construct the payload used to create/update a recommendation document."""

    item_code = item_row.get("item_code")
    warehouse = item_row.get("warehouse")

    item_doc = frappe.get_doc("Item", item_code)

    reorder_level = flt(item_row.get("warehouse_reorder_level") or 0)
    reorder_qty = flt(item_row.get("warehouse_reorder_qty") or 0)

    recommended_qty = determine_recommended_quantity(
        item_doc=item_doc,
        reorder_qty=reorder_qty,
        reorder_level=reorder_level,
        current_stock=current_stock,
    )

    avg_consumption = flt(item_doc.get("average_daily_consumption") or DEFAULT_MIN_CONSUMPTION)
    days_until_stockout = (
        flt(current_stock / avg_consumption, 1) if avg_consumption > 0 else None
    )

    supplier = item_doc.get("preferred_supplier") or get_default_supplier(item_code)
    estimated_cost = get_estimated_cost(
        item_code=item_code,
        quantity=recommended_qty,
        supplier=supplier,
    )

    recommendation_date = getdate()
    priority = calculate_priority_from_stock_level(
        current_stock=current_stock,
        reorder_level=reorder_level,
        avg_consumption=avg_consumption,
    )

    urgency_score = calculate_urgency_score(current_stock=current_stock, reorder_level=reorder_level)

    reason = _format_reason(current_stock, reorder_level)

    payload = {
        "item_code": item_code,
        "item_name": item_row.get("item_name") or item_doc.item_name,
        "warehouse": warehouse,
        "recommendation_date": recommendation_date,
        "status": DEFAULT_RECOMMENDATION_STATUS,
        "priority": priority,
        "urgency_score": urgency_score,
        "current_stock": flt(current_stock, 2),
        "reorder_point": flt(reorder_level, 2),
        "minimum_stock_level": flt(item_doc.get("global_reorder_point") or reorder_level, 2),
        "maximum_stock_level": flt(item_row.get("maximum_stock_level") or item_doc.get("maximum_stock_level") or 0, 2),
        "average_daily_consumption": flt(avg_consumption, 3),
        "days_until_stockout": days_until_stockout,
        "safety_stock_days": item_row.get("safety_stock_days") or item_doc.get("safety_stock_days"),
        "recommended_quantity": recommended_qty,
        "material_request_type": item_row.get("material_request_type") or "Purchase",
        "reason_for_recommendation": reason,
        "supplier": supplier,
        "supplier_lead_time_days": item_row.get("lead_time_days") or item_doc.get("lead_time_days"),
        "estimated_unit_cost": flt(estimated_cost / recommended_qty, 2) if recommended_qty else 0,
        "estimated_total_cost": flt(estimated_cost, 2),
        "requires_prescription": item_doc.get("requires_prescription") or 0,
        "is_controlled_substance": item_doc.get("is_controlled_substance") or 0,
        "controlled_substance_schedule": item_doc.get("controlled_substance_schedule"),
        "storage_temperature": item_doc.get("storage_temperature"),
        "drug_category": item_doc.get("drug_category"),
        "calculation_method": DEFAULT_CALCULATION_METHOD,
        "source_warehouse_reorder": 1,
        "item_reorder_reference": item_row.get("reorder_row_name"),
        "auto_generated": 1,
        "created_by_user": frappe.session.user if frappe.session.user else "Administrator",
    }

    if days_until_stockout is not None and days_until_stockout < 0:
        payload["days_until_stockout"] = 0

    return payload


def _apply_recommendation_values(
    doc: Document,
    values: Dict[str, object],
    auto_approve: bool,
) -> None:
    for key, value in values.items():
        doc.set(key, value)

    # Reset adjustment fields when auto-generation updates recommendation
    doc.adjusted_quantity = None
    doc.quantity_adjustment_reason = None

    if auto_approve and doc.status == "Pending Review":
        doc.approve_recommendation()


def _format_reason(current_stock: float, reorder_point: float) -> str:
    return _(
        "Current stock {current} is at or below reorder point {reorder}."
    ).format(current=flt(current_stock, 2), reorder=flt(reorder_point, 2))


# ---------------------------------------------------------------------------
# Purchase Order integration & approvals
# ---------------------------------------------------------------------------


@frappe.whitelist()
def create_purchase_order_from_recommendation(
    recommendation_name: str,
    batch_names: Optional[Sequence[str]] = None,
) -> Dict[str, object]:
    """Create a Purchase Order from one (or batch) recommendation(s)."""

    doc = frappe.get_doc("Replenishment Recommendation", recommendation_name)

    if batch_names and isinstance(batch_names, str):
        try:
            batch_names = json.loads(batch_names)
        except json.JSONDecodeError:
            batch_names = [batch_names]

    po_name = doc.create_purchase_order(batch_items=batch_names)
    return {"status": "success", "purchase_order": po_name}


@frappe.whitelist()
def bulk_approve_recommendations(recommendation_names: Sequence[str]) -> Dict[str, object]:
    if isinstance(recommendation_names, str):
        try:
            recommendation_names = json.loads(recommendation_names)
        except json.JSONDecodeError:
            recommendation_names = [recommendation_names]

    approved = 0
    failed: List[Dict[str, str]] = []

    for name in recommendation_names:
        try:
            doc = frappe.get_doc("Replenishment Recommendation", name)
            doc.approve_recommendation()
            approved += 1
        except Exception as exc:  # noqa: BLE001
            failed.append({"name": name, "error": str(exc)})

    return {"status": "success", "approved": approved, "failed": failed}


# ---------------------------------------------------------------------------
# External API endpoint
# ---------------------------------------------------------------------------


@frappe.whitelist(allow_guest=False)
def get_replenishment_recommendations(
    filters: Optional[dict | str] = None,
    *,
    page: int = 1,
    page_size: int = 20,
    order_by: str = "urgency_score desc",
) -> Dict[str, object]:
    """Return recommendation records for external integrations."""

    filters_dict = _parse_filters(filters)

    page = max(page, 1)
    page_size = max(min(page_size, 200), 1)
    start = (page - 1) * page_size

    fields = [
        "name",
        "item_code",
        "item_name",
        "warehouse",
        "status",
        "priority",
        "urgency_score",
        "current_stock",
        "reorder_point",
        "recommended_quantity",
        "material_request_type",
        "supplier",
        "estimated_total_cost",
        "recommendation_date",
        "purchase_order",
    ]

    data = frappe.get_all(
        "Replenishment Recommendation",
        filters=filters_dict,
        fields=fields,
        limit_start=start,
        limit_page_length=page_size,
        order_by=order_by,
    )

    total = frappe.db.count("Replenishment Recommendation", filters=filters_dict)

    return {
        "status": "success",
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": data,
    }


def _parse_filters(filters: Optional[dict | str]) -> Dict[str, object]:
    if not filters:
        return {}

    if isinstance(filters, str):
        try:
            return json.loads(filters)
        except json.JSONDecodeError:
            frappe.throw(_("Filters must be valid JSON."))

    return dict(filters)


# ---------------------------------------------------------------------------
# Utility helpers reused in multiple places
# ---------------------------------------------------------------------------


def determine_recommended_quantity(
    *,
    item_doc: Document,
    reorder_qty: float,
    reorder_level: float,
    current_stock: float,
) -> float:
    if reorder_qty > 0:
        return flt(reorder_qty, 2)

    max_stock = item_doc.get("maximum_stock_level")
    if not max_stock:
        avg_consumption = item_doc.get("average_daily_consumption") or DEFAULT_MIN_CONSUMPTION
        max_stock = (avg_consumption or DEFAULT_MIN_CONSUMPTION) * 30

    desired_level = max_stock
    recommended_qty = desired_level - current_stock
    return flt(max(recommended_qty, 0), 2)


def calculate_priority_from_stock_level(
    *,
    current_stock: float,
    reorder_level: float,
    avg_consumption: float,
) -> str:
    if current_stock <= 0:
        return "Critical"
    if reorder_level <= 0:
        return "Medium"

    ratio = current_stock / reorder_level
    if ratio <= 0.5:
        return "Critical"
    if ratio <= 0.75:
        return "High"
    if ratio <= 1:
        return "Medium"
    return "Low"


def calculate_urgency_score(*, current_stock: float, reorder_level: float) -> float:
    if reorder_level <= 0:
        return 0.0
    percentage_below = ((reorder_level - current_stock) / reorder_level) * 100
    return flt(max(percentage_below, 0), 2)


def get_current_stock(item_code: str, warehouse: str) -> float:
    stock_qty = frappe.db.sql(
        """
        SELECT SUM(actual_qty) AS qty
        FROM `tabBin`
        WHERE item_code = %s
          AND warehouse = %s
    """,
        (item_code, warehouse),
        as_dict=True,
    )
    return flt(stock_qty[0].get("qty")) if stock_qty and stock_qty[0].get("qty") else 0.0


def get_default_supplier(item_code: str) -> Optional[str]:
    supplier = frappe.db.sql(
        """
        SELECT supplier
        FROM `tabItem Supplier`
        WHERE parent = %s
        ORDER BY idx
        LIMIT 1
    """,
        (item_code,),
        as_dict=True,
    )
    if supplier:
        return supplier[0].get("supplier")
    return None


def get_estimated_cost(
    *,
    item_code: str,
    quantity: float,
    supplier: Optional[str] = None,
) -> float:
    if quantity <= 0:
        return 0.0

    last_rate = frappe.db.get_value("Item", item_code, "last_purchase_rate")
    if not last_rate:
        last_rate = frappe.db.get_value("Item", item_code, "standard_rate")

    if not last_rate and supplier:
        supplier_rate = frappe.db.sql(
            """
            SELECT price_list_rate
            FROM `tabItem Price`
            WHERE item_code = %s
              AND supplier = %s
            ORDER BY valid_from DESC
            LIMIT 1
        """,
            (item_code, supplier),
            as_dict=True,
        )
        if supplier_rate:
            last_rate = supplier_rate[0].get("price_list_rate")

    if not last_rate:
        return 0.0

    return flt(last_rate) * flt(quantity)

