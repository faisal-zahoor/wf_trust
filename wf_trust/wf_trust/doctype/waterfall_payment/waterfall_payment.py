# Copyright (c) 2025, NexTash (SMC-PVT) Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WaterfallPayment(Document):
	def validate(self):
		get_party_amounts(self)
		
	def on_submit(self):
		# Fetch trust parties in order
		trust_parties = frappe.db.sql("""
			SELECT name FROM `tabWaterfall Trust Party` ORDER BY party_order ASC
		""", as_dict=True)

		# Ensure there are at least 4 trust parties
		if len(trust_parties) < 4:
			frappe.throw("Insufficient trust parties defined. At least 4 required.")

		first_party, second_party, third_party, fourth_party = [p["name"] for p in trust_parties[:4]]

		# Fetch accounts for the trust parties
		party_accounts = frappe.db.sql("""
			SELECT name, account FROM `tabWaterfall Trust Party`
			WHERE name IN (%s)
		""" % ', '.join(['%s'] * len(trust_parties)), [p["name"] for p in trust_parties], as_dict=True)

		# Map party names to their accounts
		party_account_map = {party["name"]: party["account"] for party in party_accounts}

		# Assign accounts to respective parties
		first_party_account = party_account_map.get(first_party)
		second_party_account = party_account_map.get(second_party)
		third_party_account = party_account_map.get(third_party)
		fourth_party_account = party_account_map.get(fourth_party)

		# Create Journal Entry for payment distribution
		journal_entry = frappe.new_doc("Journal Entry")
		journal_entry.voucher_type = "Journal Entry"
		journal_entry.posting_date = self.posting_date
		journal_entry.company = self.company
		journal_entry.user_remark = f"Waterfall Payment for {self.name}"

		# Debit total amount to the 4th party and credit to the 3rd party
		journal_entry.append("accounts", {
			"account": fourth_party_account,
			"debit_in_account_currency": self.payment_amount,
		})

		journal_entry.append("accounts", {
			"account": third_party_account,
			"credit_in_account_currency": self.payment_amount
		})

		# Debit 2nd party amount from 3rd party and credit to 2nd party
		second_party_amount = sum(p.get("outstanding_amount", 0) for p in self.payment_split if p.get("party") == second_party)

		if second_party_amount > 0:
			journal_entry.append("accounts", {
				"account": third_party_account,
				"debit_in_account_currency": second_party_amount,
			})
			journal_entry.append("accounts", {
				"account": second_party_account,
				"credit_in_account_currency": second_party_amount
			})

		# Debit 1st party amount from 2nd party and credit to 1st party
		first_party_amount = sum(p.get("outstanding_amount", 0) for p in self.payment_split if p.get("party") == first_party)

		if first_party_amount > 0:
			journal_entry.append("accounts", {
				"account": second_party_account,
				"debit_in_account_currency": first_party_amount,
			})
			journal_entry.append("accounts", {
				"account": first_party_account,
				"credit_in_account_currency": first_party_amount
			})

		# Save and submit the journal entry
		journal_entry.insert()
		journal_entry.submit()
		
		self.db_set("journal_entry", journal_entry.name)

		# Process payment distribution to invoices
		for payment in self.payment_split:
			issuer = payment.get("party")
			amount_to_distribute = payment.get("outstanding_amount", 0)

			# Fetch payment schedules for the issuer, ordered by due date
			payment_schedules = frappe.db.sql("""
				SELECT 
					psi.name, psi.outstanding, psi.due_date
				FROM 
					`tabPayment Schedule` psi
				JOIN 
					`tabWaterfall Invoice` wi ON psi.parent = wi.name
				WHERE 
					wi.invoice_from = %(issuer)s
					AND psi.outstanding > 0
					AND psi.due_date <= %(invoice_due_date)s
				ORDER BY 
					psi.due_date ASC
			""", {"issuer": issuer, "invoice_due_date": self.invoice_due_date}, as_dict=True)

			# Distribute payments across schedules
			for schedule in payment_schedules:
				if amount_to_distribute <= 0:
					break

				outstanding = schedule.get("outstanding", 0)
				if outstanding > 0:
					allocated_amount = min(outstanding, amount_to_distribute)
					amount_to_distribute -= allocated_amount

					# Update the outstanding amount in the database
					frappe.db.set_value("Payment Schedule", schedule.get("name"), "outstanding", outstanding - allocated_amount)

	@frappe.whitelist()
	def get_party_due_amounts(self):	
		get_party_amounts(self)
		self.save()

def get_party_amounts(self):
    self.party_amounts = []
    self.payment_split = []

    # Fetch outstanding amounts grouped by invoice issuer
    results = frappe.db.sql("""
        SELECT 
            wi.invoice_from AS issuer,
            SUM(psi.outstanding) AS total_outstanding
        FROM 
            `tabPayment Schedule` psi
        JOIN 
            `tabWaterfall Invoice` wi ON psi.parent = wi.name
        JOIN
            `tabWaterfall Trust Party` wtp ON wi.invoice_from = wtp.party_name
        WHERE 
            psi.due_date <= %(invoice_due_date)s
        GROUP BY 
            wi.invoice_from
        ORDER BY
            wtp.party_order ASC
    """, {"invoice_due_date": self.invoice_due_date}, as_dict=True)

    # Convert results to a dictionary
    formatted_result = {row["issuer"]: row["total_outstanding"] or 0 for row in results}

    for issuer, outstanding in formatted_result.items():
        if outstanding > 0:
            self.append("party_amounts", {
                "party": issuer,
                "outstanding_amount": outstanding,
            })

    amounts_split = {issuer: 0 for issuer in formatted_result}

    trust_parties = frappe.db.sql("""
        SELECT name FROM `tabWaterfall Trust Party` ORDER BY party_order ASC
    """, as_dict=True)

    trust_party_names = [party["name"] for party in trust_parties]

    if len(trust_party_names) < 3:
        frappe.throw("Insufficient trust parties defined. At least 3 required.")

    first_party, second_party, third_party = trust_party_names[:3]

    # Calculate maximum allocation for first party
    total_amount = self.payment_amount or 0
    first_party_max = (total_amount * self.first_party_split) / 100

    # Allocate to first party
    first_party_due = formatted_result.get(first_party, 0)
    amounts_split[first_party] = min(first_party_due, first_party_max)
    total_amount -= amounts_split[first_party]

    # Allocate to second party
    second_party_due = formatted_result.get(second_party, 0)
    amounts_split[second_party] = min(second_party_due, total_amount)
    total_amount -= amounts_split[second_party]

    # Allocate remaining to third party
    if total_amount > 0:
        third_party_due = formatted_result.get(third_party, 0)
        amounts_split[third_party] = min(third_party_due, total_amount)

    # Append payment split data
    for issuer, amount in amounts_split.items():
        if amount > 0:
            self.append("payment_split", {
                "party": issuer,
                "outstanding_amount": amount,
            })

