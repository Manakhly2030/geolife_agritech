import datetime
import json
import random
import frappe
from frappe import auth
import base64
import os
from frappe.utils import get_files_path, get_site_name, now, add_to_date, get_datetime, add_to_date, validate_email_address
from frappe.utils.data import escape_html
import requests
from frappe.core.doctype.user.user import test_password_strength
import re

@frappe.whitelist(allow_guest=True)
def generate_otp(mobile_no):
    if not mobile_no :
        frappe.local.response["message"] = {
            "status": False,
            "message": "Invalid Mobile Number"
        }
        return
    
    user_email = frappe.db.get_all('User', filters={'mobile_no': mobile_no}, fields=['email'])
    if not user_email:
        frappe.local.response["message"] = {
            "status": False,
            "message": "User does not exits"
        }
        return 

    try:
        otp = "1234"
        # otp = str(random.randint(1000,9999))
        # msisdn = mobile_no #frappe.generate_hash("", 10)
        # text = f"You OTP {otp}"

        # callback_url = frappe.db.get_single_value("Geo Settings", "sms_call_back_url")
        # url = frappe.db.get_single_value("Geo Settings", "sms_base_url")
        # app_id = frappe.db.get_single_value("Geo Settings", "sms_app_id")
        # app_key = frappe.db.get_single_value("Geo Settings", "sms_app_key")

        # sms_payload = {
        #     "msisdn": msisdn,
        #     "text": text,
        #     "callback_url": callback_url,
        #     "premium": True
        # }
        # sms_headers = {
        #     "accept": "application/json",
        #     "App-ID": app_id,
        #     "API-Key": app_key,
        #     "content-type": "application/json"
        # }
        # r = requests.post(url, json=sms_payload, headers=sms_headers)

        # if r.status_code != 201:
        #     frappe.local.response["message"] = {
        #         "status": False,
        #         "message": json.loads(r.text)["message"]
        #     }
        #     return
        doc = frappe.get_doc({
            "doctype": "OTP Auth",
            "mobile_number": mobile_no,
            "otp": otp,
        })

        doc.insert(ignore_permissions=True)
        doc.save()
        frappe.db.commit()
        
        frappe.local.response["message"] = {
        "status": True,
        "message": 'OTP SENT'
        }

        return

    except Exception as e:
        return e

@frappe.whitelist(allow_guest=True)
def reset_otp(mobile_no):
    generate_otp(mobile_no)

@frappe.whitelist()
def get_user_info(api_key, api_sec):
    # api_key  = frappe.request.headers.get("Authorization")[6:21]
    # api_sec  = frappe.request.headers.get("Authorization")[22:]
    doc = frappe.db.get_value(
        doctype='User',
        filters={"api_key": api_key},
        fieldname=["name"]
    )

    doc_secret = frappe.utils.password.get_decrypted_password('User', doc, fieldname='api_secret')

    if api_sec == doc_secret:
        user = frappe.db.get_value(
            doctype="User",
            filters={"api_key": api_key},
            fieldname=["name"]
        )
        return user
    else:
        return "API Mismatch"

@frappe.whitelist(allow_guest=True)
def generate_keys(user):
    user_details = frappe.get_doc("User", user)
    api_secret = frappe.generate_hash(length=15)
    
    if not user_details.api_key:
        api_key = frappe.generate_hash(length=15)
        user_details.api_key = api_key
    
    user_details.api_secret = api_secret

    user_details.flags.ignore_permissions = True
    user_details.save(ignore_permissions = True)
    frappe.db.commit()
    
    return user_details.api_key, api_secret

