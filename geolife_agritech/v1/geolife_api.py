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
def send_whatsapp(mobile_no,tamplate_name, param):
    parameters=[]
    for v in param :
        parameters.append( {
            "type": "text",
            "text": v
        },)
    url = "https://graph.facebook.com/v17.0/101326632874700/messages"
    payload = { "messaging_product": "whatsapp", "to": mobile_no, "type": "template", 
               "template": {
                    "name": tamplate_name,
                    "language": {
                    "code": "en_US"
                },
                "components": [
                    {
                        "type": "body",
                        "parameters": parameters
                    }
                ]
            }
            }
    # payload = payload.encode('utf8').decode('iso-8859-1')
    # frappe.log_error('whatsapp',payload)
    headers = {'Authorization': 'Bearer EAAKkYgHIqkIBAK8axW3TJ05uOgHpyzVyuQpZBiFAYJrZAv6C4gt5H8T7R0ssIddK4kCIZChqj5R3MJG3nbbxLcVefMVkkOC40ZB8akhfbyAAxcqVXUPkbKsTeUVVZCH9wxADjXeSZBcstbcWXbFqlHbQyNx6JRHx1Hu9kPwZCuO6DXeUcOitNPc','Content-Type': 'application/json'}

    response = requests.request("POST", url, data=json.dumps(payload), headers=headers)
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
def generate_otp(mobile_no,hashcode):
    # frappe.log_error('Check from generate_otp user from0',json.loads(mobile_no))
    # frappe.log_error('Check from generate_otp user json from0',json.dumps(mobile_no))


    if not mobile_no :
        frappe.local.response["message"] = {
            "status": False,
            "message": "Invalid Mobile Number"
        }
        return
    
    user_email = frappe.db.get_all('User', filters={'mobile_no': mobile_no,'enabled':1}, fields=['email'])
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
        url = f"http://admin.bulksmslogin.com/api/otp.php?authkey=349851AFBrdHyz5632c330aP1&mobile=91{mobile_no}&message={otp} is your OTP for Geolife App Login, OTP is valid for 3 minutes. Do not share it with anyone. Regards, Team Geolife Digital. {hashcode}&sender=GEOLIF&otp={otp}&DLT_TE_ID=1107169060755325316"
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
        frappe.log_error('Check from generate_otp error',e)

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
        return

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
        filename_ext = f'/home/geolife/frappe-bench/sites/{frappe.local.site}/{file_type}/files/{filename}.png'
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
        frappe.log_error('ng_write_file', str(e))
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
def Evening_7pm_Notifications():
    url = "https://onesignal.com/api/v1/notifications"

    payload = "{\"app_id\": \"2890622f-7504-4d49-a4ed-9e69becefa4a\",\r\n            \"included_segments\": [\"Subscribed Users\"],\r\n            \"contents\": {\"en\": \"Dear Geo Mitra, Please End Your Day Today In Geolife App When Your Today's work is done\"}}"
    headers = {
    'Authorization': 'Basic OTVjY2YyZmUtODA0Zi00ZDZmLWI5ZWMtNGNmNDMyNDZiNzMw',
    'Content-Type': 'application/json; charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    # frappe.log_error('Evening_7pm_Notifications', response.text)
    
    return
    
@frappe.whitelist(allow_guest=True)
def daily_day_end():
    url = "https://onesignal.com/api/v1/notifications"

    payload = "{\"app_id\": \"2890622f-7504-4d49-a4ed-9e69becefa4a\",\r\n            \"included_segments\": [\"Subscribed Users\"],\r\n            \"contents\": {\"en\": \"Dear Geo Mitra, please start new sessoin on your Geolife App your previous session is closed\"}}"
    headers = {
    'Authorization': 'Basic OTVjY2YyZmUtODA0Zi00ZDZmLWI5ZWMtNGNmNDMyNDZiNzMw',
    'Content-Type': 'application/json; charset=utf-8'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    # print(req.status_code, req.reason)
    # frappe.log_error('daily_day_end', response.text)

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
        _data = frappe.form_dict
        home_data = frappe.db.get_list("Daily Activity", filters=[["posting_date",'between', [_data.get('from_date'),_data.get('to_date')]],{"geo_mitra":geo_mitra_id}], fields=["*"])
        for h in home_data:
            activity = frappe.get_doc("Daily Activity", h.get('name'))
            h.activity_type=[]
            for d in activity.multi_activity_types :
                h.activity_type.append(d.activity_type) 
            image = get_doctype_images('Daily Activity', h.name, 1)  
            if h.dealer:
                dealer = frappe.get_doc("Dealer",h.dealer)
                h.dealer = dealer.dealer_name

            if h.farmer:
                farmer = frappe.get_doc("My Farmer",h.farmer)
                h.farmer = f"{farmer.first_name} {farmer.last_name or ''}"
            # if h.multi_activity_types:
            #     icon = frappe.get_doc("Activity Type", h.multi_activity_types[0].activity_type)
            # if icon :
            #     h.icon=icon.icon

            if image:
                h.image = image[0]['image']
            else:
                h.image = ""
        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : home_data
        }
        return
    
    elif frappe.request.method == "POST":
        _data = frappe.request.json
        # frappe.log_error("Start day", _data)
        
        if geo_mitra_id == False:
            frappe.response["message"] = {
                "status": False,
                "message": "Please map a geo mitra with this user",
                "user_email": user_email
            }
            return
        doc = frappe.get_doc({
            "doctype":"Daily Activity",
            "posting_date": frappe.utils.nowdate(),
            "activity_name":  f" {_data.get('type')} Visit" if _data.get('type') else '',
            "notes": _data.get('notes') if _data.get('notes') else '',
            "party_type": _data.get('type') if _data.get('type') else '',
            "dealer": _data.get('party') if _data.get('type')=='Dealer' else '',
            "farmer": _data.get('party') if _data.get('type')=='Farmer' else '',
            "geo_mitra":geo_mitra_id,
            "my_location": _data.get('mylocation') if _data.get('mylocation') else '',
            "longitude": _data.get('longitude') if _data.get('longitude') else '',
            "latitude": _data.get('latitude') if _data.get('latitude') else ''
                            })
        
        doc.insert()
        if _data.get('activity_type'):
            doc.multi_activity_types=[]
            if type(_data.get('activity_type')) is list:
                for itm in _data.get('activity_type'):
                    cdoc =frappe.get_doc({
                        "doctype":"Activity Type Multiselect",
                        "posting_date": frappe.utils.nowdate(),
                        "activity_name":  _data.get('party') if _data.get('party') else '',
                        "notes": _data.get('notes') if _data.get('notes') else '',
                        "parent": doc.name,
                        "parentfield":"multi_activity_types",
                        "parenttype": "Daily Activity",
                        "activity_type":itm
                    }).insert()
                    cdoc.save()
                    doc.multi_activity_types.append(cdoc)

                    if itm =='Start Day' :
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
                    if itm == 'End Day':
                        doc.session_started = _data['session']
                        doc.session_enddate = now()
                        doc.save()
                        frappe.db.commit()
                        
                        frappe.response["message"] = {
                                "status":True,
                                "message": "Session Successfully End",
                            }
                        return

            else:
                cdoc =frappe.get_doc({
                        "doctype":"Activity Type Multiselect",
                        "posting_date": frappe.utils.nowdate(),
                        "activity_name":  _data.get('party') if _data.get('party') else '',
                        "notes": _data.get('notes') if _data.get('notes') else '',
                        "parent": doc.name,
                        "parentfield":"multi_activity_types",
                        "parenttype": "Daily Activity",
                        "activity_type":itm
                }).insert()
                cdoc.save()
                doc.multi_activity_types.append(cdoc)
        # if doc.get('activity_type') == "Dealer Visit" :
        #     if _data.get('multi_activity_types'):
        #         inserted=[]
        #         for itm in _data.get('multi_activity_types') :
                    
        #             if itm not in inserted:
        #                 inserted.append(itm)
        #             # doc.multi_activity_types.append({"activity_type":itm,"modified":frappe.utils.nowdate()})
        #                 doc = frappe.get_doc({
        #                     "doctype":"Daily Activity",
        #                     "posting_date": frappe.utils.nowdate(),
        #                     "activity_name":  _data.get('activity_name') if _data.get('activity_type') else 'Dealer visit',
        #                     "activity_type": itm,
        #                     "notes": _data['notes'],
        #                     "dealer": _data.get('dealer') if _data.get('dealer') else '',
        #                     "geo_mitra":geo_mitra_id,
        #                     "my_location": _data['mylocation'],


        #                 })
        #                 doc.insert()

        
            if _data.get('image'):
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
        home_data = frappe.db.get_list("Daily Activity", filters=[["Activity Type Multiselect","activity_type","in",["End Day"]],["Daily Activity","geo_mitra","=",geo_mitra_id],["Daily Activity","posting_date","Between",[datetime.today().replace(day=1),datetime.now().strftime('%Y-%m-%d')]]], fields=["*"])
        # frappe.log_error(datetime.today().replace(day=1))
        for h in home_data:
            if h.creation >= datetime.today().replace(day=1):
                if h.session_enddate is not None:
                    start_time_str = h.session_started.strftime("%Y-%m-%d %H:%M:%S")
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    end_time_str = h.session_enddate.strftime("%Y-%m-%d %H:%M:%S")
                    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                    time_difference = end_time - start_time
                    if time_difference :
                        value = time_difference.total_seconds() / 3600
                        if value > 1 :
                            count_days.append({ "value": value, "label": start_time.strftime("%d-%b")})
                            h.value = count_days
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : count_days,
            # "data1" : datetime.today().replace(day=1),
            # "homedata" : home_data[0].creation,

        }
        return


