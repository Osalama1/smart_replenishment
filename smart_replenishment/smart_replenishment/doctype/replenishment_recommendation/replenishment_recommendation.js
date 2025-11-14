// Copyright (c) 2025, analyze inventory levels, consumption patterns, and supplier information to automatically generate purchase and contributors
// For license information, please see license.txt

frappe.ui.form.on("Replenishment Recommendation", {
    refresh(frm) {
        frm.trigger("set_priority_indicator");
        frm.trigger("toggle_action_buttons");
        frm.trigger("set_stock_highlights");
        frm.trigger("set_compliance_badges");
    },

    status(frm) {
        frm.trigger("toggle_action_buttons");
    },

    priority(frm) {
        frm.trigger("set_priority_indicator");
    },

    recommended_quantity(frm) {
        frm.trigger("recalculate_totals");
    },

    adjusted_quantity(frm) {
        frm.trigger("recalculate_totals");
    },

    set_priority_indicator(frm) {
        if (!frm.doc.priority) {
            frm.dashboard.clear_headline();
            return;
        }

        const colors = {
            Critical: "red",
            High: "orange",
            Medium: "yellow",
            Low: "blue",
        };

        frm.dashboard.add_indicator(
            __('Priority: {0}', [frm.doc.priority]),
            colors[frm.doc.priority] || "blue"
        );
    },

    toggle_action_buttons(frm) {
        frm.page.clear_actions_menu();
        frm.page.clear_primary_action();

        const status = frm.doc.status;

        if (!status || frm.is_new()) {
            return;
        }

        if (status === "Pending Review") {
            frm.add_custom_button(__('Approve'), () => frm.trigger('approve_recommendation'), __('Actions'));
            frm.add_custom_button(__('Reject'), () => frm.trigger('reject_recommendation'), __('Actions'));
        }

        if (status === "Approved") {
            frm.page.set_primary_action(__('Create Purchase Order'), () => frm.trigger('create_purchase_order'));
        }

        if (status === "PO Created" && frm.doc.purchase_order) {
            frm.add_custom_button(__('View Purchase Order'), () => {
                frappe.set_route('Form', 'Purchase Order', frm.doc.purchase_order);
            }, __('Actions'));
        }
    },

    set_stock_highlights(frm) {
        if (frm.doc.current_stock != null && frm.doc.reorder_point != null) {
            const delta = flt(frm.doc.reorder_point) - flt(frm.doc.current_stock);
            frm.dashboard.add_indicator(
                __('Below Reorder by {0}', [Math.max(delta, 0)]),
                delta > 0 ? "red" : "green"
            );
        }

        if (frm.doc.days_until_stockout) {
            let color = "blue";
            const days = flt(frm.doc.days_until_stockout);
            if (days < 3) color = "red";
            else if (days < 7) color = "orange";
            else if (days < 14) color = "yellow";

            frm.dashboard.add_indicator(
                __('Days Until Stock-out: {0}', [frm.doc.days_until_stockout]),
                color
            );
        }

        if (frm.doc.estimated_total_cost) {
            frm.dashboard.add_indicator(
                __('Estimated Cost: {0}', [format_currency(frm.doc.estimated_total_cost)]),
                "blue"
            );
        }
    },

    set_compliance_badges(frm) {
        if (frm.doc.is_controlled_substance) {
            frm.dashboard.add_indicator(__('Controlled Substance'), 'orange');
        }

        if (frm.doc.requires_prescription) {
            frm.dashboard.add_indicator(__('Requires Prescription'), 'red');
        }
    },

    recalculate_totals(frm) {
        const qty = flt(frm.doc.adjusted_quantity || frm.doc.recommended_quantity || 0);
        const rate = flt(frm.doc.estimated_unit_cost || 0);
        const total = qty * rate;
        frm.set_value('estimated_total_cost', total);
    },

    approve_recommendation(frm) {
        frappe.call({
            method: 'smart_replenishment.api.bulk_approve_recommendations',
            args: {
                recommendation_names: [frm.doc.name],
            },
            freeze: true,
            freeze_message: __('Approving recommendation...'),
            callback: () => {
                frm.reload_doc();
                frappe.show_alert({
                    message: __('Recommendation approved'),
                    indicator: 'green',
                });
            },
        });
    },

    reject_recommendation(frm) {
        frappe.prompt(
            {
                label: __('Rejection Reason'),
                fieldname: 'reason',
                fieldtype: 'Small Text',
                reqd: 1,
            },
            (values) => {
                frappe.call({
                    method: 'smart_replenishment.smart_replenishment.doctype.replenishment_recommendation.replenishment_recommendation.reject_recommendation',
                    args: {
                        name: frm.doc.name,
                        reason: values.reason,
                    },
                    freeze: true,
                    freeze_message: __('Rejecting recommendation...'),
                    callback: () => frm.reload_doc(),
                });
            },
            __('Reject Recommendation'),
            __('Reject')
        );
    },

    create_purchase_order(frm) {
        frappe.call({
            method: 'smart_replenishment.api.create_purchase_order_from_recommendation',
            args: {
                recommendation_name: frm.doc.name,
            },
            freeze: true,
            freeze_message: __('Creating Purchase Order...'),
            callback: (response) => {
                if (response.message && response.message.purchase_order) {
                    frappe.show_alert({
                        message: __('Purchase Order {0} created', [response.message.purchase_order]),
                        indicator: 'green',
                    });
                    frm.reload_doc();
                }
            },
        });
    },
});