@frappe.whitelist(allow_guest=True)
def validate_otp(mobile_no, otp):

    if not mobile_no or not otp:
        frappe.local.response["message"] = {
            "status": False,
            "message": "invalid inputs"
        }
        return
    
    x_user = frappe.get_all('OTP Auth', filters={'mobile_number': mobile_no, 'otp': otp}, fields=["*"], order_by= 'creation desc')

    # if x_user[0].otp != otp:
    #     frappe.local.response["message"] = {
    #         "status": False,
    #         "message": "Invalid OTP"
    #     }
    #     return

    if x_user:
        now_time = now()
        otp_valid_upto = frappe.db.get_single_value('GeoLife Setting', 'otp_valid_upto')
        expiry_time = add_to_date(x_user[0].creation, seconds=180)

        if get_datetime(now()) > get_datetime(expiry_time):
            frappe.local.response["message"] = {
                "status": False,
                "message": "Time Out, Your OTP Expired"
            }
            return

    if not x_user:
        frappe.local.response["message"] = {
            "status": False,
            "message": "Invalid Otp, Please try again with correct otp"
        }
        return

    user_email = ""
    
    if x_user[0].otp == otp:

        user_exist = frappe.db.count("User",{'mobile_no': mobile_no})

        if user_exist > 0:

            userm = frappe.db.get_all('User', filters={'mobile_no': mobile_no}, fields=['*'])
            user_email = userm[0].name

            user_image = get_doctype_images('User', user_email, 1)
            _user_image =[]
            
            if user_image:
                _user_image = user_image[0]['image']
                userm[0].images = _user_image

            api_key, api_secret = generate_keys(user_email)
            geomitra_data = frappe.db.get_all('Geo Mitra', filters={'linked_user': user_email}, fields=['*'])
            frappe.local.response["message"] = {
                "status": True,
                "message": "User Already Exists",
                "data":{
                "api_key": api_key,
                "api_secret": api_secret,
                "geomitra_data":geomitra_data,
                "first_name": userm[0].first_name,
                "last_name": userm[0].last_name,
                "mobile_no": userm[0].mobile_no,
                "email_id": userm[0].email,
                "role": userm[0].user_type
            }
            }
            return
            

        frappe.local.response["message"] = {
            "status": False,
            "message": "User Not Exists",
        }

def get_doctype_images(doctype, docname, is_private):
    attachments = frappe.db.get_all("File",
        fields=["attached_to_name", "file_name", "file_url", "is_private"],
        filters={"attached_to_name": docname, "attached_to_doctype": doctype}
    )
    resp = []
    for attachment in attachments:
        # file_path = site_path + attachment["file_url"]
        x = get_files_path(attachment['file_name'], is_private=is_private)
        with open(x, "rb") as f:
            # encoded_string = base64.b64encode(image_file.read())
            img_content = f.read()
            img_base64 = base64.b64encode(img_content).decode()
            img_base64 = 'data:image/jpeg;base64,' + img_base64
        resp.append({"image": img_base64})

    return resp

def ng_write_file(data, filename, docname, doctype, file_type):
    try:
        filename_ext = f'/home/geolife/frappe-bench/sites/crop.erpgeolife.com/{file_type}/files/{filename}.png'
        base64data = data.replace('data:image/jpeg;base64,', '')
        imgdata = base64.b64decode(base64data)
        with open(filename_ext, 'wb') as file:
            file.write(imgdata)

        doc = frappe.get_doc(
            {
                "file_name": f'{filename}.png',
                "is_private": 0 if file_type == 'public' else 1,
                "file_url": f'/{file_type}/files/{filename}.png',
                "attached_to_doctype": doctype,
                "attached_to_name": docname,
                "doctype": "File",
            }
        )
        doc.flags.ignore_permissions = True
        doc.insert()
        frappe.db.commit()
        return doc.file_url

    except Exception as e:
        frappe.log_error(str(e))
        return e

