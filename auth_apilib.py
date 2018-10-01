import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict


from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

import smtplib
from email.mime.text import MIMEText



def auth_userid(db_obj):

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_userid"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    gmt_time = time.gmtime()
    gmt_time_to_dt = datetime.datetime.fromtimestamp(time.mktime(gmt_time), tz=pytz.timezone('GMT'))
    gmt_plus = str(gmt_time_to_dt + datetime.timedelta(minutes = 120))


    res_obj = {}
    i = 0
    while True:
        user_id = get_random_string(32).lower()
        user_obj = {"userid":user_id}
        if dbh[collection].find(user_obj).count() == 0:
            user_obj["created_ts"] = gmt_plus
            result = dbh[collection].insert_one(user_obj)
            return {"user":user_id}
        if i > 100000:
            return {"error_code":"userid-generator-failed"}
        i += 1


def auth_logging(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_userlog"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
	
    res_json = {"status":"success"}
    field_list_all = ["id", "user", "type", "page", "message"]
    field_list_required = ["user", "type", "page"]

    max_query_value_len = 2500
    for field in query_obj:
        if field not in field_list_all:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    for field in field_list_required:
        if query_obj[field].strip() == "":
            return {"error_code":"invalid-parameter-value"}
    
    result = dbh[collection].insert_one(query_obj)

    return res_json


def auth_contact(query_obj, config_obj):

    res_json = {
        "type":"alert-success",
        "message":"We have received your message, we'll get back to you soon"
    }
    field_list_all = ["fname", "lname", "email", "subject", "message"]
    field_list_required = ["fname", "lname", "email", "subject", "message"]

    max_query_value_len = 2500
    for field in query_obj:
        if field not in field_list_all:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    for field in field_list_required:
        if query_obj[field].strip() == "":
            return {"error_code":"invalid-parameter-value"}
 

    sender = config_obj[config_obj["server"]]["contactemailreceivers"][0]
    receivers = [query_obj["email"]] + config_obj[config_obj["server"]]["contactemailreceivers"][1:]


    msg_text = "\n\nFirst Name: %s\nLast Name: %s\nEmail: %s\n\nSubject: %s\n\nMessage: %s\n\n" % (query_obj["fname"], query_obj["lname"], query_obj["email"], query_obj["subject"], query_obj["message"])


    msg = MIMEText(msg_text)
    msg['Subject'] = query_obj["subject"]
    msg['From'] = sender
    msg['To'] = receivers[0]
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(sender, receivers, msg.as_string())
        s.quit()
    except:
        res_json = {
            "type":"alert-danger",
            "message":"Oops! Something's wrong. Please try again later."
        }

    return res_json


def dump_debug_log(out_string):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return


def get_random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

def get_error_obj(error_code, error_log, path_obj):
        
    error_id = get_random_string(6) 
    log_file = path_obj["apierrorlogpath"] + "/" + error_code + "-" + error_id + ".log"
    with open(log_file, "w") as FW:
        FW.write("%s" % (error_log))
    return {"error_code": "exception-error-" + error_id}


def is_valid_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True


def is_float(input):
      
    try:
        num = float(input)
    except ValueError:
        return False
    return True


                  
def is_int(input):
    try:
        num = int(input)
    except ValueError:
        return False
    return True




