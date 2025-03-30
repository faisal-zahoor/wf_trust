// Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Waterfall Invoice", {
    refresh(frm) {
        frm.set_query("invoice_from", function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });

        frm.set_query("invoice_to", function() {
            return {
                filters: {
                    company: frm.doc.company
                }
            };
        });

		if (frm.doc.docstatus > 0) {
			cur_frm.add_custom_button(
				__("Accounting Ledger"),
				function () {
					frappe.route_options = {
						voucher_no: frm.doc.journal_entry,
						from_date: frm.doc.due_date,
						to_date: moment(frm.doc.modified).format("YYYY-MM-DD"),
						company: frm.doc.company,
						group_by: "Group by Voucher (Consolidated)",
						show_cancelled_entries: frm.doc.docstatus === 2,
					};
					frappe.set_route("query-report", "General Ledger");
				},
				__("View")
			);
		}
    },
    
    payment_terms_template(frm) {
		const doc = frm.doc;
		if(doc.payment_terms_template) {
			let due_date = doc.due_date;
			
			frappe.call({
				method: "erpnext.controllers.accounts_controller.get_payment_terms",
				args: {
					terms_template: doc.payment_terms_template,
					posting_date: due_date,
					grand_total: doc.total_amount,
					base_grand_total: doc.total_amount,
					bill_date: due_date
				},
				callback: function(r) {
					if(r.message && !r.exc) {
						frm.set_value("payment_schedule", r.message);
					}
				}
			})
		}
	}
});