@frappe.whitelist(allow_guest=True)
def crop_seminar():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]
    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    geo_mitra_id = get_geomitra_from_userid(user_email)
    if geo_mitra_id == False:
        frappe.response["message"] = {
            "status": False,
            "message": "Please map a geo mitra with this user",
            "user_email": user_email
        }
        return


    if frappe.request.method =="GET":
        home_data = frappe.db.get_all("Crop Seminar", fields=["*"])

        for h in home_data:
            child_data = frappe.get_doc("Crop Seminar", h.name)
            if child_data:
                h.details = child_data
            image = get_doctype_images('Crop Seminar', h.name, 1)                

            if image:
                h.image = image[0]['image']
            else:
                h.image = frappe.utils.get_url("/files/no-image.png")

        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
    elif frappe.request.method == "POST":
        crop_data = frappe.request.json
        crop = frappe.get_doc({
            "doctype":"Crop Seminar",
            "village": crop_data['village'],
            "seminar_date": crop_data['seminar_date'],
            "seminar_time": crop_data['seminar_time'],
            "venue": crop_data['venue'],
            "speeker_name": crop_data['speeker_name'],
            "mobile_no": crop_data['mobile_no'],
            "message": crop_data['message'],
            "bk_center": crop_data['bk_center'],
            "address": crop_data['address'],
            "pincode": crop_data['pincode'],
            "geo_mitra": geo_mitra_id

        })
        crop.insert()
        crop.save()
        frappe.db.commit()

        if crop_data['image']:
            data = crop_data['image'][0]
            filename = crop.name
            docname = crop.name
            doctype = "Crop Seminar"
            image = ng_write_file(data, filename, docname, doctype, 'private')

            crop.image = image

        frappe.response["message"] = {
            "status":True,
            "message": "Crop Seminar Added Successfully",
        }
        return

    elif frappe.request.method == "PUT":
        crop_data = frappe.request.json
        crop = frappe.get_doc('Crop Seminar', crop_data['name'])

        if crop_data.get('crop_seminar_attendance'):
            crop.crop_seminar_attendance = crop_data['crop_seminar_attendance']
            # crop.crop_seminar_attendance = []
            for itm in crop_data['crop_seminar_attendance'] :
                crop.append("crop_seminar_attendance",{"farmer": crop_data.get('farmer_name')})
            
        if crop_data.get('is_pre_activity'):
            crop.pre_activities = []
            for itm in crop_data['pre_activities'] :
                crop.append("pre_activities",{"activity_name": itm['activity_name'], "activity_status":itm['activity_status']})

        if crop_data.get('is_post_activity'):
            crop.post_activities = []
            for itm in crop_data['post_activities'] :
                crop.append("post_activities",{"activity_name": itm['activity_name'], "activity_status":itm['activity_status']})
            
        if crop_data.get('is_upload_photos'):

            image_url = ng_write_file(crop_data.get('image'), crop_data.get('name'), crop_data.get('name'), 'Crop Seminar', 'private')
            crop.append("upload_photos", {"farmer": crop_data.get('farmer_name'),"note": crop_data.get('note'), "seminar_image_path": frappe.utils.get_url(image_url)})
            crop.append("crop_seminar_attendance",{"farmer": crop_data.get('farmer_name')})

        crop.save(ignore_permissions=True)
        frappe.response["message"] = {
            "status":True,
            "message": "Crop Seminar Details Updated Successfully",
        }
        
        return

@frappe.whitelist(allow_guest=True)
def activity_list():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Daily Activity", fields=["posting_date","activity_name","activity_type","notes"])
        for h in home_data:
            image = get_doctype_images('Daily Activity', h.name, 1)  

            if image:
                h.image = image[0]['image']
            else:
                h.image = "https://winaero.com/blog/wp-content/uploads/2019/11/Photos-new-icon.png"
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
        # if Crop_data['image']:
        #     ng_write_file(Crop_data['image'], 'demo.jpg', "", "Pet")
        doc = frappe.get_doc({
            "doctype":"Daily Activity",
            "posting_date": frappe.utils.nowdate(),
            "activity_name": _data['activity_name'],
            "activity_type": _data['activity_type'],
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id

        })
        doc.insert()
        
        if _data['image']:
            data = _data['image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Daily Activity"
            image = ng_write_file(data, filename, docname, doctype, 'private')

            doc.image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Daily Activity Added Successfully",
        }
        return

