# Copyright (c) 2022, Erevive Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CropProject(Document):
    def validate(self):
        self.set_totals()
        
    def set_totals(self):
        total_area = 0
                
        for dealer in self.dealers:
            total_area = total_area + dealer.area

        self.total_area = total_area
        self.total_villages = len(self.villages)
        
@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def crop_stage_query(doctype, txt, searchfield, start, page_len, filters):
    cond = ""
    if filters and filters.get("crop_cycle"):
        cond = "and cc.crop_cycle = '%s'" % filters.get("crop_cycle")
        
    return frappe.db.sql(
        """select cci.crop_stage from `tabCrop Cycle Item` cci
            LEFT JOIN `tabCrop Cycle` cc ON cc.name = cci.parent 
            where cci.crop_stage LIKE %(txt)s {cond}
            order by cc.crop_cycle limit %(page_len)s offset %(start)s""".format(
            key=searchfield, cond=cond
        ),
        {"txt": '%' + txt + '%', "start": start, "page_len": page_len},
    )