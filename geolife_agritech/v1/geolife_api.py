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
import calendar
import re
from datetime import datetime



@frappe.whitelist(allow_guest=True)
def send_whatsapp(mobile_no, msg):
    url = "https://api.ultramsg.com/instance7520/messages/chat"
    payload = f"token=9zsrw9upesu56s9m&to=91{mobile_no}&body={msg}"
    payload = payload.encode('utf8').decode('iso-8859-1')
    headers = {'content-type': 'application/x-www-form-urlencoded'}

    response = requests.request("POST", url, data=payload, headers=headers)
    return response.text

@frappe.whitelist(allow_guest=True)
def send_push_notification():
    header = {"Content-Type": "application/json; charset=utf-8",
            "Authorization": "Basic NGEwMGZmMjItY2NkNy0xMWUzLTk5ZDUtMDAwYzI5NDBlNjJj"}

    payload = {"app_id": "2890622f-7504-4d49-a4ed-9e69becefa4a",
            "include_player_ids": ["7ef10884-83c7-4b86-9564-d17ffc98711b"],
            "channel_for_external_user_ids": "push",
            "contents": {"en": "English Message"}}
    
    req = requests.post("https://onesignal.com/api/v1/notifications", headers=header, data=json.dumps(payload))
    
    print(req.status_code, req.reason)

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
        otp = str(random.randint(1000,9999))
        if mobile_no =="9685062116":
            otp =1234
        if mobile_no == "8319366462":
            otp=1234
        # otp = "1234"
        sms_headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        url = f"http://admin.bulksmslogin.com/api/otp.php?authkey=349851AFBrdHyz5632c330aP1&mobile=91{mobile_no}&message={otp} is your OTP for Geolife App Login, OTP is valid for 3 minutes. Do not share it with anyone. Regards, Team Geolife Digital. IjTfUVQTDQg &sender=GEOLIF&otp={otp}&DLT_TE_ID=1107168179859312292"
        r = requests.get(url, headers=sms_headers)
        
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
            if geomitra_data :
                frappe.local.response["message"] = {
                    "status": True,
                    "message": "User Already Exists",
                    "data":{
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "user_role":"Geo Mitra",
                    "geomitra_data":geomitra_data,
                    "first_name": userm[0].first_name,
                    "last_name": userm[0].last_name,
                    "mobile_no": userm[0].mobile_no,
                    "email_id": userm[0].email,
                    "role": userm[0].user_type
                    }
                }
                return
            
            dealer_data = frappe.db.get_all('Dealer', filters={'linked_user': user_email}, fields=['*'])
            if dealer_data :
                frappe.local.response["message"] = {
                    "status": True,
                    "message": "User Already Exists",
                    "data":{
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "user_role":"Dealer",
                    "dealer_data":dealer_data,
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
def Upload_image_in_dealer():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]
    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    dealer_id = get_dealer_from_userid(user_email)
    dealer_data=[]
    if frappe.request.method == "POST":
        _data = frappe.request.json
        if _data['image']:
            data = _data['image']
            filename = dealer_id
            docname = dealer_id
            doctype = _data["doctype"]
            image = ng_write_file(data, filename, docname, doctype, 'private')

            if image : 
                doc = frappe.get_doc("Dealer",dealer_id)
                doc.qr_code = image
                doc.save()
                dealer_data.append(doc)


        frappe.response["message"] = {
            "status":True,
            "message": "Image Uploaded Successfully",
            "qr_code":doc.qr_code,
            "data":{
                "api_key": api_key,
                "api_secret": api_sec,
                "user_role":"Dealer",
                "dealer_data":dealer_data
            }
        }
        return
    

    

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

        if crop_data.get('is_attendance'):
            for itm in crop_data['crop_seminar_attendance'] :
                crop.append("crop_seminar_attendance",{"farmer":itm,"posting_date": frappe.utils.nowdate()})
            if crop_data.get('is_attendance_image') :
                for img in crop_data['images'] :
                    image_url = ng_write_file(img, crop_data.get('name'), crop_data.get('name'), 'Crop Seminar', 'private')
                    crop.append("crop_seminar_attendance", { "image": frappe.utils.get_url(image_url),"posting_date": frappe.utils.nowdate()})
            
        if crop_data.get('is_pre_activity'):
            crop.pre_activities = []
            for itm in crop_data['pre_activities'] :
                crop.append("pre_activities",{"activity_name": itm['activity_name'], "activity_status":itm['activity_status']})

        if crop_data.get('is_post_activity'):
            crop.post_activities = []
            for itm in crop_data['post_activities'] :
                crop.append("post_activities",{"activity_name": itm['activity_name'], "activity_status":itm['activity_status']})
            
        if crop_data.get('is_upload_photos'):
            for itm in crop_data['image'] :
                image_url = ng_write_file(itm, crop_data.get('name'), crop_data.get('name'), 'Crop Seminar', 'private')
                crop.append("upload_photos", { "seminar_image_path": frappe.utils.get_url(image_url)})

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
    geo_mitra_id = get_geomitra_from_userid(user_email)

    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Daily Activity", filters={"posting_date": frappe.utils.nowdate(), "geo_mitra":geo_mitra_id}, fields=["posting_date","activity_name","activity_type","notes"])
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
            "activity_name":  _data.get('activity_name') if _data.get('activity_type') else '',
            "activity_type": _data.get('activity_type') if _data.get('activity_type') else '',
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
        
        if doc.activity_type == 'Start Day' :
            doc.save()
            frappe.db.commit()
            videoData = frappe.db.get_list('Session Videos', filters={"session_date":frappe.utils.nowdate()}, fields=["name","session_date","youtube_video"])
            if videoData :
                faq = frappe.get_doc('Session Videos',videoData[0].name)
                videoData[0].faq = faq
                frappe.response["message"] = {
                    "status":True,
                    "message": "Daily Activity Added Successfully",
                    "video":faq
                }
                return
        if doc.activity_type == 'End Day' :
            doc.session_started = _data['session']
            doc.session_enddate = now()
            doc.save()
            frappe.db.commit()
            
            frappe.response["message"] = {
                    "status":True,
                    "message": "Session Successfully End",
                }
            return

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Daily Activity Added Successfully",
            "video":False
        }
        return

