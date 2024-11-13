import frappe
import json
import os
import time
from frappe.integrations.utils import make_get_request, make_post_request
import frappe.desk.query_report
from frappe.www.printview import get_print_style
from frappe.utils.file_manager import save_file
from frappe.utils import random_string
from frappe.core.doctype.file.file import create_new_folder
from datetime import datetime, timedelta
import calendar


def get_pdf_data(doctype:None, name: None, print_format: None, letterhead: None, is_report:False, report_html:None):
    
    if not is_report:
        html = frappe.get_print(doctype, name, print_format, letterhead)
        return frappe.utils.pdf.get_pdf(html)
    else:
        from frappe.utils.pdf import get_pdf
        return get_pdf(report_html)

def create_folder(folder, parent):
    new_folder_name = "/".join([parent, folder])
    
    if not frappe.db.exists("File", new_folder_name):
        create_new_folder(folder, parent)
    
    return new_folder_name



@frappe.whitelist()
def whatsapp_for_dealer_not_visit_report(age):
#     send_whatsapp_for_ledger = frappe.db.get_single_value("Geolife Settings", "send_whatsapp_for_ledger")
#     if send_whatsapp_for_ledger == 0:
#         return
    try:
        employees = frappe.db.get_all("Geo Mitra", filters=[["Geo Mitra","custom_status","=","Active"],["Multiple Territory","territory","is","set"],["Geo Mitra","designation","like","%sales%"]], fields=["name"], group_by="name")
        frappe.log_error("geo mitra list", employees)

        for emp in employees:
            send_whatsapp_for_dealer_not_visit_report(emp.get('name'),age)

                    
    except Exception as e:
        frappe.log_error("whatsapp_for_dealer not visit_log", e)


def send_whatsapp_for_dealer_not_visit_report(geo_mitra,age):
        try:
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            today = datetime.today()

            # Calculate the first and last days of the previous month
            first_day_previous_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last_day_previous_month = today.replace(day=1) - timedelta(days=1)

            # Calculate the first, last, and fifteenth dates of the current month
            first_date = datetime(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]  # Access the last day correctly
            last_date = datetime(year, month, last_day)
            fifteenth_date = datetime(year, month, 15)

            # Set the from_date and to_date based on the `age` value
            if age == "Current_Month":
                from_date = first_date.strftime("%Y-%m-%d")
                to_date = fifteenth_date.strftime("%Y-%m-%d")
            else:
                from_date = first_day_previous_month.strftime("%Y-%m-%d")
                to_date = last_day_previous_month.strftime("%Y-%m-%d")


            filters = frappe._dict(
                {
                 "geo_mitra":geo_mitra,
                 "from_date":from_date,
                 "to_date":to_date
                }
            )
            report_data = frappe.desk.query_report.run(
                "All Dealer Not Visit Report",
                filters=filters,
                ignore_prepared_report=True
            )

            frappe.log_error("dealer not visit report_data list", report_data)
            report_data["result"].pop()

            letter_head = frappe.get_doc('Letter Head', 'geolife')

            html = frappe.render_template('templates/dealer_not_visit.html',
                {
                    "filters": filters,
                    "data": report_data["result"],
                    "title": "Dealer Not Visited",
                    "columns": report_data["columns"],
                    "letter_head": letter_head,
                    "terms_and_conditions": False,
                    "ageing": False,
                }
            )

            html = frappe.render_template('frappe/www/printview.html',
                { "body": html, "css": get_print_style(), "title": "Dealer Not Visited"}
            )
            frappe.log_error('entered in enqueue', "enqueue list")

            # send_report_auto_whatsapp_report(html,geo_mitra)
            geo_mitra1 = frappe.get_doc("Geo Mitra", geo_mitra)

            frappe.enqueue(send_report_auto_whatsapp_report(html,geo_mitra,"dealer_no_visit_reminder",[geo_mitra1.get('sales_person_name')]),queue='long', html=html, geo_mitra=geo_mitra, template_name="dealer_no_visit_reminder", params=[geo_mitra1.get('sales_person_name')]  )

        except Exception as e:
            frappe.log_error(" error report_whatsapp_for_dealer not visit", e)