@frappe.whitelist(allow_guest=True)
def activity_type():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Activity Type", fields=["activity_type","name"], filters={"type":"Show"})
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return

@frappe.whitelist(allow_guest=True)
def expense_type():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Geo Expense Type", fields=["name","json"])
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
@frappe.whitelist(allow_guest=True)
def expenses():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Geo Expenses", fields=["name","posting_date","expense_type","amount","against_expense","notes"])
        # for hd in home_data:
        #     himage = get_doctype_images("Geo Expenses",hd.name,0)
        #     if himage :
        #         hd.image = himage

        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
        
        doc = frappe.get_doc({
            "doctype":"Geo Expenses",
            "posting_date": frappe.utils.nowdate(),
            "expense_type": _data['expense_type'],
            "amount" : _data.get('amount') if _data.get('amount') else 0,
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id,
            "vehical_type" : _data.get('vehical_type') if _data.get('vehical_type') else '',
            "fuel_type" : _data.get('fuel_type') if _data.get('fuel_type') else '',
            "odometer_start" : _data.get('odometer_start') if _data.get('odometer_start') else '',
            "odometer_end" : _data.get('odometer_end') if _data.get('odometer_end') else '',
            "liters" : _data.get('liters') if _data.get('liters') else '',
            "employee_location": _data['mylocation'],

        })
        doc.insert()        
        if _data['odometer_start_image']:
            data = _data['odometer_start_image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Geo Expenses"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.odometer_start_image = image

        if _data.get('odometer_end_image'):
            data = _data['odometer_end_image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Geo Expenses"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.odometer_end_image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Expensey Added Successfully",
        }
        return
    
@frappe.whitelist(allow_guest=True)
def free_sample_distribution():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Free Sample Distribution", fields=["posting_date","farmer","geo_mitra","notes","update_status"])
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
        doc = frappe.get_doc({
            "doctype":"Free Sample Distribution",
            "posting_date": frappe.utils.nowdate(),
            "farmer": _data['farmer'],
            "geo_mitra": geo_mitra_id,
            # "crop_seminar": _data['name'],
            # "notes": _data['notes'],
            # "product": _data['product'],
            "update_status": "Used",
        })
        doc.insert()
        # if _data['image']:
        #     data = _data['image']
        #     filename = doc.name
        #     docname = doc.name
        #     doctype = "Free Sample Distribution"
        #     image = ng_write_file(data, filename, docname, doctype, 'private')

        #     doc.image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Free Sample distribution Successfully",
        }
        return
    elif frappe.request.method == "PUT":
        payload = frappe.request.json
        doc = frappe.get_doc('Free Sample Distribution', payload['fsd_name'])
        doc.update_status = payload['status']
        doc.crop_seminar = payload['crop_seminar_name']

        doc.save(ignore_permissions=True)
        frappe.response["message"] = {
            "status":True,
            "message": "Free Sample Details Updated Successfully",
        }
        
        return

   

@frappe.whitelist(allow_guest=True)
def whatsapp_to_farmer():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Whatsapp Templates", fields=["*"], filters={"type": "Daily"}, order_by="creation desc")

        himage = get_doctype_images("Whatsapp Templates",home_data[0].name,0)
        home_data[0].image = himage[0]

        # home_data[0].image = frappe.utils.get_url(home_data[0].image)
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data[0]
        }
        return

@frappe.whitelist(allow_guest=True)
def get_seminar_masters():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="GET":

        # bk_center = frappe.db.get_all("BK Center", fields=["*"])
        villages = [d.name for d in frappe.db.get_all("Village", fields=["name"])]
        venues = [d.name for d in frappe.db.get_all("Venue", fields=["name"])]

        home_data = {
            "bk_center": frappe.db.get_all("BK Center", fields=["*"]),
            "villages": villages,
            "venues": venues
        }

        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return

