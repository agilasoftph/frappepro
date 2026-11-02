// Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
// License: MIT. See license.txt

// Invoice Type options must match frappehero/accounts/invoice_types.py.
const FRAPPEHERO_INVOICE_TYPES = "Sales\nPurchase\nCredit Note\nDebit Note";

function frappehero_party_type(invoice_type) {
	return invoice_type === "Purchase" || invoice_type === "Debit Note" ? "Supplier" : "Customer";
}

function frappehero_show_invoice_types(frm) {
	const field = frm.get_field("invoice_type");
	if (!field) {
		return;
	}
	frm.set_df_property(
		"invoice_type",
		"description",
		__(
			"Credit Note creates an opening customer credit. Debit Note creates an opening supplier debit. Enter the note amount as a positive number."
		)
	);
	if ((field.df.options || "") === FRAPPEHERO_INVOICE_TYPES) {
		return;
	}
	// Set the field definition before the select is built. Calling set_options
	// before the input exists records an empty option list and the dropdown
	// never picks up Credit Note and Debit Note.
	const value = frm.doc.invoice_type;
	field.df.options = FRAPPEHERO_INVOICE_TYPES;
	if (field.$input && typeof field.set_options === "function") {
		field.last_options = null;
		field.set_options();
		if (value && FRAPPEHERO_INVOICE_TYPES.split("\n").indexOf(value) !== -1) {
			field.$input.val(value);
		}
	}
}

function frappehero_apply_party_labels(frm) {
	const party_type = frappehero_party_type(frm.doc.invoice_type);
	const is_customer = party_type === "Customer";
	const grid = frm.fields_dict.invoices && frm.fields_dict.invoices.grid;
	if (!grid) {
		return;
	}
	grid.update_docfield_property("party", "label", is_customer ? "Customer ID" : "Supplier ID");
	grid.update_docfield_property("party_name", "label", is_customer ? "Customer Name" : "Supplier Name");
	frm.set_df_property(
		"create_missing_party",
		"description",
		is_customer
			? __("If party does not exist, create it using the Customer Name field.")
			: __("If party does not exist, create it using the Supplier Name field.")
	);
	frm.refresh_field("invoices");
	frm.refresh_field("create_missing_party");
}

function frappehero_apply_party_types(frm) {
	const party_type = frappehero_party_type(frm.doc.invoice_type);
	(frm.doc.invoices || []).forEach((row) => {
		row.party_type = party_type;
	});
	frm.refresh_field("invoices");
}

function frappehero_set_create_action(frm) {
	const messages = {
		Sales: __("Creating Sales Invoices ..."),
		Purchase: __("Creating Purchase Invoices ..."),
		"Credit Note": __("Creating Credit Notes ..."),
		"Debit Note": __("Creating Debit Notes ..."),
	};
	frm.page.set_primary_action(__("Create Invoices"), () => {
		const button = frm.page.btn_primary.get(0);
		return frm.call({
			doc: frm.doc,
			btn: $(button),
			method: "make_invoices",
			freeze: 1,
			freeze_message: messages[frm.doc.invoice_type] || __("Creating Invoices ..."),
		});
	});
}

frappe.ui.form.on("Opening Invoice Creation Tool", {
	setup(frm) {
		frappehero_show_invoice_types(frm);
	},
	refresh(frm) {
		// Run after ERPNext's own refresh, which only knows Sales and Purchase.
		frappehero_show_invoice_types(frm);
		setTimeout(() => {
			frappehero_show_invoice_types(frm);
			frappehero_apply_party_labels(frm);
			frappehero_set_create_action(frm);
		}, 0);
	},
	invoice_type(frm) {
		setTimeout(() => {
			frappehero_apply_party_labels(frm);
			frappehero_apply_party_types(frm);
		}, 0);
	},
	update_party_labels(frm) {
		setTimeout(() => frappehero_apply_party_labels(frm), 0);
	},
	update_invoice_table(frm) {
		setTimeout(() => frappehero_apply_party_types(frm), 0);
	},
});

frappe.ui.form.on("Opening Invoice Creation Tool Item", {
	party(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row) {
			return;
		}
		const party_type = frappehero_party_type(frm.doc.invoice_type);
		row.party_type = party_type;
		if (!row.party) {
			frappe.model.set_value(cdt, cdn, "party_name", "");
			return;
		}
		const name_field = party_type === "Customer" ? "customer_name" : "supplier_name";
		frappe.db.get_value(party_type, row.party, name_field, (r) => {
			frappe.model.set_value(cdt, cdn, "party_name", (r && r[name_field]) || "");
		});
	},
});

// ERPNext looks up a Supplier whenever the type is not Sales, so a Credit Note
// would fetch the wrong party name. Keep only this handler.
(function () {
	const handlers = frappe.ui.form.handlers["Opening Invoice Creation Tool Item"];
	if (!handlers || !handlers.party || !handlers.party.length) {
		return;
	}
	handlers.party = [handlers.party[handlers.party.length - 1]];
})();