def send_report_auto_whatsapp_report(html, geo_mitra, template_name, params):
    try:
        parameters=[]
        for v in params :
            parameters.append( {
                "type": "text",
                "text": v
            },)
        geo_mitra1 = frappe.get_doc("Geo Mitra", geo_mitra)
        url = frappe.db.get_single_value("Geolife Whatsapp Settings", "url")
        version = frappe.db.get_single_value("Geolife Whatsapp Settings", "version")
        phone_number_id = frappe.db.get_single_value("Geolife Whatsapp Settings", "phone_number_id")
        token = frappe.db.get_single_value("Geolife Whatsapp Settings", "token")
        token = f"Bearer {token}"
        base_url = f"{url}/{version}/{phone_number_id}/messages"

        pdf_data = get_pdf_data(None, None, None, None, is_report=True, report_html=html)
        unique_hash = frappe.generate_hash()[:10]
        s_file_name = f"{unique_hash}.pdf"
        folder_name = create_folder("Whatsapp", "Home")
        saved_file = save_file(s_file_name, pdf_data, '', '', folder=folder_name, is_private=0)
        s_document_link = f"{frappe.utils.get_url()}/files/{saved_file.file_name}"
        # receiver = frappe.db.get_value("Contact", contact, "mobile_no")
        # if not receiver:
        #     frappe.throw("Mobile Number Not Specified")

        file_path = frappe.utils.get_files_path(saved_file.file_name)

        while not os.path.exists(file_path):
            time.sleep(1)

        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": geo_mitra1.get('mobile_number'),
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": "en_US"
                },
                
                "components": [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "document",
                                "document":{
                                    "link": s_document_link,
                                    "filename": template_name
                                } 
                            }                    
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
        })
        headers = {
            'Authorization': token,
            'Content-Type': 'application/json'
        }

        response = make_post_request(base_url, headers=headers, data=payload)

        frappe.get_doc(
            {'doctype':'Whatsapp Chat Log',
            'to':geo_mitra1.get('name'),
            'mobile_no':geo_mitra1.get('name'),
            'full_name':geo_mitra1.get('sales_person_name'),
            'template':template_name,
            'payload':payload,
            'response':response,
            'ref_doctype':'Geo Mitra'}
        ).save()
        frappe.db.commit()
        # frappe.log_error(f"Req = {str(payload)} Resp = {str(response)}", "whatsapp_for_ledger")
        frappe.log_error("Whatsapp Sent to geo mitra", payload)

    except Exception as e:
        frappe.log_error("error que",f"error = {str(e)}")





@frappe.whitelist()
def whatsapp_for_overdue_120days_reminder_attachment():
#     send_whatsapp_for_ledger = frappe.db.get_single_value("Geolife Settings", "send_whatsapp_for_ledger")
#     if send_whatsapp_for_ledger == 0:
#         return
    try:
        employees = frappe.db.get_all("Geo Mitra", filters=[["Geo Mitra","custom_status","=","Active"],["Multiple Territory","territory","is","set"],["Geo Mitra","designation","like","%sales%"]], fields=["name"], group_by="name")
        frappe.log_error("geo mitra list", employees)

        for emp in employees:
            frappe.enqueue(send_whatsapp_for_overdue_120days_reminder_attachment_report(emp.get('name')),queue='long'  )
                   
    except Exception as e:
        frappe.log_error("whatsapp_for_overdue_120days_reminder_attachment error", e)