@frappe.whitelist(allow_guest=True)
def get_attendance():
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

    if frappe.request.method =="GET":
        mdata =[]
        count_days=[]
        home_data = frappe.db.get_list("Daily Activity", filters={"activity_type":"End Day","activity_name":"End Day", "geo_mitra":geo_mitra_id}, fields=["*"])
        for h in home_data:
            if h.session_enddate is not None:
                start_time_str = h.session_started.strftime("%Y-%m-%d %H:%M:%S")
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_time_str = h.session_enddate.strftime("%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                time_difference = end_time - start_time
                if time_difference :
                    value = time_difference.total_seconds() / 3600
                    if value > 3 :
                        count_days.append({ "value": value, "label": start_time.strftime("%d-%b")})
                        h.value = count_days
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data[0].value
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
def activity_for():
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
        home_data = frappe.db.get_list("Geo Activity Type", fields=["name","json"])
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
    
    geo_mitra_id = get_geomitra_from_userid(user_email)


    if frappe.request.method =="GET":
        home_data = frappe.db.get_list("Geo Expenses",filters={"posting_date": ['=', frappe.utils.nowdate()],"geo_mitra":geo_mitra_id}, fields=["name","posting_date","expense_type","amount","against_expense","notes"])
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
            "notes": data.get('notes') if _data.get('notes') else 0 ,
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
        if _data['image']:
            data = _data['image']
            filename = doc.name
            docname = doc.name
            doctype = "Free Sample Distribution"
            image = ng_write_file(data, filename, docname, doctype, 'private')

            doc.image = image
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


@frappe.whitelist(allow_guest=True)
def create_farmer():
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

        db_check = frappe.db.exists("My Farmer", _data['mobile_no'])
        if db_check :
            frappe.response["message"] = {
            "status":True,
            "message": "Farmer Already Added",
            }
            return

        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
            
        if  _data['first_name']: 
            doc = frappe.get_doc({
            "doctype":"My Farmer",
            "register_date": frappe.utils.nowdate(),
            "first_name": _data['first_name'],
            "last_name": _data['last_name'],
            "mobile_number": _data['mobile_no'],
            "pincode": _data['pincode'],
            "city": _data['city'],
            "geomitra_number": geo_mitra_id,
            "farm_acre": _data['acre'],
            "app_installed":False
            })
        else :
            doc = frappe.get_doc({
            "doctype":"My Farmer",
            "register_date": frappe.utils.nowdate(),
            "first_name": _data['farmer_name'],
            "mobile_number": _data['mobile_no'],
            "geomitra_number": geo_mitra_id,
            "app_installed":"Not Installed"
            })
        doc.insert()
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Farmer Added Successfully",
        }
        return



