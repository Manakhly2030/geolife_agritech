import json
import frappe
from frappe.integrations.utils import make_get_request, make_post_request

@frappe.whitelist()
def attendance_sync():
    geo_mitra_list = frappe.db.sql(f"""
        SELECT
            gm.dgo_code, gm.name
        FROM `tabGeo Mitra` AS gm
        WHERE gm.custom_status="Active" AND gm.dgo_code!="" AND gm.geo_mitra_company ="Geolife"
        GROUP BY gm.name
        ORDER BY gm.name
    """, as_dict=1)
    for emp in geo_mitra_list:
        frappe.enqueue(get_attendance, emp=emp)

def get_attendance(emp):
    data =[]
    result1 = frappe.db.sql(
        f"""SELECT da.geo_mitra, da.posting_date, atm.activity_type as activity_type, da.session_started AS str, da.session_enddate AS end
        FROM
            `tabDaily Activity` da
        LEFT JOIN
            `tabGeo Mitra` gm ON gm.name = da.geo_mitra
        LEFT JOIN
            `tabActivity Type Multiselect` atm ON atm.parent = da.name
        WHERE
            da.posting_date between %s and %s
            AND da.geo_mitra=%s
            AND atm.activity_type='End Day'
        ORDER BY
            da.posting_date DESC
    """, (frappe.utils.add_to_date(frappe.utils.today(), days=-1), frappe.utils.add_to_date(frappe.utils.today()), emp.get("name")), as_dict=1)
    
    full_day = frappe.utils.get_time("08:30:00")
    half_day = frappe.utils.get_time("04:30:00")

    if result1:
        attendance_data = {
            "staff_code": "",
            "posting_date": "",
            "status": "",
            "leave_type": ""
        }
        difference_seconds=float('0.00')
        total_working_seconds = 0
        for r in result1:
            start_time = frappe.utils.get_datetime(r.get('str'))
            end_time = frappe.utils.get_datetime(r.get('end'))
            difference = frappe.utils.time_diff_in_seconds(end_time, start_time)
            difference_seconds =difference_seconds + float(difference)
        full_day_seconds = full_day.hour * 3600 + full_day.minute * 60 + full_day.second
        half_day_seconds = half_day.hour * 3600 + half_day.minute * 60 + half_day.second
        date_key = frappe.utils.formatdate(r.get('posting_date'), 'YYYYMMDD')
        posting_date_str = frappe.utils.formatdate(r.get("posting_date"), "yyyy-MM-dd")

        if difference_seconds >= full_day_seconds:
            attendance_data["status"] = "Present"
            attendance_data["posting_date"] = posting_date_str
            attendance_data["staff_code"] = emp.get("dgo_code")
            attendance_data["leave_type"] = ""
        elif half_day_seconds <= difference_seconds <= full_day_seconds:
            attendance_data["status"] = "Half Day"
            attendance_data["posting_date"] = posting_date_str
            attendance_data["staff_code"] = emp.get("dgo_code")
            attendance_data["leave_type"] = "Leave Without Pay"
        else:
            attendance_data["status"] = "Absent"
            attendance_data["posting_date"] = posting_date_str
            attendance_data["staff_code"] = emp.get("dgo_code")
            attendance_data["leave_type"] = ""
        attendance_data['working_time']=difference_seconds/3600
    else:
        attendance_data = {
            "staff_code": emp.get("dgo_code"),
            "posting_date": frappe.utils.add_to_date(frappe.utils.today(), days=-1),
            "status": "Absent",
            "leave_type": ""
        }
        
    insert_atte = frappe.get_doc({'doctype':'Attendance',
    'naming_series':'HR-ATT-.YYYY.-',
    'geo_mitra':emp.get("name"),
    'status':attendance_data.get('status'),
    'attendance_date':attendance_data.get('posting_date'),
    }).insert()
            
    url = 'https://geolife.erpgeolife.com'
    apikey = frappe.db.get_single_value('GeoLife Setting', 'api_key')
    apisec =  frappe.db.get_single_value('GeoLife Setting', 'api_secret')
    headers = {'Authorization': f'token {apikey}:{apisec}','Content-Type': 'application/json'}
    
    url= f"{url}/api/method/attendance_sync"
    mdata={'adata':[attendance_data]}
    my_req = make_post_request(url, data=json.dumps(mdata), headers=headers)    

    frappe.log_error("sync Errror of attendance",my_req)