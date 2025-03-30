# Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WaterfallInvoice(Document):
	def on_submit(self):
		issuer = self.invoice_from
		issuer_account = frappe.db.get_value("Waterfall Trust Party", issuer, "account")
		
		payer = self.invoice_to
		payer_account = frappe.db.get_value("Waterfall Trust Party", payer, "account")

		amount = self.total_amount

		jv_doc = frappe.get_doc({
			"doctype": "Journal Entry",
			"voucher_type": "Journal Entry",
			"company": self.company,
			"posting_date": self.due_date,
		}) 

		jv_doc.append("accounts", {
			"account": issuer_account,
			"debit_in_account_currency": amount,
		})

		jv_doc.append("accounts", {
			"account": payer_account,
			"credit_in_account_currency": amount,
		})

		jv_doc.save()
		jv_doc.submit()

		self.db_set("journal_entry", jv_doc.name)