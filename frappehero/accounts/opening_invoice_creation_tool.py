# Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
# License: MIT. See license.txt

"""Opening Invoice Creation Tool with Credit Note and Debit Note.

ERPNext's controller only understands Sales and Purchase. Selecting a note
used to fall through to a Purchase Invoice, and the Invoice Type field did
not list the notes at all. This subclass keeps the standard behaviour for
Sales and Purchase and creates return invoices for the two notes.
"""

from __future__ import annotations

import frappe
from frappe import _

from frappehero.accounts.invoice_types import (
	InvoiceTypeError,
	build_opening_invoice,
	prepare_opening_row,
)

try:
	from erpnext.accounts.doctype.opening_invoice_creation_tool.opening_invoice_creation_tool import (
		OpeningInvoiceCreationTool as _ERPNextOpeningInvoiceCreationTool,
	)
except ImportError:  # ERPNext is not installed on this site.
	_ERPNextOpeningInvoiceCreationTool = None


if _ERPNextOpeningInvoiceCreationTool:

	class OpeningInvoiceCreationTool(_ERPNextOpeningInvoiceCreationTool):
		def set_missing_values(self, row):
			try:
				prepare_opening_row(self, row, super().set_missing_values)
			except InvoiceTypeError as exc:
				self._reject_invoice_type(exc)

		def get_invoice_dict(self, row=None):
			try:
				return build_opening_invoice(self, row, super().get_invoice_dict)
			except InvoiceTypeError as exc:
				self._reject_invoice_type(exc)

		def _reject_invoice_type(self, exc: InvoiceTypeError):
			frappe.throw(
				_("Invoice Type {0} is not supported.").format(frappe.bold(exc.invoice_type)),
				title=_("Unsupported Invoice Type"),
			)

else:

	class OpeningInvoiceCreationTool:  # pragma: no cover - desk class needs ERPNext
		"""Placeholder so the hook can import on a site that has no ERPNext."""
