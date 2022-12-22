// Copyright (c) 2022, Erevive Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crop Project', {
	refresh: function(frm) {
		frm.set_query("crop_cycle", function() {
			return {
				"filters": {
					"crop_name": frm.doc.crop_name
				}
			}
		});

		frm.set_query("crop_stage", function() {
			return {
				query: "geolife_agritech.geolife_agritech.doctype.crop_project.crop_project.crop_stage_query",
				filters: {"crop_cycle": frm.doc.crop_cycle}
			};
		});
	}
});