@frappe.whitelist(allow_guest=True)
def submit_quiz():
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

        db_check = frappe.db.exists("Geo Mitra Points", {"geo_mitra":geo_mitra_id,"posting_date":frappe.utils.nowdate()})
        if db_check :
            frappe.response["message"] = {
            "status":True,
            "message": "Quiz Already Played",
            }
            return

        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
            
        doc = frappe.get_doc({
            "doctype":"Geo Mitra Points",
            "posting_date": frappe.utils.nowdate(),
            "points": _data['points'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Answers Submited Successfully",
        }
        return

def get_geomitra_from_userid(email):
    geo_mitra = frappe.db.get_all("Geo Mitra", fields=["name"], filters={"linked_user": email})
    if geo_mitra: 
        return geo_mitra[0].name
    else: 
        return False
    
def get_dealer_from_userid(email):
    dealer = frappe.db.get_all("Dealer", fields=["name"], filters={"linked_user": email})
    if dealer: 
        return dealer[0].name
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
    
    elif frappe.request.method == "PUT":
        _data = frappe.request.json

        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
        if _data['payment_method'] == 'UPI' :
            doc = frappe.get_doc({
            "doctype":"Geo Payment Entry",
            "posting_date": frappe.utils.nowdate(),
            "amount":_data['amount'],
            "payment_method":_data['payment_method'],
            "ref_number":_data['ref_number'],
            "geo_mitra":geo_mitra_id,
            "dealer":_data['dealer_mobile'],
            })
            doc.insert()
            if _data['image']:
                data = _data['image']
                filename = doc.name
                docname = doc.name
                doctype = "Geo Payment Entry"
                image = ng_write_file(data, filename, docname, doctype, 'private')
                doc.image = image
            doc.save()
            frappe.response["message"] = {
                "status":True,
                "message": "Advance Booking Successfully Created",
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
            "booking_date": _data['expected_date'],
            "payment_method": _data['payment_method'],
            "amount": _data['amount'],
            "geo_mitra": geo_mitra_id,
        })
        doc.insert()
        for itm in _data['cart'] :
                doc.append("product_kit",{"product_kit": itm.get('name'), "qty": itm.get('quantity')})
        # doc.farmer_msg = send_whatsapp(doc.farmer, f"HI {doc.farmer} your Advance booking order id is {doc.name}")
        doc.dealer_msg = send_whatsapp(doc.dealer, f"HI {doc.dealer} your have a new Advance booking order id is {doc.name}")

        if _data['payment_method'] == 'UPI' :
            vdoc = frappe.get_doc({
            "doctype":"Geo Payment Entry",
            "posting_date": frappe.utils.nowdate(),
            "amount":_data['amount'],
            "payment_method":_data['payment_method'],
            "ref_number":doc.name,
            "geo_mitra":geo_mitra_id,
            "dealer":_data['dealer_mobile'],
            })
            vdoc.insert()
            if _data['image']:
                data = _data['image']
                filename = vdoc.name
                docname = vdoc.name
                doctype = "Geo Payment Entry"
                image = ng_write_file(data, filename, docname, doctype, 'private')
                vdoc.image = image
            vdoc.save()

        doc.save()
        frappe.db.commit()
       
        frappe.response["message"] = {
            "status":True,
            "message": "Advance Booking Successfully Created",
            "name":doc.name
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
            "dealer":_data['dealer_mobile']
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
def add_dealer_Cash_payment():
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
        dealer_id = get_dealer_from_userid(user_email)
        
        if dealer_id == False:
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
            "payment_method":"Cash",
            "notes": _data['notes'],
            "geo_mitra":_data['geo_mitra'],
            "dealer": dealer_id
        })
        doc.insert()
        if _data['image']:
            data = _data['image']
            filename = doc.name
            docname = doc.name
            doctype = "Geo Payment Entry"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.image = image
        doc.save()
        frappe.db.commit()

        if doc :
           orders = frappe.db.get_list("Geo Advance Booking",filters={"geo_mitra":doc.geo_mitra,"dealer":doc.dealer,"payment_method":"Cash", "is_cash_received":0}, fields=["*"])
           for ord in orders :
               update_order = frappe.get_doc("Geo Advance Booking",ord.name)
               update_order.is_cash_received = True
               update_order.save()

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
            "posting_date": frappe.utils.nowdate(),
            # "employ_location": _data['location'],
            "employee_location": _data['mylocation'],
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id
        })
        doc.insert()
        if _data['image']:
            data = _data['image'][0]
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
    geo_mitra_id = get_geomitra_from_userid(user_email)
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
            "dashboard":dashboard_data(geo_mitra_id)
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

        if _data.get("all_farmer") :
            geomitras = frappe.db.sql("""
                SELECT 
                    *
                FROM
                    `tabMy Farmer`
                WHERE first_name like %s OR last_name like %s OR mobile_number like %s
                LIMIT 10
            """, (text, text, text), as_dict=1)
        else :
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
def search_pravakta_farmer():
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
            WHERE (first_name like %s OR last_name like %s OR mobile_number like %s) AND geomitra_number = %s AND gpk=1
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
def search_farmer_orders():
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

        geoOrders = frappe.db.sql("""
            SELECT 
                *
            FROM
                `tabGeo Advance Booking`
            WHERE (name like %s OR farmer like %s OR dealer like %s) AND geo_mitra = %s AND posting_date BETWEEN %s AND %s 
            ORDER BY posting_date DESC
        """, (text, text, text, geo_mitra_id,_data["from_date"],_data["to_date"]), as_dict=1)

        for m in geoOrders :
            mn = frappe.db.get_list("Geo Payment Entry", filters={"ref_number":m.name},fields=["*"])
            if mn :
                image = get_doctype_images('Geo Payment Entry', mn[0].get('name'), 1)
                if image :
                    m.image=image[0].get("image")

            farmer_name = frappe.get_doc("My Farmer",m.farmer)
            m.farmer_name= farmer_name.first_name
            m.last_name= farmer_name.last_name
            dealer_name = frappe.get_doc("Dealer", m.dealer)
            m.dealer_name=dealer_name.dealer_name
            mdata = frappe.db.sql(""" SELECT * FROM `tabGeo Advance Booking Details` WHERE parent = %s """, (m.name), as_dict=1)
            if mdata :
                for md in mdata :
                    product_kit = frappe.get_doc("Product Kit",md.get("product_kit"))
                    if product_kit :
                        m.kit_type =product_kit.get("cnp_kit_type")
                        m.crop_bundle =product_kit.get("crop_bundle")
                m.mdata=mdata
            else :
                m.mdata = 'not available'
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : geoOrders,
            "geo_mitra_id": geo_mitra_id
        }
        return


