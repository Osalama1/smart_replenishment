from __future__ import annotations

import json
from typing import List, Optional, Sequence

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, flt, getdate, now


class ReplenishmentRecommendation(Document):
    """
    Transactional document representing an actionable replenishment recommendation.
    """

    def validate(self) -> None:
        self.validate_quantities()
        self.validate_supplier()
        self.calculate_estimated_cost()
        self.calculate_expected_delivery()
        self.set_risk_indicators()
        self.validate_status_transitions()

    def before_save(self) -> None:
        self.last_modified_date = now()
        if not self.created_by_user:
            self.created_by_user = frappe.session.user

    def on_update(self) -> None:
        self.update_item_last_recommendation_date()

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------
    def validate_quantities(self) -> None:
        if flt(self.recommended_quantity) <= 0:
            frappe.throw(_("Recommended Quantity must be greater than zero."))

        if self.adjusted_quantity is not None and flt(self.adjusted_quantity) < 0:
            frappe.throw(_("Adjusted Quantity cannot be negative."))

        if self.adjusted_quantity:
            diff_percent = abs(self.adjusted_quantity - self.recommended_quantity) / max(
                self.recommended_quantity, 1
            ) * 100
            if diff_percent > 50:
                frappe.msgprint(
                    _("Adjusted quantity differs by {0:.1f}% from recommended quantity.").format(
                        diff_percent
                    ),
                    indicator="orange",
                    alert=True,
                )

    def validate_supplier(self) -> None:
        if self.status == "Approved" and not self.supplier:
            frappe.throw(_("Select a supplier before approving the recommendation."))

        if self.supplier:
            supplier_item_exists = frappe.db.exists(
                "Item Supplier",
                {"parent": self.item_code, "supplier": self.supplier},
            )
            if not supplier_item_exists and not self.alternate_supplier:
                frappe.msgprint(
                    _(
                        "Supplier {0} is not linked to item {1}. Consider setting an alternate supplier."
                    ).format(self.supplier, self.item_code),
                    indicator="yellow",
                    alert=True,
                )

    def validate_status_transitions(self) -> None:
        if self.is_new():
            return

        previous = self.get_doc_before_save()
        old_status = previous.status
        new_status = self.status

        allowed_transitions = {
            "Draft": ["Pending Review", "Cancelled"],
            "Pending Review": ["Approved", "Rejected", "Draft", "Cancelled"],
            "Approved": ["PO Created", "Cancelled"],
            "Rejected": ["Draft"],
            "PO Created": ["Completed", "Cancelled"],
            "Completed": [],
            "Cancelled": [],
        }

        if new_status != old_status:
            if new_status not in allowed_transitions.get(old_status, []):
                frappe.throw(
                    _("Cannot change status from {0} to {1}.").format(old_status, new_status)
                )

            if new_status == "Approved":
                self.reviewed_by = frappe.session.user
                self.reviewed_date = now()
            elif new_status == "Rejected":
                self.rejected_by = frappe.session.user
                self.rejection_date = now()
                if not self.rejection_reason:
                    frappe.throw(_("Please provide a rejection reason."))

    # ------------------------------------------------------------------
    # Calculations
    # ------------------------------------------------------------------
    def calculate_estimated_cost(self) -> None:
        if not self.estimated_unit_cost:
            last_rate = frappe.db.get_value("Item", self.item_code, "last_purchase_rate")
            if not last_rate:
                last_rate = frappe.db.get_value("Item", self.item_code, "standard_rate")
            self.estimated_unit_cost = flt(last_rate, 2) if last_rate else 0

        qty = flt(self.adjusted_quantity or self.recommended_quantity or 0)
        self.estimated_total_cost = flt(self.estimated_unit_cost * qty, 2) if qty else 0

    def calculate_expected_delivery(self) -> None:
        if not self.expected_delivery_date and self.supplier_lead_time_days:
            base_date = self.recommendation_date or getdate()
            self.expected_delivery_date = add_days(base_date, self.supplier_lead_time_days)

    def set_risk_indicators(self) -> None:
        stock = flt(self.current_stock)
        days_to_stockout = flt(self.days_until_stockout or 0)

        if stock <= 0:
            self.stockout_risk_level = "Critical"
            self.urgency_score = 100
            return

        if days_to_stockout <= 0:
            risk = "High"
            score = 80
        elif days_to_stockout < 3:
            risk = "Critical"
            score = 90
        elif days_to_stockout < 7:
            risk = "High"
            score = 70
        elif days_to_stockout < 14:
            risk = "Medium"
            score = 50
        else:
            risk = "Low"
            score = 30

        if self.is_controlled_substance:
            score = min(score + 10, 100)

        self.stockout_risk_level = risk
        self.urgency_score = score

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------
    def update_item_last_recommendation_date(self) -> None:
        if frappe.db.has_column("Item", "last_replenishment_recommendation"):
            frappe.db.set_value(
                "Item",
                self.item_code,
                "last_replenishment_recommendation",
                self.recommendation_date,
            )

    # ------------------------------------------------------------------
    # Whitelisted actions
    # ------------------------------------------------------------------
    @frappe.whitelist()
    def approve_recommendation(self) -> bool:
        if self.status != "Pending Review":
            frappe.throw(_("Only recommendations in Pending Review can be approved."))

        self.status = "Approved"
        self.reviewed_by = frappe.session.user
        self.reviewed_date = now()
        self.save()
        frappe.msgprint(_("Recommendation approved successfully."), indicator="green")
        return True

    @frappe.whitelist()
    def reject_recommendation(self, reason: str) -> bool:
        if self.status != "Pending Review":
            frappe.throw(_("Only recommendations in Pending Review can be rejected."))
        if not reason:
            frappe.throw(_("Please provide a rejection reason."))

        self.status = "Rejected"
        self.rejected_by = frappe.session.user
        self.rejection_date = now()
        self.rejection_reason = reason
        self.save()
        frappe.msgprint(_("Recommendation rejected."), indicator="red")
        return True

    @frappe.whitelist()
    def create_purchase_order(self, batch_items: Optional[Sequence[str]] = None) -> str:
        if self.status != "Approved":
            frappe.throw(_("Only approved recommendations can be converted to Purchase Orders."))
        if self.purchase_order:
            frappe.throw(_("Purchase Order {0} already linked.").format(self.purchase_order))
        if not self.supplier:
            frappe.throw(_("Select a supplier before creating a Purchase Order."))

        items = self._collect_po_items(batch_items=batch_items)

        po = frappe.get_doc(
            {
                "doctype": "Purchase Order",
                "supplier": self.supplier,
                "transaction_date": getdate(),
                "schedule_date": items[0]["schedule_date"],
                "items": items,
            }
        )
        po.insert()

        self._update_po_linkage(po.name, items[0]["qty"], "Manual" if not batch_items else "Batch")

        if batch_items:
            self._update_batch_recommendations(po.name, batch_items)

        frappe.msgprint(
            _("Purchase Order {0} created with {1} item(s).").format(po.name, len(items)),
            indicator="green",
        )
        return po.name

    # ------------------------------------------------------------------
    # Internal helpers for PO creation
    # ------------------------------------------------------------------
    def _collect_po_items(self, batch_items: Optional[Sequence[str]] = None) -> List[dict]:
        schedule_date = self.expected_delivery_date or add_days(
            getdate(), self.supplier_lead_time_days or 7
        )
        items = [
            {
                "item_code": self.item_code,
                "qty": flt(self.adjusted_quantity or self.recommended_quantity),
                "rate": flt(self.estimated_unit_cost),
                "warehouse": self.warehouse,
                "schedule_date": schedule_date,
            }
        ]

        if batch_items:
            for rec_name in batch_items:
                if rec_name == self.name:
                    continue
                rec = frappe.get_doc("Replenishment Recommendation", rec_name)
                if rec.status != "Approved" or rec.supplier != self.supplier or rec.purchase_order:
                    continue
                rec_schedule = rec.expected_delivery_date or add_days(
                    getdate(), rec.supplier_lead_time_days or 7
                )
                items.append(
                    {
                        "item_code": rec.item_code,
                        "qty": flt(rec.adjusted_quantity or rec.recommended_quantity),
                        "rate": flt(rec.estimated_unit_cost),
                        "warehouse": rec.warehouse,
                        "schedule_date": rec_schedule,
                    }
                )
        return items

    def _update_po_linkage(self, po_name: str, qty: float, method: str) -> None:
        self.status = "PO Created"
        self.purchase_order = po_name
        self.purchase_order_date = getdate()
        self.actual_order_quantity = qty
        self.actual_order_cost = flt(self.estimated_unit_cost) * qty
        self.po_creation_method = method
        self.save()

    def _update_batch_recommendations(self, po_name: str, batch_items: Sequence[str]) -> None:
        for rec_name in batch_items:
            if rec_name == self.name:
                continue
            rec = frappe.get_doc("Replenishment Recommendation", rec_name)
            if rec.status != "Approved" or rec.supplier != self.supplier:
                continue
            qty = flt(rec.adjusted_quantity or rec.recommended_quantity)
            rec.status = "PO Created"
            rec.purchase_order = po_name
            rec.purchase_order_date = getdate()
            rec.actual_order_quantity = qty
            rec.actual_order_cost = flt(rec.estimated_unit_cost) * qty
            rec.po_creation_method = "Batch"
            rec.save()


@frappe.whitelist()
def bulk_approve_recommendations(recommendation_names: Sequence[str]) -> dict:
    names = _ensure_list(recommendation_names)
    approved = 0
    failed = []

    for name in names:
        try:
            doc = frappe.get_doc("Replenishment Recommendation", name)
            doc.approve_recommendation()
            approved += 1
        except Exception as err:  # noqa: BLE001
            failed.append({"name": name, "error": str(err)})

    return {"success": approved, "failed": failed}


@frappe.whitelist()
def create_batch_purchase_order(recommendation_names: Sequence[str], supplier: str) -> dict:
    names = _ensure_list(recommendation_names)
    if not names:
        frappe.throw(_("Provide at least one recommendation to batch."))

    first_doc = frappe.get_doc("Replenishment Recommendation", names[0])
    if first_doc.supplier != supplier:
        frappe.throw(_("Supplied supplier does not match the first recommendation."))

    po_name = first_doc.create_purchase_order(batch_items=names)
    return {"purchase_order": po_name, "items_count": len(names)}


def _ensure_list(value: Sequence[str] | str) -> List[str]:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return [value]
    return list(value)

