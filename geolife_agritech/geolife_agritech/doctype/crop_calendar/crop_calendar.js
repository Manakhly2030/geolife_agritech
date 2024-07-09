// Copyright (c) 2022, Erevive Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Calendar', {

	// refresh: function (frm) {
	// 	frm.events.set_crop_product(frm);
	// },

	set_crop_product: function (frm) {
		if (frm.doc.crop_name !== null && frm.doc.crop_cycle_products === undefined) {
			frappe.call("geolife_agritech.geolife_agritech.doctype.crop_calendar.crop_calendar.get_crop_products_html", {
				crop_name: frm.doc.crop_name
			}).then(r => {
				frm.set_value("crop_cycle_products", r.message);
			});
		}
	},

	crop_name: function (frm) {
		if (!frm.doc.crop_name) {
			return;
		} else {
			frappe.call("geolife_agritech.geolife_agritech.doctype.crop_calendar.crop_calendar.get_crop_products_html", {
				crop_name: frm.doc.crop_name
			}).then(r => {
				frm.set_value("crop_cycle_products", r.message);
			});
		}
	}

});