@frappe.whitelist(allow_guest=True)
def door_to_door_awareness():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    elif frappe.request.method == "POST":
        _data = frappe.request.json
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
            
        doc = frappe.get_doc({
            "doctype":"Door To Door Visit",
            # "posting_date": frappe.utils.nowdate(),
            "employee_location": _data['mylocation'],
            "farmer": _data['farmer_name'],
            "notes": _data['notes'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()

        if _data['image']:
            data = _data['image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Door To Door Visit"
            image = ng_write_file(data, filename, docname, doctype, 'private')

            doc.image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Report Added Successfully",
        }
        return

def get_geomitra_from_userid(email):
    geo_mitra = frappe.db.get_all("Geo Mitra", fields=["name"], filters={"linked_user": email})
    if geo_mitra: 
        return geo_mitra[0].name
    else: 
        return False

def get_farmer_from_id(name):
    farmer_check = frappe.db.get_all("Free Sample Distribution", fields=["*"], filters={"farmer": name})
    if farmer_check: 
        return farmer_check[0].update_status, farmer_check[0].name
    else: 
        return False , False

@frappe.whitelist(allow_guest=True)
def sticker_pasting():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"Sticker Pasting",
            "posting_date": frappe.utils.nowdate(),
            "employee_location": _data['mylocation'],
            "farmer": _data['farmer_name'],
            "geo_mitra": geo_mitra_id

        })
        doc.insert()
        if _data['image']:
            data = _data['image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Sticker Pasting"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.image = image

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Report Added Successfully",
        }
        return


@frappe.whitelist(allow_guest=True)
def create_sales_order():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"GEO Orders",
            "posting_date": frappe.utils.nowdate(),
            "dealer": _data['dealer_mobile'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()

        for itm in _data['cart'] :
                doc.append("products",{"item_code": itm.get('item_code'),"product_name": itm.get('title'), "uom": itm.get('uom'), "quantity": itm.get('quantity'), "rate": itm.get('rate')})

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Sales Order Successfully Created",
        }
        return

@frappe.whitelist(allow_guest=True)
def create_Advance_booking_order():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"Geo Advance Booking",
            "posting_date": frappe.utils.nowdate(),
            "dealer": _data['dealer_mobile'],
            "farmer": _data['farmer'],
            "crop": _data['crop'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()

        for itm in _data['cart'] :
                doc.append("product_kit",{"product_kit": itm.get('name'), "qty": itm.get('quantity')})

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Advance Booking Successfully Created",
        }
        return


@frappe.whitelist(allow_guest=True)
def update_dealer_stock():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"Dealer Stock",
            "posting_date": frappe.utils.nowdate(),
            "dealer": _data['dealer_mobile'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()

        for itm in _data['stock'] :
                doc.append("stock",{"product": itm.get('item_code'), "uom": itm.get('uom'),"product_name": itm.get('title'), "quantity": itm.get('quantity'), "rate": itm.get('rate')})

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Dealer Stock Successfully Updated",
        }
        return


@frappe.whitelist(allow_guest=True)
def add_dealer_payment():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    elif frappe.request.method == "POST":
        _data = frappe.request.json
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"Geo Payment Entry",
            "posting_date": frappe.utils.nowdate(),
            "employee_location": _data['mylocation'],
            "amount":_data['amount'],
            "ref_number":_data['ref_number'],
            "payment_method":_data['type'],
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id,
            "dealer":_data['dealer_mobile'],
        })
        doc.insert()
        if _data['image']:
            data = _data['image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Geo Payment Entry"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Payment Added Successfully",
        }
        return