@frappe.whitelist(allow_guest=True)
def checkuser():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": True,
            "message": "Unauthorised Access",
        }
        return
    geo_mitra_id = get_geomitra_from_userid(user_email)
    # frappe.log_error('Check user',geo_mitra_id)
    if not geo_mitra_id :
        frappe.response["message"] = {
            "status": True,
            "message": "Geo Mitra not found",
        }
        return

    if frappe.request.method =="POST":
        mdata =[]
        count_time=0
        home_data = frappe.db.get_list("Daily Activity", filters=[["Activity Type Multiselect","activity_type","in",["Start Day"]],["Daily Activity","posting_date","=", frappe.utils.nowdate()], ["Daily Activity", "geo_mitra" ,"=", geo_mitra_id]], fields=["*"])
        
        if home_data:
            for h in home_data:
                if h.session_enddate is not None:
                    start_time_str = h.session_started.strftime("%Y-%m-%d %H:%M:%S")
                    start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                    end_time_str = h.session_enddate.strftime("%Y-%m-%d %H:%M:%S")
                    end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                    time_difference = end_time - start_time
                    if time_difference :
                        value = time_difference.total_seconds() / 3600
                        count_time = count_time+value
                        if h.session_started.strftime("%Y-%m-%d") != frappe.utils.nowdate():
                            frappe.response["message"] = {
                                "status":False,
                                "message": "big date",
                            }
                            return
            # if count_time >= 8 :
            #     frappe.response["message"] = {
            #         "status":False,
            #         "message": "small",
            #     }
            #     return
            frappe.response["message"] = {
                "status":True,
                "message": "",
            }
            return
        frappe.response["message"] = {
                "status":False,
                "message": "small",
                "data":home_data
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
        home_data = frappe.db.get_list("Activity Type", fields=["activity_type","name","icon","activity_for"], filters={"type":"Show"})
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
        _data = frappe.form_dict
        home_data = frappe.db.get_list("Geo Expenses",filters=[["posting_date",'between', [_data.get('from_date'),_data.get('to_date')]],{"geo_mitra":geo_mitra_id}], fields=["*"])
        for hd in home_data:
            if hd.amount:
                hd.amount = float(hd.get('amount'))
            # if himage :
            #     hd.image = himage

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
                
        try:
            doc = frappe.get_doc({
            "doctype":"Geo Expenses",
            "posting_date": frappe.utils.nowdate(),
            "expense_type": _data['expense_type'],
            "amount" : _data.get('amount') if _data.get('amount') else 0,
            "notes": _data.get('notes') if _data.get('notes') else 0 ,
            "geo_mitra":geo_mitra_id,
            "vehical_type" : _data.get('vehical_type') if _data.get('vehical_type') else '',
            "fuel_type" : _data.get('fuel_type') if _data.get('fuel_type') else '',
            "odometer_start" : _data.get('odometer_start') if _data.get('odometer_start') else '',
            "odometer_end" : _data.get('odometer_end') if _data.get('odometer_end') else '',
            "liters" : _data.get('liters') if _data.get('liters') else '',
            "employee_location": _data['mylocation'],
            "vehicale_type":_data.get('vehicale_type') if _data.get('vehicale_type') else '',
            "longitude": _data.get('longitude') if _data.get('longitude') else '',
            "latitude": _data.get('latitude') if _data.get('latitude') else ''

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
                "message": "Expense Added Successfully",
            }
            return
        except Exception as e:
            frappe.log_error('Expense Create',str(e))
            frappe.response["message"] = {
                "status":True,
                "message": "Expense Not Created",
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
                
        doc = frappe.get_doc("Geo Expenses", _data.get('name'))
        doc.odometer_start = _data.get('odometer_start')
        doc.odometer_end = _data.get('odometer_end')
        doc.notes = _data.get('notes') if _data.get('notes') else ''
        doc.end_longitude =_data.get('longitude') if _data.get('longitude') else ''
        doc.end_latitude = _data.get('latitude') if _data.get('latitude') else ''

        # km = doc.odometer_end-doc.odometer_start
        # petrol= 10 if doc.vehicle=='Four Wheeler' else 3.5
        doc.amount = _data.get('amount') if _data.get('amount') else ''
        

        # if _data['odometer_start_image']:
        #     data = _data['odometer_start_image'][0]
        #     filename = doc.name
        #     docname = doc.name
        #     doctype = "Geo Expenses"
        #     image = ng_write_file(data, filename, docname, doctype, 'private')
        #     doc.odometer_start_image = image

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
            "message": "Expense Updated Successfully",
        }
        return

@frappe.whitelist(allow_guest=True)
def update_geo_ledger_report():
    # frappe.log_error('update_geo_ledger_report',frappe.request.headers.get("Authorization"))
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
        try:
            _data = frappe.form_dict
            doc = frappe.get_doc("Geo Mitra Ledger Report", _data.get('name'))
            doc.workflow_state = _data.get('workflow_state') if _data.get('workflow_state') else ''
            doc.save()
            frappe.db.commit()
            frappe.response["message"] = {
                "status": True,
                "message": "Updated report",
                }
            return 
        except:
            frappe.log_error('error update_geo_ledger_report')

    

@frappe.whitelist(allow_guest=True)
def geo_ledger_report():
    api_key  = frappe.request.headers.get("Authorization")[6:21]
    api_sec  = frappe.request.headers.get("Authorization")[22:]
    
    url = frappe.db.get_single_value('GeoLife Setting', 'url')
    apikey = frappe.db.get_single_value('GeoLife Setting', 'api_key')
    apisec = frappe.db.get_single_value('GeoLife Setting', 'api_secret')
    headers = {'Authorization': f'token {apikey}:{apisec}','Content-Type': 'application/json'}

    user_email = get_user_info(api_key, api_sec)
    if not user_email:
        frappe.response["message"] = {
            "status": False,
            "message": "Unauthorised Access",
        }
        return
    geo_mitra_id = get_geomitra_from_userid(user_email)

    if frappe.request.method =="GET":
        _data = frappe.form_dict
        # home_data = frappe.db.get_list("Geo Mitra Ledger Report",filters=[["posting_date",'between', [_data.get('from_date'),_data.get('to_date')]],{"geo_mitra":geo_mitra_id, "dealer":_data.get('dealer')}], fields=["*"])
        home_data = frappe.db.get_list("Geo Mitra Ledger Report", filters={"geo_mitra":geo_mitra_id, "dealer":_data.get('dealer')}, fields=["*"])

        for hd in home_data:
            hd.images=[]
            images = get_doctype_images("Geo Mitra Ledger Report", hd.name,1)
            for img in images:
                hd.images.append(img.get('image'))
            
        #     if hd.amount:
        #         hd.amount = float(hd.get('amount'))
            # if himage :
            #     hd.image = himage

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
                
        try:
            doc = frappe.get_doc({
            "doctype":"Geo Mitra Ledger Report",
            "posting_date": frappe.utils.nowdate(),
            "notes": _data.get('notes') if _data.get('notes') else '' ,
            "geo_mitra":geo_mitra_id,
            "workflow_state":'Pending',
            "dealer" : _data.get('dealer') if _data.get('dealer') else '',
            "from_date" : add_to_date(_data.get('from_date'), days=0, as_string=True, as_datetime=True)if _data.get('from_date') else '',
            "to_date" : add_to_date(_data.get('to_date'), days=0, as_string=True, as_datetime=True) if _data.get('to_date') else ''
            # "employee_location": _data['mylocation'],
            # "longitude": _data.get('longitude') if _data.get('longitude') else '',
            # "latitude": _data.get('latitude') if _data.get('latitude') else ''

            })
            doc.insert()        
            if _data['image']:
                for img in _data['image']:
                    data = img
                    filename = doc.name
                    docname = doc.name
                    doctype = "Geo Mitra Ledger Report"
                    image = ng_write_file(data, filename, docname, doctype, 'private')
            doc.save()
            frappe.db.commit()
            dealer=frappe.get_doc("Dealer", _data.get('dealer'))
            geo_mitra_doc=frappe.get_doc("Geo Mitra", geo_mitra_id)

            payload={
            "posting_date": frappe.utils.nowdate(),
            "crop_doc_name":doc.name,
            "notes": _data.get('notes') if _data.get('notes') else '' ,
            "geo_mitra":geo_mitra_id,
            'sales_person':geo_mitra_doc.get('sales_person_name') if geo_mitra_doc.get('sales_person_name') else '' ,
            "dealer" : _data.get('dealer') if _data.get('dealer') else '',
            "customer" : dealer.get('dealer_code') if dealer.get('dealer_code') else '',
            "from_date" : add_to_date(_data.get('from_date'), days=0, as_string=True, as_datetime=True)if _data.get('from_date') else '',
            "to_date" : add_to_date(_data.get('to_date'), days=0, as_string=True, as_datetime=True) if _data.get('to_date') else ''
            }

           
            response11 = requests.request("POST", f"{url}/api/resource/Geo%20Mitra%20Ledger%20Report", data=json.dumps(payload), headers=headers)
            result = json.loads(response11.text)
            # frappe.log_error("api responsedd1", result)

            if(result):
                frappe.log_error("api response11", result['data']['name'])
                if _data['image']:

                    for img in _data['image']:
                        payload2={
                            "data":img,
                            "docname":result['data']['name'] if result['data'] else 'f6391f1cee',
                            "filename":f"{result['data']['name']}{str(random.randint(1000,9999))}"

                        }
                        response1 = requests.request("POST", f"{url}/api/method/erpnext.geolife_api.gm_write_file", data=json.dumps(payload2), headers=headers)
                
                        frappe.log_error("geolife api response image",response1.text)

                frappe.response["message"] = {
                    "status":True,
                    "message": "Report Added Successfully",
                }
                return
            
        except Exception as e:
            frappe.log_error('ledger Report Create',str(e))
            frappe.response["message"] = {
                "status":False,
                "message": "Ledger Report Not Created",
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
                
        doc = frappe.get_doc("Geo Mitra Ledger Report", _data.get('name'))
        doc.notes = _data.get('notes') if _data.get('notes') else ''
        # doc.end_longitude =_data.get('longitude') if _data.get('longitude') else ''
        # doc.end_latitude = _data.get('latitude') if _data.get('latitude') else ''

        if _data['image']:
                for img in _data['image']:
                    data = img
                    filename = doc.name
                    docname = doc.name
                    doctype = "Geo Mitra Ledger Report"
                    image = ng_write_file(data, filename, docname, doctype, 'private')        
        doc.save()
        frappe.db.commit()

        if _data['image']:
            for img in _data['image']:
                payload2={
                    "data":img,
                    "docname":doc.name,
                    "filename":f"{doc.name}{str(random.randint(1000,9999))}"
                }
                response1 = requests.request("POST", f"{url}/api/method/erpnext.geolife_api.gm_write_file", data=json.dumps(payload2), headers=headers)
                frappe.log_error("Geolife api update image",response1.text)

        frappe.response["message"] = {
            "status":True,
            "message": "Ledger Report Updated Successfully",
        }
        return


@frappe.whitelist(allow_guest=True)
def dayplan_list():
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
        home_data = frappe.db.get_list("Day Plan",filters={"geo_mitra":geo_mitra_id}, fields=["*"],limit='30')
        # for hd in home_data:
        #     if hd.amount:
        #         hd.amount = int(hd.get('amount'))
            # if himage :
            #     hd.image = himage

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
        exits_doc = frappe.db.exists("Day Plan", {"geo_mitra":geo_mitra_id,"posting_date": frappe.utils.nowdate()})
        if exits_doc :
            frappe.response["message"] = {
                "status": False,
                "message": "Already Day Plan Created",
                "user_email": user_email
            }
            return
        
        doc = frappe.get_doc({
            "doctype":"Day Plan",
            "posting_date": frappe.utils.nowdate(),
            "number_of_dealer_appointment": _data['num_dealer'],
            "collections" : _data.get('collections_n_lakhs') if _data.get('collections_n_lakhs') else 0,
            "sales": _data.get('sales_in_lakhs') if _data.get('sales_in_lakhs') else 0 ,
            "geo_mitra":geo_mitra_id,
            "my_location": _data['mylocation'],
            "longitude": _data.get('longitude') if _data.get('longitude') else '',
            "latitude": _data.get('latitude') if _data.get('latitude') else ''

        })
        doc.insert()        
        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
            "status":True,
            "message": "Dayplan Added Successfully",
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
        try:
            
            if  _data['first_name']: 
                doc = frappe.get_doc({
                "doctype":"My Farmer",
                "register_date": frappe.utils.nowdate(),
                "first_name": _data['first_name'],
                "last_name": _data['last_name'],
                "mobile_number": _data['mobile_no'],
                "pincode": _data['pincode'],
                "geo_city": _data['village'],
                "village": _data['village'],
                "geomitra_number": geo_mitra_id,
                "farm_acre": _data['acre'],

                "crop": _data['crop'],
                "market": _data['market'],
                "date_of_sowing": _data['data_of_sowing'],
                "address_data": _data['address_data'],
                
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

        except Exception as e:
            # frappe.log_error('farmer Meeting',str(e))
            frappe.response["message"] = {
                "status":False,
                "message": e,
            }
            return

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
            "transaction_id":_data['transaction_id'],
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
       
        farmer = frappe.get_doc("My Farmer",doc.farmer)
        if farmer :
            doc.farmer_msg = send_whatsapp(doc.farmer, "order_advance_received_farmer",[f"{farmer.first_name} {farmer.last_name}", doc.name])
        dealer = frappe.get_doc("Dealer",doc.dealer)
        if dealer :
            doc.dealer_msg = send_whatsapp(doc.dealer, 'order_advance_received_dealer',[dealer.dealer_name,doc.name])

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
                LIMIT 100
            """, (text, text, text), as_dict=1)
        else :
            if _data.get('village'):
                geomitras = frappe.db.sql("""
                    SELECT 
                        *
                    FROM
                        `tabMy Farmer`
                    WHERE (first_name like %s OR last_name like %s OR mobile_number like %s) AND geomitra_number = %s AND village=%s
                    """, (text, text, text, geo_mitra_id,_data.get('village') ), as_dict=1)
            else:
                geomitras = frappe.db.sql("""
                    SELECT 
                        *
                    FROM
                        `tabMy Farmer`
                    WHERE (first_name like %s OR last_name like %s OR mobile_number like %s) AND geomitra_number = %s
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
            doc.farmer_msg = send_whatsapp(doc.farmer, "order_confirmed_farmer",[f"{farmer.first_name} {farmer.last_name}",doc.name])
        geoMitra = frappe.get_doc("Geo Mitra",doc.geo_mitra)
        if geoMitra :
            doc.geo_mitra_msg = send_whatsapp(doc.geo_mitra,"order_confirmed_staff",[f"{geoMitra.get('first_name')} {geoMitra.get('last_name')}", doc.name])
        
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
        search_able_geo_mitra =  _data.get("child_geo_mitra") if _data.get("child_geo_mitra") else geo_mitra_id


        

        # mdealers = frappe.db.sql("""
        #     SELECT 
        #         dm.parent, dm.name
        #     FROM
        #         `tabDealer Geo Mitra` dm
        #     LEFT JOIN `tabDealer` d ON d.name=dm.parent
        #     WHERE (d.dealer_name like %s OR d.contact_person like %s OR d.mobile_number like %s) AND dm.geo_mitra = %s
        #     LIMIT 500
        # """, (text, text, text,geo_mitra_id), as_dict=1)

        dealers=[]
        # for md in mdealers :
        #     dealers.append(frappe.get_doc("Dealer",md.parent))

        lft = frappe.db.get_value("Geo Mitra", search_able_geo_mitra, "lft")
        rgt = frappe.db.get_value("Geo Mitra", search_able_geo_mitra, "rgt")       

        result = frappe.db.sql("""
                SELECT
                    dgm.parent as dealer,
                    dgm.geo_mitra,
                    d.dealer_name,d.qr_code, d.mobile_number,
                    gm.sales_person_name, gm.parent_geo_mitra as parent,
                    gm.name as id
                    
                FROM
                    `tabDealer Geo Mitra` dgm
                LEFT JOIN `tabDealer` d ON d.name = dgm.parent
                LEFT JOIN `tabGeo Mitra` gm ON gm.name = dgm.geo_mitra
                WHERE
                (d.dealer_name like %s OR d.contact_person like %s OR d.mobile_number like %s) AND
                gm.lft >= %s AND gm.rgt <= %s
                Group By d.dealer_name
            """, (text, text, text, lft, rgt), as_dict=1)    

        
        # dealers = frappe.db.get_list("Dealer", filters= [['DGO List', 'geo_mitra', 'in', geo_mitra_id]], fields=["*"])
        for m in result :
            check_activity= frappe.db.get_all('Daily Activity',filters=[['dealer','=',m.dealer],['posting_date', 'between', [datetime.today().replace(day=1),datetime.now().strftime('%Y-%m-%d')]]], fields=["count(name) as count","name", "posting_date","geo_mitra","geo_mitra_name"], order_by='creation desc',)
            # frappe.log_error('dealer',str(m))
            # frappe.log_error('dealer data',str(check_activity))

            if check_activity:
                if check_activity[0].name:
                    # frappe.log_error('farmer Meeting',str(check_activity))
                    # frappe.log_error('dealer count',str(len(check_activity)))

                    activity = frappe.get_doc('Daily Activity',check_activity[0].name)
                    # frappe.log_error('Activitys',activity.multi_activity_types[0].activity_type)

                    check_activity[0].last_visit=activity.multi_activity_types[0].activity_type
                    check_activity[0].count= len(check_activity)

                m.activity = check_activity
            

            if m.qr_code:
                m.qr_code = frappe.utils.get_url(m.qr_code)
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : result,
            "geo_mitra_id": geo_mitra_id
        }
        return

@frappe.whitelist(allow_guest=True)
def search_retailer():

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

        retailers = frappe.db.sql("""
            SELECT 
                name, mobile_no, retailer_name
            FROM
                `tabRetailer`
            WHERE (retailer_name like %s OR mobile_no like %s OR name like %s) AND dm.geo_mitra = %s
        """, (text, text, text,geo_mitra_id), as_dict=1)
                
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : retailers,
            "geo_mitra_id": geo_mitra_id
        }
        return




@frappe.whitelist(allow_guest=True)
def search_other():

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

        retailers = frappe.db.sql("""
            SELECT 
                name, mobile_no, persone_name
            FROM
                `tabGeo Other`
            WHERE (persone_name like %s OR mobile_no like %s OR name like %s) AND dm.geo_mitra = %s
        """, (text, text, text,geo_mitra_id), as_dict=1)
                
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : retailers,
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
def get_villages():

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
        geo_mitra_id = get_geomitra_from_userid(user_email)
        villages=[]

        # geomitra = frappe.get_doc("Geo Mitra",geo_mitra_id )
        # if geomitra.get('geo_market'):
            # villages = [d.name for d in frappe.db.get_all("Geo Market Details",filters={'parent':geomitra.get('geo_market')}, fields=["*"])]
        villages = [d.village for d in frappe.db.get_all("My Farmer",filters={'geomitra_number':geo_mitra_id }, fields=["*"], group_by='village')]

        
        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : villages,
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
def getfarmer_meeting():

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
       
        geo_mitra_id = get_geomitra_from_userid(user_email)

        meetings = frappe.db.get_all("Farmer Meeting",filters={'geo_mitra':geo_mitra_id}, fields=["*"],order_by='posting_date DESC', limit='30' )
        for itm in meetings:
            farmer_attendance = frappe.db.get_all("Crop Seminar Attendance",filters={"parenttype":"Farmer Meeting","parent":itm.name}, fields=["farmer"])
            if farmer_attendance :
                itm.farmer_attendance=farmer_attendance
            else :
                itm.farmer_attendance=[]

        frappe.response["message"] = {
            "status":True,
            "message": "",
            "data" : meetings,
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


        try:
            doc = frappe.get_doc({
            "doctype":"Farmer Meeting",
            "posting_date": frappe.utils.nowdate(),
            "employee_location": _data['mylocation'],
            "agenda":_data['agenda'],
            "location":_data['location'],
            "no_attendees":_data['no_attendees'],
            "notes": _data['notes'],

            "dealer_image_name": _data.get('dealer_image_name') if _data.get('dealer_image_name') else '' ,
            "so_name": _data.get('so_name') if _data.get('so_name') else '',
            "dealer": _data.get('dealer') if _data.get('dealer') else '',
            "market": _data.get('market') if _data.get('market') else '',

            "geo_mitra":geo_mitra_id,
            
            })
            doc.insert()
            if _data.get('farmer_image'):
                for img in _data['farmer_image']:
                    data = img
                    filename = doc.name
                    docname = doc.name
                    doctype = "Farmer Meeting"
                    image = ng_write_file(data, filename, docname, doctype, 'private')
                    doc.append("farmers_image",{'image':image})

            if _data.get('farmer_list_image'):
                data = _data['farmer_list_image'][0]
                filename = doc.name
                docname = doc.name
                doctype = "Farmer Meeting"
                image = ng_write_file(data, filename, docname, doctype, 'private')
                doc.farmer_list_image = image

            if _data.get('so_image'):
                data = _data['so_image'][0]
                filename = doc.name
                docname = doc.name
                doctype = "Farmer Meeting"
                image = ng_write_file(data, filename, docname, doctype, 'private')
                doc.so_image = image

            if _data.get('dealer_image'):
                data = _data['dealer_image'][0]
                filename = doc.name
                docname = doc.name
                doctype = "Farmer Meeting"
                image = ng_write_file(data, filename, docname, doctype, 'private')
                doc.dealer_image = image

            if _data.get('image'):
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
                "message": "Successfully Submited",
                "geo_mitra_id": geo_mitra_id
            }
            return
        
        except Exception as e:
            # frappe.log_error('farmer Meeting',str(e))
            frappe.response["message"] = {
                "status":False,
                "message": e,
            }
            return
    elif frappe.request.method == "PUT":
        _data = frappe.request.json
        doc = frappe.get_doc('Farmer Meeting', _data['name'])

        if _data.get('is_attendance'):
            doc.farmer_attendance=[]
            # for frm_att in doc.farmer_attendance:
            #     if frm_att.farmer in _data['farmer_attendance']:
            #         doc.farmer_attendance.pop(frm_att)
                    
            if doc.farmer_attendance==[]:
                for itm in _data['farmer_attendance'] :
                    doc.append("farmer_attendance",{"farmer":itm,"posting_date": frappe.utils.nowdate()})
            
            if doc.farmer_attendance==[]:
                for itm in _data['farmer_attendance'] :
                    doc.append("farmer_attendance",{"farmer":itm,"posting_date": frappe.utils.nowdate()})
            
            # for frm_att in doc.farmer_attendance:
            #     if frm_att.farmer not in _data['farmer_attendance']:
            #         doc.farmer_attendance.pop(frm_att)

            if _data.get('is_attendance_image') :
                for img in _data['images'] :
                    image_url = ng_write_file(img, _data.get('name'), _data.get('name'), 'Farmer Meeting', 'private')
                    doc.append("farmers_image", { "image": frappe.utils.get_url(image_url),"posting_date": frappe.utils.nowdate()})

        doc.save()
        frappe.db.commit()

        frappe.response["message"] = {
                "status":True,
                "message": "Successfully Updated",
                # "geo_mitra_id": geo_mitra_id
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
        home_data = frappe.db.get_list("Daily Activity", filters=[["Activity Type Multiselect","activity_type","in",["End Day"]],["Daily Activity","geo_mitra","=",geo_mitra],["Daily Activity","posting_date","Between",[datetime.today().replace(day=1),datetime.now().strftime('%Y-%m-%d')]]], 
                                       fields=["name","activity_type","activity_name","session_started","session_enddate"])
        for h in home_data:
            if h.session_enddate is not None:
                start_time_str = h.session_started.strftime("%Y-%m-%d %H:%M:%S")
                start_time = datetime.strptime(start_time_str, "%Y-%m-%d %H:%M:%S")
                end_time_str = h.session_enddate.strftime("%Y-%m-%d %H:%M:%S")
                end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
                time_difference = end_time - start_time
                if time_difference :
                    value = time_difference.total_seconds() / 3600
                    if value > 8 :
                        count_days = count_days+1
                        h.value = count_days

        input_dt = datetime(2022, 9, 13)
        res = calendar.monthrange(input_dt.year, input_dt.month)
        last_day = res[1]
        Dashboard["present_days"] = f"{count_days}/{last_day}"

        Dashboard["kit_booking"] = frappe.db.count("Geo Advance Booking", {"geo_mitra":geo_mitra})
        Dashboard["incentive"] = frappe.db.count("Geo Mitra Incentive", {"geo_mitra":geo_mitra})
        Dealers_count=0
        # Dealers = frappe.db.get_all("Dealer Geo Mitra",filters={"geo_mitra":geo_mitra}, fields=["parent"])
        # for dealer in Dealers :
        #     ddealer = frappe.get_doc("Dealer",dealer.parent)
        #     if ddealer.dgo_list:
        #         for d in ddealer.dgo_list :
        #             if d.geo_mitra == geo_mitra :
        #                 Dealers_count = Dealers_count+1

        lft = frappe.db.get_value("Geo Mitra", geo_mitra, "lft")
        rgt = frappe.db.get_value("Geo Mitra", geo_mitra, "rgt") 
        result = frappe.db.sql("""
                SELECT
                    dgm.parent as dealer,
                    dgm.geo_mitra,
                    d.dealer_name,d.qr_code, d.mobile_number,
                    gm.sales_person_name, gm.parent_geo_mitra as parent,
                    gm.name as id       
                FROM
                    `tabDealer Geo Mitra` dgm
                LEFT JOIN `tabDealer` d ON d.name = dgm.parent
                LEFT JOIN `tabGeo Mitra` gm ON gm.name = dgm.geo_mitra
                WHERE
                gm.lft >= %s AND gm.rgt <= %s
                Group By d.dealer_name
            """, (lft, rgt), as_dict=1) 

        # frappe.log_error("Dash board", result)
        if result:
            Dealers_count=len(result)


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

        inc = frappe.db.get_list("Geo Mitra Incentive", filters={"geo_mitra":geo_mitra}, fields=["name","incentive"])
        incentive =0
        if inc :
            for i in inc :
                incentive =incentive+i.get('incentive')


        Dashboard["incentive"] = incentive
      
        return Dashboard
