# Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
# License: MIT. See license.txt

"""Invoice types for the Opening Invoice Creation Tool.

Nothing in this module imports Frappe, so the mapping can be unit tested
without a site.

ERPNext only offers Sales and Purchase. A credit note is an opening customer
credit (Sales Invoice return). A debit note is an opening supplier debit
(Purchase Invoice return). The note amount is entered as a positive number;
the invoice is stored with a negative quantity so the party balance falls.
"""

from __future__ import annotations

INVOICE_TYPE_OPTIONS = ("Sales", "Purchase", "Credit Note", "Debit Note")

# Keep the desk script in public/js/opening_invoice_creation_tool.js in step
# with this list. The form reads the options from both places.
INVOICE_TYPE_OPTIONS_TEXT = "\n".join(INVOICE_TYPE_OPTIONS)

_SPECS = {
	"Sales": {
		"base_type": "Sales",
		"party_type": "Customer",
		"doctype": "Sales Invoice",
		"is_return": False,
	},
	"Purchase": {
		"base_type": "Purchase",
		"party_type": "Supplier",
		"doctype": "Purchase Invoice",
		"is_return": False,
	},
	"Credit Note": {
		"base_type": "Sales",
		"party_type": "Customer",
		"doctype": "Sales Invoice",
		"is_return": True,
	},
	"Debit Note": {
		"base_type": "Purchase",
		"party_type": "Supplier",
		"doctype": "Purchase Invoice",
		"is_return": True,
	},
}


class InvoiceTypeError(ValueError):
	def __init__(self, invoice_type: str):
		self.invoice_type = invoice_type
		super().__init__(invoice_type)


def invoice_type_spec(invoice_type: str) -> dict:
	try:
		return _SPECS[invoice_type]
	except KeyError as exc:
		raise InvoiceTypeError(invoice_type) from exc


def normalize_note_qty(qty):
	"""Turn a note quantity into a positive magnitude.

	The Opening Invoice Creation Tool rejects non-positive quantities before
	it builds the invoice. Notes are entered the same way; the sign is applied
	when the return invoice is assembled.
	"""
	if qty in (None, ""):
		return qty
	try:
		number = float(qty)
	except (TypeError, ValueError):
		return qty
	return abs(number) or 1.0


def prepare_opening_row(tool, row, set_missing_values) -> None:
	"""Fill a tool row, asking ERPNext for Sales or Purchase behaviour.

	``set_missing_values`` is the parent method. It looks up ``Sales Invoice
	Item`` or ``Purchase Invoice Item`` from ``tool.invoice_type``, so a note
	has to borrow its base type for that call and then restore the selection
	the user actually made.
	"""
	spec = invoice_type_spec(tool.invoice_type)
	if spec["is_return"]:
		row.qty = normalize_note_qty(getattr(row, "qty", None))
	original = tool.invoice_type
	tool.invoice_type = spec["base_type"]
	try:
		set_missing_values(row)
	finally:
		tool.invoice_type = original
	row.party_type = spec["party_type"]


def apply_note_to_invoice(invoice: dict, invoice_type: str) -> dict:
	"""Mark a note as a return and give it a negative quantity."""
	spec = invoice_type_spec(invoice_type)
	invoice["doctype"] = spec["doctype"]
	invoice["is_return"] = 1 if spec["is_return"] else 0
	if not spec["is_return"]:
		return invoice
	for item in invoice.get("items") or []:
		raw_qty = item.get("qty")
		magnitude = abs(_number(raw_qty, default=1.0)) or 1.0
		item["qty"] = -magnitude
		item["rate"] = abs(_number(item.get("rate"), default=0.0))
	return invoice


def build_opening_invoice(tool, row, get_invoice_dict) -> dict:
	"""Build the invoice dict, then apply the note sign when needed."""
	original = tool.invoice_type
	spec = invoice_type_spec(original)
	tool.invoice_type = spec["base_type"]
	try:
		invoice = get_invoice_dict(row)
	finally:
		tool.invoice_type = original
	return apply_note_to_invoice(invoice, original)


def _number(value, default: float) -> float:
	if value in (None, ""):
		return default
	try:
		return float(value)
	except (TypeError, ValueError):
		return default
