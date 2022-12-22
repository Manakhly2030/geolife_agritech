// Copyright (c) 2022, Erevive Technologies and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Stage Wise Inventory"] = {
	"filters": [
		{
			"fieldname": "crop_project",
			"fieldtype": "Link",
			"options": "Crop Project",
			"label": "Crop Project"
		},
		{
			"fieldname": "total_land",
			"fieldtype": "Float",
			"label": "Total Land"
		},
		{
			"fieldname": "sowing_date",
			"fieldtype": "Date",
			"label": "Sowing Date",
			"default": "Today"
		}


	]
};
