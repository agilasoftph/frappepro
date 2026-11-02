# Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
# License: MIT. See license.txt

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from frappehero.accounts.invoice_types import INVOICE_TYPE_OPTIONS_TEXT

OPENING_INVOICE_TOOL = "Opening Invoice Creation Tool"

CUSTOM_FIELDS: dict[str, list[dict]] = {
	"User Permission": [
		{
			"fieldname": "frappehero_group",
			"label": "Frappe Hero Group",
			"fieldtype": "Link",
			"options": "Permission Group",
			"insert_after": "user",
			"read_only": 1,
			"no_copy": 1,
			"in_list_view": 1,
			"in_standard_filter": 1,
			"description": "Permission Group that last synced this restriction.",
		},
		{
			"fieldname": "frappehero_managed",
			"label": "Managed by Frappe Hero",
			"fieldtype": "Check",
			"insert_after": "frappehero_group",
			"read_only": 1,
			"no_copy": 1,
			"default": "0",
			"description": "Frappe Hero created this User Permission and removes it when the group no longer grants it.",
		},
	]
}


def after_install() -> None:
	ensure_custom_fields()
	ensure_opening_invoice_types()


def after_migrate() -> None:
	ensure_custom_fields()
	ensure_opening_invoice_types()


def before_tests() -> None:
	ensure_custom_fields()
	ensure_opening_invoice_types()


def ensure_custom_fields() -> None:
	"""Create the User Permission fields Permission Studio uses to track what it owns."""
	create_custom_fields(CUSTOM_FIELDS, ignore_validate=True, update=True)


def ensure_opening_invoice_types() -> None:
	"""Add Credit Note and Debit Note to the Opening Invoice Creation Tool.

	ERPNext ships the Invoice Type field as Sales and Purchase only. The
	property setter is what the desk reads when it draws the dropdown, so the
	notes show up even before the form script runs. Sites without ERPNext
	have no such DocType and are left alone.
	"""
	if not frappe.db.exists("DocType", OPENING_INVOICE_TOOL):
		return

	current = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": OPENING_INVOICE_TOOL,
			"field_name": "invoice_type",
			"property": "options",
		},
		"value",
	)
	if current == INVOICE_TYPE_OPTIONS_TEXT:
		return

	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	make_property_setter(
		OPENING_INVOICE_TOOL,
		"invoice_type",
		"options",
		INVOICE_TYPE_OPTIONS_TEXT,
		"Text",
		validate_fields_for_doctype=False,
	)
	frappe.clear_cache(doctype=OPENING_INVOICE_TOOL)