@frappe.whitelist(allow_guest=True)
def raise_crop_alert():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    elif frappe.request.method == "POST":
        _data = frappe.request.json
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return

        doc = frappe.get_doc({
            "doctype":"Crop Alert",
            # "posting_date": frappe.utils.nowdate(),
            # "employ_location": _data['location'],
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id
        })
        doc.insert()
        if _data['image']:
            data = _data['image']
            filename = doc.name
            docname = doc.name
            doctype = "Crop Alert"
            image = ng_write_file(data, filename, docname, doctype, 'private')

        doc.image = image
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Report Added Successfully",
        }
        return

@frappe.whitelist(allow_guest=True)
def get_user_task():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    elif frappe.request.method == "GET":
        tasks = frappe.db.get_all("ToDo", fields=["*"], filters={"allocated_to": user_email})

        for t in tasks:
            regex = re.compile(r'<[^>]+>')
            t.description = regex.sub('', t.description)

        frappe.response["message"] = {
            "status":True,
            "data": tasks,
        }
        return
    
    frappe.response["message"] = {
            "status":False,
            "message": "Something Went Wrong",
        }
    return

@frappe.whitelist(allow_guest=True)
def search_farmer():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        _data = frappe.request.json
        text = f'%{_data["text"]}%'
        geo_mitra_id = get_geomitra_from_userid(user_email)

        geomitras = frappe.db.sql("""
            SELECT 
                *
            FROM
                `tabMy Farmer`
            WHERE (first_name like %s OR last_name like %s OR mobile_number like %s) AND geomitra_number = %s
            LIMIT 10
        """, (text, text, text, geo_mitra_id), as_dict=1)
        
        for g in geomitras:
           g.free_sample, g.free_sample_name = get_farmer_from_id(g.name)

        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : geomitras,
            "geo_mitra_id": geo_mitra_id
        }
        return

@frappe.whitelist(allow_guest=True)
def search_dealer():

    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        _data = frappe.request.json
        text = f'%{_data["text"]}%'
        geo_mitra_id = get_geomitra_from_userid(user_email)

        dealers = frappe.db.sql("""
            SELECT 
                *
            FROM
                `tabDealer`
            WHERE (dealer_name like %s OR contact_person like %s OR mobile_number like %s) AND geomitra_number = %s
            LIMIT 10
        """, (text, text, text, geo_mitra_id), as_dict=1)
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : dealers,
            "geo_mitra_id": geo_mitra_id
        }
        return


@frappe.whitelist(allow_guest=True)
def search_product():

    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        _data = frappe.request.json
        text = f'%{_data["text"]}%'
        geo_mitra_id = get_geomitra_from_userid(user_email)

        products = frappe.db.get_all("Product",fields=["*"] )
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : products,
            "geo_mitra_id": geo_mitra_id
        }
        return


@frappe.whitelist(allow_guest=True)
def search_crops():

    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        _data = frappe.request.json
        text = f'%{_data["text"]}%'
        geo_mitra_id = get_geomitra_from_userid(user_email)

        products = frappe.db.get_all("Crop",fields=["*"] )
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : products,
            "geo_mitra_id": geo_mitra_id
        }
        return

@frappe.whitelist(allow_guest=True)
def search_product_kit():

    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        _data = frappe.request.json
        text = f'%{_data["text"]}%'
        geo_mitra_id = get_geomitra_from_userid(user_email)

        if text :
            products = frappe.db.get_all("Product Kit",filters={"crop":_data["text"]},fields=["*"] )
        else :
            products = frappe.db.get_all("Product Kit",fields=["*"] )
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : products,
            "geo_mitra_id": geo_mitra_id
        }
        return


@frappe.whitelist(allow_guest=True)
def get_stock():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return

    if frappe.request.method =="POST":
        home_data = frappe.db.get_list("Dealer Stock", fields=["*"])
        for h in home_data:
            child_data = frappe.get_doc("Dealer Stock", h.name)
            if child_data:
                h.details = child_data
        
        frappe.response["message"] = {
            "status":True,
            "data" : home_data
        }
        return
