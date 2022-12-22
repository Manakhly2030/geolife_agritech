# Copyright (c) 2022, Erevive Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import add_to_date, formatdate

def execute(filters=None):
    
    total_land = filters.get("total_land") or 1
    sowing_date = filters.get("sowing_date")
    
    columns = ["Stage", "Interval", "Date", "Product Bundle", "Inventory", "POP", "Sales", "Material Liquidation", "Finance"]
    data = []

    crop_cycle = frappe.db.get_value("Crop Project", filters.get("crop_project"), "crop_cycle")
    crop_cycles = frappe.get_doc("Crop Cycle", crop_cycle)
    
    for index, cs in enumerate(crop_cycles.crop_items):
        
        date = sowing_date
        interval = 0

        inventory_date = add_to_date(sowing_date, days=-40)
        pop_date = add_to_date(sowing_date, days=-20)
        sales_date = add_to_date(sowing_date, days=-15)
        material_date = add_to_date(sowing_date, days=15)
        
        if index >= 1:
            interval = crop_cycles.crop_items[index-1].interval
            date = add_to_date(sowing_date, days=interval)

            inventory_date = add_to_date(date, days=-40)
            pop_date = add_to_date(date, days=-20)
            sales_date = add_to_date(date, days=-15)
            material_date = add_to_date(date, days=15)
        
        x = {
            "stage": cs.crop_stage,
            "interval": cs.interval,
            "date": formatdate(date),
            "product_bundle": cs.product_bundle,
            "inventory": formatdate(inventory_date),
            "pop": formatdate(pop_date),
            "sales": formatdate(sales_date),
            "material_liquidation": formatdate(material_date),
            "finance": formatdate(date)
        }
        data.append(x)
        
    return columns, data
