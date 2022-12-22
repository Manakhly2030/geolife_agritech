# Copyright (c) 2022, Erevive Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class CropCalendar(Document):
    pass


@frappe.whitelist()
def get_crop_products_html(crop_name):
    values = { 'crop_name': crop_name}
    sql = frappe.db.sql("""
        SELECT
            cci.crop_stage, cci.interval, cci.product_bundle
        FROM `tabCrop Cycle Item` cci
        LEFT JOIN `tabCrop Cycle` cc ON cc.name = cci.parent 
        WHERE cc.crop_name = %(crop_name)s
    """, values=values, as_dict=1)	

    html = """
    <div class="tax-break-up" style="overflow-x: auto;">
    <table class="table table-bordered table-hover">
        <tr>
            <th>Stage</th>
            <th>Interval</th>
            <th class='text-right' >Product Bundle</th>
        </tr>
        {% for d in sql %}
        <tr>
            <td>{{ d['crop_stage']}}</td>
            <td>{{ d['interval'] }}</td>
            <td class='text-right' >{{ d['product_bundle'] }}</td>
        </tr>
        {% endfor %}
    </table>
    """
    return frappe.render_template(html, dict(sql=sql))