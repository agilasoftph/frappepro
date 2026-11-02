# Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
# License: MIT. See license.txt

import unittest
from types import SimpleNamespace

from frappehero.accounts.invoice_types import (
	INVOICE_TYPE_OPTIONS,
	INVOICE_TYPE_OPTIONS_TEXT,
	InvoiceTypeError,
	apply_note_to_invoice,
	build_opening_invoice,
	invoice_type_spec,
	normalize_note_qty,
	prepare_opening_row,
)


class Tool:
	def __init__(self, invoice_type):
		self.invoice_type = invoice_type


class TestInvoiceTypes(unittest.TestCase):
	def test_options_list_credit_note_and_debit_note(self):
		self.assertEqual(INVOICE_TYPE_OPTIONS, ("Sales", "Purchase", "Credit Note", "Debit Note"))
		self.assertEqual(INVOICE_TYPE_OPTIONS_TEXT, "Sales\nPurchase\nCredit Note\nDebit Note")

	def test_credit_note_is_a_customer_sales_return(self):
		spec = invoice_type_spec("Credit Note")
		self.assertEqual(spec["party_type"], "Customer")
		self.assertEqual(spec["doctype"], "Sales Invoice")
		self.assertEqual(spec["base_type"], "Sales")
		self.assertTrue(spec["is_return"])

	def test_debit_note_is_a_supplier_purchase_return(self):
		spec = invoice_type_spec("Debit Note")
		self.assertEqual(spec["party_type"], "Supplier")
		self.assertEqual(spec["doctype"], "Purchase Invoice")
		self.assertEqual(spec["base_type"], "Purchase")
		self.assertTrue(spec["is_return"])

	def test_sales_and_purchase_are_unchanged(self):
		self.assertFalse(invoice_type_spec("Sales")["is_return"])
		self.assertFalse(invoice_type_spec("Purchase")["is_return"])
		self.assertEqual(invoice_type_spec("Sales")["party_type"], "Customer")
		self.assertEqual(invoice_type_spec("Purchase")["party_type"], "Supplier")

	def test_unknown_type_is_rejected(self):
		with self.assertRaises(InvoiceTypeError) as raised:
			invoice_type_spec("Receipt")
		self.assertEqual(raised.exception.invoice_type, "Receipt")

	def test_note_qty_becomes_a_positive_magnitude(self):
		self.assertEqual(normalize_note_qty(-2), 2)
		self.assertEqual(normalize_note_qty(0), 1)
		self.assertIsNone(normalize_note_qty(None))
		self.assertEqual(normalize_note_qty(""), "")

	def test_credit_note_borrows_sales_then_negates_the_amount(self):
		tool = Tool("Credit Note")
		row = SimpleNamespace(qty=-2, outstanding_amount=300, party_type=None)
		seen = []

		def parent_set_missing(current):
			seen.append(tool.invoice_type)
			current.party_type = "Customer" if tool.invoice_type == "Sales" else "Supplier"

		def parent_invoice(current):
			seen.append(tool.invoice_type)
			return {
				"doctype": "Sales Invoice" if tool.invoice_type == "Sales" else "Purchase Invoice",
				"items": [{"qty": current.qty, "rate": current.outstanding_amount / current.qty}],
			}

		prepare_opening_row(tool, row, parent_set_missing)
		invoice = build_opening_invoice(tool, row, parent_invoice)

		self.assertEqual(seen, ["Sales", "Sales"])
		self.assertEqual(tool.invoice_type, "Credit Note")
		self.assertEqual(row.party_type, "Customer")
		self.assertEqual(row.qty, 2)
		self.assertEqual(invoice["doctype"], "Sales Invoice")
		self.assertEqual(invoice["is_return"], 1)
		self.assertEqual(invoice["items"][0]["qty"], -2)
		self.assertEqual(invoice["items"][0]["rate"], 150)

	def test_negative_note_amount_still_posts_as_a_credit(self):
		invoice = apply_note_to_invoice(
			{"doctype": "Sales Invoice", "items": [{"qty": 1, "rate": -80}]},
			"Credit Note",
		)
		self.assertEqual(invoice["items"][0]["qty"], -1)
		self.assertEqual(invoice["items"][0]["rate"], 80)

	def test_debit_note_borrows_purchase(self):
		tool = Tool("Debit Note")
		row = SimpleNamespace(qty=1, outstanding_amount=40, party_type=None)

		def parent_invoice(current):
			self.assertEqual(tool.invoice_type, "Purchase")
			return {
				"doctype": "Purchase Invoice",
				"items": [{"qty": current.qty, "rate": current.outstanding_amount}],
			}

		invoice = build_opening_invoice(tool, row, parent_invoice)
		self.assertEqual(tool.invoice_type, "Debit Note")
		self.assertEqual(invoice["doctype"], "Purchase Invoice")
		self.assertEqual(invoice["is_return"], 1)
		self.assertEqual(invoice["items"][0]["qty"], -1)
		self.assertEqual(invoice["items"][0]["rate"], 40)

	def test_sales_invoice_keeps_a_positive_amount(self):
		tool = Tool("Sales")
		row = SimpleNamespace(qty=3, outstanding_amount=90, party_type=None)

		def parent_set_missing(current):
			current.party_type = "Supplier"

		def parent_invoice(current):
			return {"doctype": "Sales Invoice", "items": [{"qty": current.qty, "rate": 30}]}

		prepare_opening_row(tool, row, parent_set_missing)
		invoice = build_opening_invoice(tool, row, parent_invoice)
		self.assertEqual(row.party_type, "Customer")
		self.assertEqual(invoice["is_return"], 0)
		self.assertEqual(invoice["items"][0]["qty"], 3)
		self.assertEqual(invoice["items"][0]["rate"], 30)

	def test_selected_type_is_restored_when_building_fails(self):
		tool = Tool("Debit Note")

		def boom(row):
			raise RuntimeError("missing account")

		with self.assertRaises(RuntimeError):
			build_opening_invoice(tool, SimpleNamespace(), boom)
		self.assertEqual(tool.invoice_type, "Debit Note")
