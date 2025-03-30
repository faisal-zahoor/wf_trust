// Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on("Waterfall Trust Party", {
  setup(frm) {
    frm.set_query("account", function () {
      return {
        filters: {
          company: frm.doc.company,
          account_type: "Payable"
        },
      };
    });
  },
});
