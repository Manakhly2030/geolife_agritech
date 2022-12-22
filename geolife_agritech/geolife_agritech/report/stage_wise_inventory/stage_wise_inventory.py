# Copyright (c) 2022, Erevive Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_to_date, formatdate

def execute(filters=None):
    
    total_land = filters.get("total_land") or 1
    sowing_date = filters.get("sowing_date")
    
    columns = ["Stage", "Interval", "Date", "Product Bundle", "Quantity", "Total Quantity", "Unit"]
    data = []

    crop_cycle = frappe.db.get_value("Crop Project", filters.get("crop_project"), "crop_cycle")
    crop_cycles = frappe.get_doc("Crop Cycle", crop_cycle)
    
    for index, cs in enumerate(crop_cycles.crop_items):
        date = sowing_date
        interval = 0
        if index >= 1:
            interval = crop_cycles.crop_items[index-1].interval
            date = add_to_date(sowing_date, days=interval)
        
        x = {
            "stage": cs.crop_stage,
            "interval": cs.interval,
            "date": formatdate(date),
            "product_bundle": cs.product_bundle,
            "quantity": "",
            "total_quantity": "",
            "unit": ""
        }
        data.append(x)
        
        product_bundle = frappe.get_doc("Product Bundle", cs.product_bundle)
        for product in product_bundle.bundle_items:
            p = {
                "stage": "",
                "interval": "",
                "date": "",
                "product_bundle": product.product_name,
                "quantity": product.quantity,
                "total_quantity":  product.quantity * total_land,
                "unit": product.uom
            }
            data.append(p)
            
        
    return columns, data