def send_whatsapp_for_overdue_120days_reminder_attachment_report(geo_mitra):
        try:

            geo_mitra2 = frappe.get_doc("Geo Mitra", geo_mitra)
            territories = [d.territory for d in geo_mitra2.get('territory')]
            territory_result=territories
            for territory in territories:
                lft = frappe.db.get_value("Territory", territory, "lft")
                rgt = frappe.db.get_value("Territory", territory, "rgt") 
                mterritory =[d.name for d in frappe.db.sql("""SELECT name FROM `tabTerritory` WHERE lft >= %s AND rgt <= %s """, (lft, rgt), as_dict=1)]
                if len(mterritory):
                    for tr in mterritory:
                        if tr not in territory_result:
                            territory_result.append(tr)

            report_data = frappe.db.get_all("Customer 120 Day Overdue For Currenct Fiscal Year", filters=[['territory', 'in',territory_result ],['outstanding_amount','>','1']], fields=["*"])
            if report_data:
                letter_head = frappe.get_doc('Letter Head', 'geolife')

                html = frappe.render_template('templates/overdue_120days_reminder_attachment_report.html',
                    {
                        "data": report_data,
                        "title": "Dealer  120 Day Overdue",
                        "letter_head": letter_head,
                        "terms_and_conditions": False,
                        "ageing": False,
                    }
                )

                html = frappe.render_template('frappe/www/printview.html',
                    { "body": html, "css": get_print_style(), "title": "Dealer overdue_120days_reminder_attachment_report"}
                )
                frappe.log_error('entered in enqueue', geo_mitra)

                # send_report_auto_whatsapp_report(html,geo_mitra)
                geo_mitra1 = frappe.get_doc("Geo Mitra", geo_mitra)

                frappe.enqueue(send_report_auto_whatsapp_report(html,geo_mitra,"overdue_120days_reminder_attachment", [geo_mitra1.get('sales_person_name'), f"{len(report_data)}"] ),queue='long'  )
            else:
                frappe.log_error('error overdue_120days_reminder_attachment_report',territory_result)
        except Exception as e:
            frappe.log_error(" error overdue_120days_reminder_attachment_report not visit", e)




@frappe.whitelist()
def whatsapp_for_overdue_150days_reminder_attachment():
#     send_whatsapp_for_ledger = frappe.db.get_single_value("Geolife Settings", "send_whatsapp_for_ledger")
#     if send_whatsapp_for_ledger == 0:
#         return
    try:
        employees = frappe.db.get_all("Geo Mitra", filters=[["Geo Mitra","custom_status","=","Active"],["Multiple Territory","territory","is","set"],["Geo Mitra","designation","like","%sales%"]], fields=["name"], group_by="name")
        frappe.log_error("geo mitra list", employees)

        for emp in employees:
            
            frappe.enqueue(send_whatsapp_for_overdue_150days_reminder_attachment_report(emp.get('name')),queue='long'  )


                    
    except Exception as e:
        frappe.log_error("whatsapp_for_overdue_150days_reminder_attachment error", e)


def send_whatsapp_for_overdue_150days_reminder_attachment_report(geo_mitra):
        try:

            geo_mitra2 = frappe.get_doc("Geo Mitra", geo_mitra)
            territories = [d.territory for d in geo_mitra2.get('territory')]
            territory_result=territories
            for territory in territories:
                lft = frappe.db.get_value("Territory", territory, "lft")
                rgt = frappe.db.get_value("Territory", territory, "rgt") 
                mterritory =[d.name for d in frappe.db.sql("""SELECT name FROM `tabTerritory` WHERE lft >= %s AND rgt <= %s """, (lft, rgt), as_dict=1)]
                if len(mterritory):
                    for tr in mterritory:
                        if tr not in territory_result:
                            territory_result.append(tr)

            report_data = frappe.db.get_all("Customer 150 Day Overdue For Currenct Fiscal Year", filters=[['territory', 'in',territory_result ],['outstanding_amount','>','1']], fields=["*"])
            if report_data:
                letter_head = frappe.get_doc('Letter Head', 'geolife')

                html = frappe.render_template('templates/overdue_150days_reminder_attachment_report.html',
                    {
                        "data": report_data,
                        "title": "Dealer  150 Day Overdue",
                        "letter_head": letter_head,
                        "terms_and_conditions": False,
                        "ageing": False,
                    }
                )

                html = frappe.render_template('frappe/www/printview.html',
                    { "body": html, "css": get_print_style(), "title": "Dealer overdue_150days_reminder_attachment_report"}
                )
                frappe.log_error('entered in enqueue', "enqueue list")

                # send_report_auto_whatsapp_report(html,geo_mitra)
                geo_mitra1 = frappe.get_doc("Geo Mitra", geo_mitra)

                frappe.enqueue(send_report_auto_whatsapp_report(html,geo_mitra,"overdue_150days_reminder_attachment", [geo_mitra1.get('sales_person_name'), f"{len(report_data)}"] ),queue='long'  )
            else:
                frappe.log_error('error overdue_150days_reminder_attachment_report',territory_result)
        except Exception as e:
            frappe.log_error(" error overdue_150days_reminder_attachment_report not visit", e)