@frappe.whitelist(allow_guest=True)
def dealer_search_farmer_orders():
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
        dealer_id = get_dealer_from_userid(user_email)

        geoOrders = frappe.db.sql("""
            SELECT 
                *
            FROM
                `tabGeo Advance Booking`
            WHERE (name like %s OR farmer like %s OR geo_mitra like %s) AND dealer = %s AND posting_date BETWEEN %s AND %s
            LIMIT 10
        """, (text, text, text, dealer_id, _data["from_date"],_data["to_date"]), as_dict=1)

        # for m in geoOrders :
        #     farmer_name = frappe.get_doc("My Farmer",m.farmer)
        #     m.farmer_name= farmer_name.first_name
        #     dealer_name = frappe.get_doc("Dealer", m.dealer)
        #     m.dealer_name=dealer_name.dealer_name
        #     mdata = frappe.db.sql(""" SELECT * FROM `tabGeo Advance Booking Details` WHERE parent = %s """, (m.name), as_dict=1)
        #     if mdata :
        #         m.mdata=mdata
        #     else :
        #         m.mdata = 'not available'
        
        for m in geoOrders :
            mn = frappe.db.get_list("Geo Payment Entry", filters={"ref_number":m.name},fields=["*"])
            if mn :
                image = get_doctype_images('Geo Payment Entry', mn[0].get('name'), 1)
                if image :
                    m.image=image[0].get("image")

            farmer_name = frappe.get_doc("My Farmer",m.farmer)
            m.farmer_name= farmer_name.first_name
            m.last_name= farmer_name.last_name
            dealer_name = frappe.get_doc("Dealer", m.dealer)
            m.dealer_name=dealer_name.dealer_name
            mdata = frappe.db.sql(""" SELECT * FROM `tabGeo Advance Booking Details` WHERE parent = %s """, (m.name), as_dict=1)
            if mdata :
                for md in mdata :
                    product_kit = frappe.get_doc("Product Kit",md.get("product_kit"))
                    if product_kit :
                        m.kit_type =product_kit.get("cnp_kit_type")
                        m.crop_bundle =product_kit.get("crop_bundle")
                m.mdata=mdata
            else :
                m.mdata = 'not available'
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : geoOrders,
            "geo_mitra_id": dealer_id
        }
        return




