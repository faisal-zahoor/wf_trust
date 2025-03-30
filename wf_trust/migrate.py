import frappe


def after_migrate():
    if not frappe.db.exists("Party Type", {"party_type": "Waterfall Trust Party"}):
        frappe.get_doc({
            "doctype": "Party Type",
            "party_type": "Waterfall Trust Party",
            "account_type": "Payable",
        }).save()