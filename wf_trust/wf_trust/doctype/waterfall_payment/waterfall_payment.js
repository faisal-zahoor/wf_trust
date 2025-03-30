// Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Waterfall Payment", {
  refresh(frm) {
    frm.add_custom_button(__("Fetch Split"), function () {
      frm.call("get_party_due_amounts");
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
});
