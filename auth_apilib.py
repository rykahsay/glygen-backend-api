import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import bcrypt
import base64
import pytz
from collections import OrderedDict
from bson.objectid import ObjectId



import smtplib
from email.mime.text import MIMEText
import errorlib
import util


def make_hash_string():
    m = hashlib.md5()
    m.update(str(time.time()))
    m.update(str(os.urandom(64)))

    s = string.replace(base64.encodestring(m.digest())[:-3], '/', '$')
    s = s.replace("+", "$")
    return s


def auth_tokenstatus(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    doc = dbh["c_session"].find_one({"token":query_obj["token"]})
    if doc == None:
        return {"error_list":[{"error_code":"no-token-found"}]}
    duration = datetime.datetime.now() - doc["createdts"]
    hours = divmod(duration.total_seconds(), 3600)[0]
    if hours > config_obj["session_life"] :
        return {"error_list":[{"error_code":"expired-token"}]}
    doc.pop("_id")
    res_obj = doc
    res_obj["status"] = 1
    res_obj["duration"] = divmod(duration.total_seconds(), 3600)[0]
    doc["createdts"] = doc["createdts"].strftime('%Y-%m-%d %H:%M:%S %Z%z')

    return res_obj




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


    sender = config_obj[config_obj["server"]]["contactemailreceivers"][0]
    receivers = [query_obj["email"]] + config_obj[config_obj["server"]]["contactemailreceivers"]
    query_obj["page"] = query_obj["page"] if "page" in query_obj else ""


    msg_text = "\n\n%s,\n"  % (query_obj["fname"])
    msg_text += "We have received your message and will make every effort "
    msg_text += "to respond to you within a reasonable amount of time.\n\n"
    param_dict = {
        "fname":"First Name", "lname":"Last Name", "email":"Email", "subject":"Subject", 
        "page":"Page", "message":"Message"
    }
    param_list = ["fname", "lname", "email", "subject", "page", "message"]
    for param in param_list:
        if param in query_obj:
            if query_obj[param].strip() != "":
                msg_text += "%s: %s\n" % (param_dict[param], query_obj[param].strip())
    

    page_url = query_obj["page"] if "page" in query_obj else ""

    res_json = {
        "type":"alert-success",
        "message":msg_text
    }

    msg = MIMEText(msg_text)
    msg['Subject'] = query_obj["subject"]
    msg['From'] = sender
    msg['To'] = receivers[0]
    store_json = {
        "fname":query_obj["fname"],
        "lname":query_obj["lname"],
        "email":sender,
        "subject":query_obj["subject"], 
        "message":query_obj["message"], 
        "page":page_url,
        "agent":"",
        "comment":"",
        "creation_time":"",
        "update_time":"",
        "status":"new",
        "visibility":"visible"
    }
   
    
    try:
        s = smtplib.SMTP('localhost')
        s.sendmail(sender, receivers, msg.as_string())
        s.quit()
        store_json["message_status"] = "success"
    except:
        res_json = {
            "type":"alert-danger",
            "message":"Oops! Something's wrong. Please try again later."
        }
        store_json["message_status"] = "failed"

    store_json["creation_time"] = datetime.datetime.now()
    store_json["update_time"] = store_json["creation_time"] 
    result = dbh[collection].insert_one(store_json)

    
    return res_json





def auth_register(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_register",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_users"

    query_obj["email"] = query_obj["email"].lower()
    query_obj["password"] = bcrypt.hashpw(query_obj["password"].encode('utf-8'), bcrypt.gensalt())
    query_obj["status"] = 0
    query_obj["access"] = "readonly"
    query_obj["role"] = ""

    res_obj = {}
    if dbh[collection].find({"email":query_obj["email"]}).count() != 0:
        res_obj =  {"error_list":[{"error_code":"email-already-regisgered"}]}
    else:
        res = dbh[collection].insert_one(query_obj)
        res_obj = {"type":"success"}

    return res_obj



    
def auth_userinfo(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_userinfo",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
   
    res_obj = auth_tokenstatus({"token":query_obj["token"]}, config_obj)
    
    user_info = dbh["c_users"].find_one({'email' : res_obj["email"].lower()})
    if "access" not in user_info:
        return {"error_list":[{"error_code":"no-write-access"}]}
    if user_info["access"] != "write":
        return {"error_list":[{"error_code":"no-write-access"}]}

    res_obj = dbh["c_users"].find_one({'email' : query_obj["email"].lower()})
    res_obj.pop("_id")
    res_obj.pop("password")

    return res_obj



def auth_login(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_login",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    collection = "c_users"

    query_obj["email"] = query_obj["email"].lower()
    login_user = dbh[collection].find_one({'email' : query_obj["email"]})
    res_obj = {}
    if login_user:
        stored_password = login_user['password'].encode('utf-8')
        submitted_password = query_obj['password'].encode('utf-8')
        if login_user["status"] == 0:
            res_obj =  {"error_list":[{"error_code":"inactive-account"}]}
        elif bcrypt.hashpw(submitted_password, stored_password) == stored_password:
            token = make_hash_string() + make_hash_string()
            ts = datetime.datetime.now()
            session_obj = {"email":query_obj["email"], "token":token, "createdts":ts}
            res = dbh["c_session"].insert_one(session_obj)
            res_obj = {"type":"success", "token":token}
        else:
            res_obj =  {"error_list":[{"error_code":"invalid-email/password-combination"}]}
    else:
        res_obj =  {"error_list":[{"error_code":"invalid-email/password-combination"}]}

    return res_obj



def auth_contactlist(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_contactlist",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    res_obj = auth_tokenstatus({"token":query_obj["token"]}, config_obj)
    if "error_list" in res_obj:
        return res_obj
    if "status" not in res_obj:
        return {"error_list":[{"error_code":"invalid-token"}]}
    if res_obj["status"] != 1:
        return {"error_list":[{"error_code":"invalid-token"}]}
    import pymongo
    doc_list = []
    try:
        q_obj = {} if query_obj["visibility"] == "all" else {"visibility":query_obj["visibility"]}
        doc_list = dbh["c_message"].find(q_obj).sort('creation_time', pymongo.DESCENDING)
    except Exception as e:
        return {"error_list":[{"error_code":str(e)}]}

    out_obj = []
    for doc in doc_list:
        doc["id"] = str(doc["_id"])
        doc.pop("_id")
        for k in ["creation_time", "update_time", "ts"]:
            if k not in doc:
                continue
            doc[k] = doc[k].strftime('%Y-%m-%d %H:%M:%S %Z%z')
        out_obj.append(doc)


    return out_obj


def auth_userupdate(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb


    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_userupdate",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    res_obj = auth_tokenstatus({"token":query_obj["token"]}, config_obj)
    if "error_list" in res_obj:
        return res_obj
    if "status" not in res_obj:
        return {"error_list":[{"error_code":"invalid-token"}]}
    if res_obj["status"] != 1:
        return {"error_list":[{"error_code":"invalid-token"}]}



    try: 
        user_info = dbh["c_users"].find_one({'email' : res_obj["email"].lower()})
        q_obj = {"email":query_obj["email"]}
        update_obj = {}
        if "access" not in query_obj and "role" not in query_obj and "password" in query_obj and res_obj["email"].lower() == query_obj["email"]:
            update_obj["password"] = bcrypt.hashpw(query_obj["password"].encode('utf-8'),bcrypt.gensalt())
        else:
            if "role" not in user_info:
                return {"error_list":[{"error_code":"no-admin-role"}]}
            if user_info["role"] != "admin":
                return {"error_list":[{"error_code":"no-admin-role"}]}
            for k in query_obj:
                if k == "password":
                    update_obj[k] = bcrypt.hashpw(query_obj[k].encode('utf-8'), bcrypt.gensalt())
                elif k not in ["token", "email"]:
                    update_obj[k] = query_obj[k]
        res = dbh["c_users"].update_one(q_obj, {'$set':update_obj}, upsert=True)
        return {"type":"success"}
    except Exception as e:
        return {"error_list":[{"error_code":str(e)}]}





def auth_contactupdate(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb


    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_contactupdate",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    res_obj = auth_tokenstatus({"token":query_obj["token"]}, config_obj)
    if "error_list" in res_obj:
        return res_obj
    if "status" not in res_obj:
        return {"error_list":[{"error_code":"invalid-token"}]}
    if res_obj["status"] != 1:
        return {"error_list":[{"error_code":"invalid-token"}]}

    try: 
        user_info = dbh["c_users"].find_one({'email' : res_obj["email"].lower()})
        if "access" not in user_info:
            return {"error_list":[{"error_code":"no-write-access"}]}
        if user_info["access"] != "write":
            return {"error_list":[{"error_code":"no-write-access"}]}
        
        q_obj = {"_id":ObjectId(query_obj["id"])}
        update_obj = {}
        for k in query_obj:
            if k not in ["id", "token"]:
                update_obj[k] = query_obj[k]
        res = dbh["c_message"].update_one(q_obj, {'$set':update_obj}, upsert=True)
        return {"type":"success"}
    except Exception as e:
        return {"error_list":[{"error_code":str(e)}]}




def auth_contactdelete(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb

    #Collect errors 
    error_list = errorlib.get_errors_in_query("auth_contactdelete",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    res_obj = auth_tokenstatus({"token":query_obj["token"]}, config_obj)
    if "error_list" in res_obj:
        return res_obj
    if "status" not in res_obj:
        return {"error_list":[{"error_code":"invalid-token"}]}
    if res_obj["status"] != 1:
        return {"error_list":[{"error_code":"invalid-token"}]}


    try: 
        q_obj = {"_id":ObjectId(query_obj["id"])}
        doc = dbh["c_message"].find_one(q_obj)
        if doc == None:
            return {"error_list":[{"error_code":"message-not-found"}]}
    except Exception as e:
        return {"error_list":[{"error_code":str(e)}]}

    try:
        user_info = dbh["c_users"].find_one({'email' : res_obj["email"].lower()})
        if "access" not in user_info:
            return {"error_list":[{"error_code":"no-write-access"}]}
        if user_info["access"] != "write":
            return {"error_list":[{"error_code":"no-write-access"}]}
        q_obj = {"_id":ObjectId(query_obj["id"])}
        update_obj = {"visibility":"hidden"}
        res = dbh["c_message"].update_one(q_obj, {'$set':update_obj}, upsert=True)
        return {"type":"success"}
    except Exception as e:
        return {"error_list":[{"error_code":str(e)}]}

