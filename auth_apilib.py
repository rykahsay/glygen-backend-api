import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict



import smtplib
from email.mime.text import MIMEText
import errorlib
import util


def auth_userid(config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_userid",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_userid"

    res_obj = {}
    i = 0
    while True:
        user_id = util.get_random_string(32).lower()
        user_obj = {"userid":user_id}
        if dbh[collection].find(user_obj).count() == 0:
            ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
            user_obj["created_ts"] = ts
            result = dbh[collection].insert_one(user_obj)
            return {"user":user_id}
        if i > 100000:
            return {"error_list":[{"error_code":"userid-generator-failed"}]}

        i += 1




def auth_contact(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_contact",query_obj, config_obj)
    if error_list != []: 
        return {"error_list":error_list}

    collection = "c_message"

    res_json = {
        "type":"alert-success",
        "message":"We have received your message, we'll get back to you soon"
    }

    sender = config_obj[config_obj["server"]]["contactemailreceivers"][0]
    receivers = [query_obj["email"]] + config_obj[config_obj["server"]]["contactemailreceivers"]
    query_obj["page"] = query_obj["page"] if "page" in query_obj else ""

    msg_text = "\n\n"
    param_dict = {
        "fname":"First Name", "lname":"Last Name", "email":"Email", "subject":"Subject", 
        "page":"Page", "message":"Message"
    }
    for param in param_dict:
        if param in query_obj:
            if query_obj[param].strip() != "":
                msg_text += "%s: %s\n" % (param_dict[param], query_obj[param].strip())


    msg = MIMEText(msg_text)
    msg['Subject'] = query_obj["subject"]
    msg['From'] = sender
    msg['To'] = receivers[0]
    store_json = {"from":sender, "to":receivers[0], "subject":query_obj["subject"], "message":query_obj["message"]}
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(sender, receivers, msg.as_string())
        s.quit()
        store_json["status"] = "success"
    except:
        res_json = {
            "type":"alert-danger",
            "message":"Oops! Something's wrong. Please try again later."
        }
        store_json["status"] = "failed"

    store_json["ts"] = datetime.datetime.now()
    result = dbh[collection].insert_one(store_json)

    
    return res_json