@frappe.whitelist(allow_guest=True)
def submit_advance_booking():
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
        dealer_id = get_dealer_from_userid(user_email)

        doc = frappe.get_doc("Geo Advance Booking",_data.get('order_id'))
        if doc.payment_method == "Cash" :
            if doc.is_cash_received ==0 :
                frappe.response["message"] = {
                    "status":False,
                    "message": "Order Payment Details Not Found",
                }
                return

        doc.submit()

        if doc :
            incentive =0

            if _data.get('products') :
                for itm in _data.get('products') :
                    getProduct = frappe.get_doc("Product Kit",itm.get("title"), fields=["*"])
                    if getProduct.get("cnp_kit_type")=="With Soil Application" :
                        incentive= frappe.db.get_single_value('GeoLife Setting', 'incentive_with_soil_kit')
                    else :
                        incentive= frappe.db.get_single_value('GeoLife Setting', 'incentive_without_soil_kit')

                    mdoc = frappe.get_doc({"doctype":"Geo Mitra Incentive",
                                        "dealer":dealer_id,
                                        "order_id":_data.get('order_id'),
                                        "product_kit":getProduct.get('name'),
                                        "geo_mitra":doc.get('geo_mitra'),
                                        "crop_type":getProduct.get("cnp_kit_type"),
                                        "posting_date": frappe.utils.nowdate(),
                                        "incentive":incentive*itm.get("percent"),
                                        "qty":itm.get("percent")
                                        })
                    mdoc.insert()
                    # mdoc.incentive = mdoc.incentive*mdoc.qty
                    # mdoc.save()
        farmer = frappe.get_doc("My Farmer",doc.farmer)
        if farmer :
            doc.farmer_msg = send_whatsapp(doc.farmer, f"HI {farmer.first_name} {farmer.last_name} your Advance booking order id is {doc.name} is Successfully completed ")
        geoMitra = frappe.get_doc("Geo Mitra",doc.geo_mitra)
        if geoMitra :
            doc.geo_mitra_msg = send_whatsapp(doc.geo_mitra, f"Dear, {geoMitra.first_name}{geoMitra.last_name} your Advance booking order id {doc.name} is Successfully completed.  ")
        
        frappe.response["message"] = {
            "status":True,
            "message": "Order successfully completed",
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

        # dealers = frappe.db.sql("""
        #     SELECT 
        #         *
        #     FROM
        #         `tabDealer`
        #     WHERE (dealer_name like %s OR contact_person like %s OR mobile_number like %s) AND geomitra_number = %s
        #     LIMIT 10
        # """, (text, text, text, geo_mitra_id), as_dict=1)

        mdealers = frappe.db.sql("""
            SELECT 
                *
            FROM
                `tabDealer Geo Mitra`
            WHERE geo_mitra = %s
            LIMIT 10
        """, (geo_mitra_id), as_dict=1)

        dealers=[]
        for md in mdealers :
            dealers.append(frappe.get_doc("Dealer",md.parent))

        # dealers = frappe.db.get_list("Dealer", filters= [['DGO List', 'geo_mitra', 'in', geo_mitra_id]], fields=["*"])
        for m in dealers :
            m.qr_code = frappe.utils.get_url(m.qr_code)
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : dealers,
            "geo_mitra_id": geo_mitra_id
        }
        return

