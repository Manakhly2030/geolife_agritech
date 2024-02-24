import frappe
from frappe.model.document import Document
from frappe.query_builder import Interval
from frappe.query_builder.functions import Now
import json


@frappe.whitelist()
def clear_dealer_monthly_target():
	frappe.only_for("System Manager")
	frappe.db.truncate("Dealer Monthly Target")
	return {'status':"true"}
	

@frappe.whitelist()
def dealer_import(doc_name):
	clear_dealer_monthly_target()
	# frappe.log_error("Whitelist Method dealer import", result_data)
	my_doc = frappe.get_doc("Dealer Monthly Target Report Data", doc_name)
	result = json.loads(my_doc.api_report_data)
	cust_avilable = []
	cust_not_avilable = []
	for res in result:
		if frappe.db.count('Dealer', {'dealer_code': res.get("customer")}) > 0:
			customer_name = frappe.db.get_value('Dealer', {'dealer_code': res.get("customer")}, ['name','dealer_name'], as_dict=1)
			cust_avilable.append(customer_name)
			if customer_name:
				monthly_sales = frappe.new_doc("Dealer Monthly Target")
				monthly_sales.dealer = customer_name.name if customer_name.name else ''
				monthly_sales.dealer_name = customer_name.dealer_name if customer_name.dealer_name else ''
				monthly_sales.dealer_code = res.get("customer") if res.get("customer") else ''
				monthly_sales.territory = res.get("territory") if res.get("territory") else ''
				monthly_sales.fiscal_year = res.get("fiscal_year") if res.get("fiscal_year") else '' 
				monthly_sales.month = res.get("month") if res.get("month") else ''
				monthly_sales.outstanding = res.get("outstanding") if res.get("outstanding") else ''
				monthly_sales.item_group = res.get("item_group") if res.get("item_group") else ''
				monthly_sales.sale_quantity = res.get("s_quantity") if res.get("s_quantity") else ''
				monthly_sales.sale_amount = res.get("s_amount") if res.get("s_amount") else ''
				monthly_sales.return_quantity = res.get("r_quantity") if res.get("r_quantity") else ''
				monthly_sales.return_amount = res.get("r_amount") if res.get("r_amount") else ''
				monthly_sales.insert(ignore_permissions=True, ignore_links=True, ignore_if_duplicate=True, ignore_mandatory=True)
			else:
				cust_not_avilable.append(res.get("customer"))
		else:
			cust_not_avilable.append(res.get("customer"))
			monthly_sales = frappe.new_doc("Dealer Monthly Target")
			monthly_sales.dealer_code = res.get("customer") if res.get("customer") else ''
			monthly_sales.territory = res.get("territory") if res.get("territory") else ''
			monthly_sales.fiscal_year = res.get("fiscal_year") if res.get("fiscal_year") else '' 
			monthly_sales.month = res.get("month") if res.get("month") else ''
			monthly_sales.item_group = res.get("item_group") if res.get("item_group") else ''
			monthly_sales.sale_quantity = res.get("s_quantity") if res.get("s_quantity") else ''
			monthly_sales.sale_amount = res.get("s_amount") if res.get("s_amount") else ''
			monthly_sales.return_quantity = res.get("r_quantity") if res.get("r_quantity") else ''
			monthly_sales.return_amount = res.get("r_amount") if res.get("r_amount") else ''
			monthly_sales.insert(ignore_permissions=True, ignore_links=True, ignore_if_duplicate=True, ignore_mandatory=True)
	
	# frappe.log_error('Customer_Avilable', cust_avilable)
	# frappe.log_error('Customer_Not_Avilable', cust_not_avilable)

@frappe.whitelist()
def custom_enqueue(doc_name):
	# result_data = json.dumps(result)
	frappe.enqueue(dealer_import, queue='long', doc_name=doc_name)

	return {"status":"success"}


@frappe.whitelist()
def mrm_api_dealer_target():
	data = frappe.request.json
	result = data.get("result")
	# frappe.log_error("MY Result",result)
	report_result = frappe.new_doc("Dealer Monthly Target Report Data")
	report_result.api_report_data = json.dumps(result)
	try:
		report_result.insert(ignore_permissions=True, ignore_links=True, ignore_if_duplicate=True, ignore_mandatory=True)
		if report_result.name:
			doc_name = report_result.name
			custom_enqueue(doc_name)
			
	except:
		frappe.log_error("Error In Import Report data Queue")





