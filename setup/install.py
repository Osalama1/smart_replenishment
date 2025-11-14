from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


CUSTOM_FIELDS = {
    "Item": [
        {
            "fieldname": "pharmacy_inventory_section",
            "label": "Pharmacy Inventory Management",
            "fieldtype": "Section Break",
            "insert_after": "reorder_levels",
            "collapsible": 1,
            "description": "Global inventory settings. Use 'Auto re-order' table above for warehouse-specific levels.",
        },
        {
            "fieldname": "average_daily_consumption",
            "label": "Average Daily Consumption",
            "fieldtype": "Float",
            "insert_after": "pharmacy_inventory_section",
            "read_only": 1,
            "precision": 3,
            "description": "Global average calculated from all warehouses. Used to calculate warehouse-specific reorder levels.",
        },
        {
            "fieldname": "consumption_calculation_period",
            "label": "Consumption Period (Days)",
            "fieldtype": "Int",
            "insert_after": "average_daily_consumption",
            "default": "30",
            "description": "Number of days for consumption analysis.",
        },
        {
            "fieldname": "last_consumption_update",
            "label": "Last Calculation Date",
            "fieldtype": "Date",
            "insert_after": "consumption_calculation_period",
            "read_only": 1,
        },
        {
            "fieldname": "pharmacy_column_1",
            "fieldtype": "Column Break",
            "insert_after": "last_consumption_update",
        },
        {
            "fieldname": "global_reorder_point",
            "label": "Global Reorder Point",
            "fieldtype": "Float",
            "insert_after": "pharmacy_column_1",
            "read_only": 1,
            "precision": 2,
            "description": "Default reorder point. Overridden by warehouse-specific levels in table above.",
        },
        {
            "fieldname": "maximum_stock_level",
            "label": "Maximum Stock Level",
            "fieldtype": "Float",
            "insert_after": "global_reorder_point",
            "precision": 2,
            "description": "Maximum quantity to order (order up to this level).",
        },
        {
            "fieldname": "safety_stock_days",
            "label": "Safety Stock (Days)",
            "fieldtype": "Int",
            "insert_after": "maximum_stock_level",
            "default": "7",
            "description": "Buffer days for safety stock calculation.",
        },
        {
            "fieldname": "pharmacy_requirements_section",
            "label": "Pharmacy Requirements",
            "fieldtype": "Section Break",
            "insert_after": "safety_stock_days",
            "collapsible": 1,
        },
        {
            "fieldname": "requires_prescription",
            "label": "Requires Prescription",
            "fieldtype": "Check",
            "insert_after": "pharmacy_requirements_section",
            "default": "0",
        },
        {
            "fieldname": "is_controlled_substance",
            "label": "Controlled Substance",
            "fieldtype": "Check",
            "insert_after": "requires_prescription",
            "default": "0",
        },
        {
            "fieldname": "controlled_substance_schedule",
            "label": "Schedule",
            "fieldtype": "Select",
            "insert_after": "is_controlled_substance",
            "options": "\nSchedule I\nSchedule II\nSchedule III\nSchedule IV\nSchedule V",
            "depends_on": "eval:doc.is_controlled_substance==1",
        },
        {
            "fieldname": "pharmacy_column_2",
            "fieldtype": "Column Break",
            "insert_after": "controlled_substance_schedule",
        },
        {
            "fieldname": "storage_temperature",
            "label": "Storage Temperature",
            "fieldtype": "Select",
            "insert_after": "pharmacy_column_2",
            "options": "\nRoom Temperature\nRefrigerated (2-8°C)\nFrozen (-20°C)\nControlled Room Temperature",
        },
        {
            "fieldname": "drug_category",
            "label": "Drug Category",
            "fieldtype": "Select",
            "insert_after": "storage_temperature",
            "options": "\nAnalgesics\nAntibiotics\nAntidiabetics\nAntihypertensives\nCardiovascular\nDermatological\nGastrointestinal\nNeurological\nRespiratory\nVitamins & Supplements\nOther",
        },
        {
            "fieldname": "preferred_supplier_section",
            "label": "Preferred Replenishment Supplier",
            "fieldtype": "Section Break",
            "insert_after": "drug_category",
            "collapsible": 1,
            "description": "Default supplier for automatic replenishment orders.",
        },
        {
            "fieldname": "preferred_supplier",
            "label": "Preferred Supplier",
            "fieldtype": "Link",
            "insert_after": "preferred_supplier_section",
            "options": "Supplier",
            "description": "Primary supplier for replenishment recommendations.",
        },
        {
            "fieldname": "supplier_reliability_score",
            "label": "Reliability Score",
            "fieldtype": "Percent",
            "insert_after": "preferred_supplier",
            "read_only": 1,
            "description": "Calculated from delivery performance.",
        },
    ]
}


def ensure_custom_fields():
    if frappe.flags.in_install:
        frappe.clear_cache(doctype="Item")
    create_custom_fields(CUSTOM_FIELDS, update=True)