@frappe.whitelist(allow_guest=True)
def search_geomitra():

    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    dealer_id = get_dealer_from_userid(user_email)

    if frappe.request.method =="GET":
        geomitras = frappe.get_doc("Dealer",dealer_id)
        for gm in geomitras.dgo_list :
            cash_amount = frappe.db.sql(""" SELECT sum(amount) as amount FROM `tabGeo Advance Booking` WHERE dealer=%s AND geo_mitra= %s AND payment_method ='Cash' AND is_cash_received=0  """, (dealer_id, gm.get("geo_mitra")), as_dict=1)
            upi_amount  = frappe.db.sql(""" SELECT sum(amount) as amount FROM `tabGeo Advance Booking` WHERE dealer=%s AND geo_mitra= %s AND payment_method ='UPI' """, (dealer_id, gm.get("geo_mitra")), as_dict=1)
            if cash_amount :
                gm.geo_mitra_cash=cash_amount[0].amount
            if upi_amount :
                gm.geo_mitra_upi=upi_amount[0].amount
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : geomitras.dgo_list,
            "geo_mitra_id": dealer_id,
            "qr_code":geomitras.get("qr_code")
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
def farmer_meeting():

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
        geo_mitra_id = get_geomitra_from_userid(user_email)

        doc = frappe.get_doc({
            "doctype":"Farmer Meeting",
            "posting_date": frappe.utils.nowdate(),
            "employee_location": _data['mylocation'],
            "agenda":_data['agenda'],
            "location":_data['location'],
            "no_attendees":_data['no_attendees'],
            "notes": _data['notes'],
            "geo_mitra":geo_mitra_id,
            
        })
        doc.insert()
        if _data['image']:
            data = _data['image'][0]
            filename = doc.name
            docname = doc.name
            doctype = "Farmer Meeting"
            image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.image = image
        doc.save()
        frappe.db.commit()
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
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
        text = _data["text"]
        geo_mitra_id = get_geomitra_from_userid(user_email)
        
        products = frappe.db.get_list("Product Kit",filters={"crop_bundle":_data.get("text"),"cnp_kit_type":_data.get("cnp_type")},fields=["*"] )
        for product in products :
            price = frappe.db.get_list("Dealer Price List",filters={"dealer":_data.get("dealer"),"product_kit":product.name,"price_status":"Active"}, fields=["*"])
            if price :
                product.price =price[0].price
                product.discount = price[0].discount
        
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


@frappe.whitelist(allow_guest=True)
def dealer_payments_data():
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
        dealer_id = get_dealer_from_userid(user_email)

        geoPayments = frappe.db.get_all("Geo Payment Entry", filters={'dealer':dealer_id,'posting_date': ['>=', _data['from_date']],'posting_date': ['<=', _data['to_date']]}, fields=["*"])

        # for m in geoOrders :
        #     farmer_name = frappe.get_doc("My Farmer",m.farmer)
        #     m.farmer_name= farmer_name.first_name
        #     dealer_name = frappe.get_doc("Dealer", m.dealer)
        #     m.dealer_name=dealer_name.dealer_name
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : geoPayments,
            "dealer_id": dealer_id
        }
        return


@frappe.whitelist(allow_guest=True)
def dashboard_data(geo_mitra):
    if frappe.request.method =="GET":
        Dashboard = {"present_days":""}
        count_days=0
        present_days=""
        home_data = frappe.db.get_list("Daily Activity", filters={"activity_type":"End Day","activity_name":"End Day", "geo_mitra":geo_mitra}, fields=["*"])
        for h in home_data:
            if h.session_enddate is not None:
                start_time_str = h.session_started.strftime("%Y-%m-%d %H:%M:%S")
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_time_str = h.session_enddate.strftime("%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                time_difference = end_time - start_time
                if time_difference :
                    value = time_difference.total_seconds() / 3600
                    if value > 3 :
                        count_days = count_days+1
                        h.value = count_days
        Dashboard["present_days"] = f"{count_days}/{calendar.monthrange(2023, 1)[1]}"

        Dashboard["kit_booking"] = frappe.db.count("Geo Advance Booking", {"geo_mitra":geo_mitra})
        Dashboard["incentive"] = frappe.db.count("Geo Mitra Incentive", {"geo_mitra":geo_mitra})
        Dealers_count=0
        Dealers = frappe.db.get_all("Dealer", fields=["*"])
        for dealer in Dealers :
            ddealer = frappe.get_doc("Dealer",dealer.name)
            if ddealer.dgo_list:
                for d in ddealer.dgo_list :
                    if d.geo_mitra == geo_mitra :
                        Dealers_count = Dealers_count+1
        dealer_visit_data = frappe.db.count("Daily Activity", {"activity_type":"Dealer Appointment", "geo_mitra":geo_mitra})
        if dealer_visit_data :
            dealer_not_visit = Dealers_count-dealer_visit_data
        else :
            dealer_not_visit=0
        Dashboard["dealer_not_visit"] = f"{dealer_not_visit}/{Dealers_count}"

        Dashboard["tft_downloads"] = frappe.db.count("Door To Door Visit", {"geo_mitra":geo_mitra})
        Dashboard["farmer_connected"] = frappe.db.count("My Farmer", {"geomitra_number":geo_mitra})
        Dashboard["new_dealer"] = Dealers_count
        Dashboard["target_achievement"] = ""

        inc = frappe.db.get_list("Geo Mitra Incentive", filters={"geo_mitra":geo_mitra}, fields=["*"])
        incentive =0
        if inc :
            for i in inc :
                incentive =incentive+i.get('incentive')


        Dashboard["incentive"] = incentive
      
        return Dashboard
