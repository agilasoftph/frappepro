// Copyright (c) 2026, Agilasoft Cloud Technologies and contributors
// License: MIT. See license.txt

// Invoice Type options must match frappehero/accounts/invoice_types.py.
const FRAPPEHERO_INVOICE_TYPE_LIST = ["Sales", "Purchase", "Credit Note", "Debit Note"];
const FRAPPEHERO_INVOICE_TYPES = FRAPPEHERO_INVOICE_TYPE_LIST.join("\n");

function frappehero_party_type(invoice_type) {
	return invoice_type === "Purchase" || invoice_type === "Debit Note" ? "Supplier" : "Customer";
}

function frappehero_select_has_notes(input) {
	if (!input || !input.options) {
		return false;
	}
	const values = {};
	for (let i = 0; i < input.options.length; i++) {
		values[input.options[i].value] = true;
	}
	return Boolean(values["Credit Note"] && values["Debit Note"]);
}

function frappehero_write_invoice_type_options(frm) {
	const field = frm.get_field("invoice_type");
	if (!field || field._frappehero_applying) {
		return;
	}
	field._frappehero_applying = true;
	try {
		// Meta is what refresh_field reads. The live <select> is what the
		// phone picker reads. Both have to list the notes, or the dialog
		// stays on Sales and Purchase.
		if (frm.meta && frm.meta.fields) {
			frm.meta.fields.forEach((df) => {
				if (df.fieldname === "invoice_type") {
					df.options = FRAPPEHERO_INVOICE_TYPES;
				}
			});
		}
		if (window.frappe && frappe.meta && frappe.meta.get_docfield) {
			const meta_field = frappe.meta.get_docfield(frm.doctype, "invoice_type");
			if (meta_field) {
				meta_field.options = FRAPPEHERO_INVOICE_TYPES;
			}
		}
		field.df.options = FRAPPEHERO_INVOICE_TYPES;

		let input = field.$input && field.$input.get(0);
		if (input && !frappehero_select_has_notes(input) && typeof field.set_options === "function") {
			const value = frm.doc.invoice_type;
			field.last_options = null;
			field.set_options();
			input = field.$input && field.$input.get(0);
			if (input && value && FRAPPEHERO_INVOICE_TYPE_LIST.indexOf(value) !== -1) {
				input.value = value;
			}
		}
		input = field.$input && field.$input.get(0);
		if (input && !frappehero_select_has_notes(input)) {
			FRAPPEHERO_INVOICE_TYPE_LIST.forEach((label) => {
				let found = false;
				for (let i = 0; i < input.options.length; i++) {
					if (input.options[i].value === label) {
						found = true;
						break;
					}
				}
				if (!found) {
					const option = document.createElement("option");
					option.value = label;
					option.textContent = __(label);
					input.appendChild(option);
				}
			});
		}
		if (input && !input.dataset.frappeheroNotes) {
			input.dataset.frappeheroNotes = "1";
			const open_picker = () => frappehero_write_invoice_type_options(frm);
			input.addEventListener("pointerdown", open_picker, true);
			input.addEventListener("touchstart", open_picker, true);
			input.addEventListener("mousedown", open_picker, true);
		}
	} finally {
		field._frappehero_applying = false;
	}
}

function frappehero_show_invoice_types(frm) {
	frappehero_write_invoice_type_options(frm);
	const field = frm.get_field("invoice_type");
	if (!field || field._frappehero_described) {
		return;
	}
	field._frappehero_described = true;
	frm.set_df_property(
		"invoice_type",
		"description",
		__(
			"Credit Note creates an opening customer credit. Debit Note creates an opening supplier debit. Enter the note amount as a positive number."
		)
	);
	// set_df_property refreshes the control from meta. Write the options
	// again so that refresh cannot put Sales and Purchase back.
	frappehero_write_invoice_type_options(frm);
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
	const form_handlers = frappe.ui && frappe.ui.form && frappe.ui.form.handlers;
	const handlers = form_handlers && form_handlers["Opening Invoice Creation Tool Item"];
	if (!handlers || !handlers.party || !handlers.party.length) {
		return;
	}
	handlers.party = [handlers.party[handlers.party.length - 1]];
})();
