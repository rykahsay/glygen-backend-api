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



def log_logging(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("log_logging",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_userlog"

    query_obj["ts"] = datetime.datetime.now()

    res_json = {"status":"success"}
    result = dbh[collection].insert_one(query_obj)

    return res_json




def log_init(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("log_init",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    mongo_query = {}
    if "start_date" in query_obj:
        yy, mm, dd = query_obj["start_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["start_date"].split(" ")[1].split(":")
        start_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)

        yy, mm, dd = query_obj["end_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["end_date"].split(" ")[1].split(":")
        end_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)

        mongo_query = {'ts': {'$gte': start_ts, '$lt': end_ts}}


    stat_obj = {"pagestat":{}, "typestat":{}, "userstat":{}}
    for doc in dbh["c_userlog"].find(mongo_query):
        #page_name = doc["page"].split("/")[-1]
        page_name = doc["page"]
        user_name = doc["user"]
        type_name = doc["type"]
        if page_name not in stat_obj["pagestat"]:
            stat_obj["pagestat"][page_name] = {"access":0, "error":0}
        if user_name not in stat_obj["userstat"]:
            stat_obj["userstat"][user_name] = {"access":0, "error":0}
        if type_name not in stat_obj["typestat"]:
            stat_obj["typestat"][type_name] = {"number":0}

        if type_name == "user":
            stat_obj["pagestat"][page_name]["access"] += 1
            stat_obj["userstat"][user_name]["access"] += 1
        elif type_name == "error":
            stat_obj["pagestat"][page_name]["error"] += 1
            stat_obj["userstat"][user_name]["error"] += 1 
        stat_obj["typestat"][type_name]["number"] += 1
                
    


    res_obj = {"pages":[], "types":[], "users":[]}
    for page_name in stat_obj["pagestat"]:
        n_one, n_two = stat_obj["pagestat"][page_name]["access"], stat_obj["pagestat"][page_name]["error"]
        res_obj["pages"].append({"page":page_name, "access":n_one, "error":n_two})

    for user_name in stat_obj["userstat"]:
        n_one, n_two = stat_obj["userstat"][user_name]["access"], stat_obj["userstat"][user_name]["error"]
        res_obj["users"].append({"user":user_name, "access":n_one, "error":n_two})

    for type_name in stat_obj["typestat"]:
        n_one = stat_obj["typestat"][type_name]["number"]
        res_obj["types"].append({"type":type_name, "number":n_one})

    return res_obj 







def log_access(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("log_access",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

 
    mongo_query = {"type":query_obj["type"]}
    for k in ["page", "user"]:
        if k in query_obj:
            mongo_query[k] = query_obj[k]


    if "start_date" in query_obj:
        yy, mm, dd = query_obj["start_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["start_date"].split(" ")[1].split(":")
        start_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)
        yy, mm, dd = query_obj["end_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["end_date"].split(" ")[1].split(":")
        end_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)
        mongo_query["ts"] = {'$gte': start_ts, '$lt': end_ts}




    res_obj = {"logs":[]}
    obj_list = []
    for doc in dbh["c_userlog"].find(mongo_query):
        doc["type"] = doc["type"] if "type" in doc else ""
        doc["id"] = doc["id"] if "id" in doc else ""
        doc["user"] = doc["user"] if "user" in doc else ""
        doc["page"] = doc["page"] if "page" in doc else ""
        doc["message"] = doc["message"] if "message" in doc else ""
        doc["ts"] = doc["ts"] if "ts" in doc else ""
        obj = {"type":doc["type"], "user":doc["user"], "page":doc["page"], 
                "id":doc["id"],"message":doc["message"], "created":doc["ts"]}
        obj_list.append(obj)

    if obj_list == []:
        return res_obj

    query_obj["offset"] = query_obj["offset"] if "offset" in query_obj else 1
    query_obj["limit"] = query_obj["limit"] if "limit" in query_obj else 100
    query_obj["order"] = query_obj["order"] if "order" in query_obj else "asc"


    sorted_id_list = util.sort_objects(obj_list, config_obj["log_access"]["returnfields"],
                                                  "created", query_obj["order"])




    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(obj_list):
        return {"error_list":[{"error_code":"invalid-parameter-value", "field":"offset"}]}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])

    res_obj = {"logs":[]}
    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = obj_list[obj_id]
        res_obj["logs"].append(obj)

    #res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
    #    "total_length":len(obj_list), "sort":query_obj["sort"], "order":query_obj["order"]}

    return res_obj 




def log_grouped(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("log_grouped",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    mongo_query = {"type":query_obj["type"]}
    for k in ["page", "user"]:
        if k in query_obj:
            mongo_query[k] = query_obj[k]


    if "start_date" in query_obj:
        yy, mm, dd = query_obj["start_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["start_date"].split(" ")[1].split(":")
        start_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)
        yy, mm, dd = query_obj["end_date"].split(" ")[0].split("-")
        hr, mn, sc = query_obj["end_date"].split(" ")[1].split(":")
        end_ts = datetime.datetime(int(yy), int(mm), int(dd), int(hr), int(mn), int(sc), 0)
        mongo_query["ts"] = {'$gte': start_ts, '$lt': end_ts}


    count_dict = {}
    for doc in dbh["c_userlog"].find(mongo_query):
        msg = doc["message"] if "message" in doc else ""
        count_dict[msg] = count_dict[msg] + 1 if msg in count_dict else 1

    res_obj = {"logs":[]}
    obj_list = []
    for msg in count_dict:
        obj_list.append({"message":msg, "count":count_dict[msg]})


    if obj_list == []:
        return res_obj

    query_obj["offset"] = query_obj["offset"] if "offset" in query_obj else 1
    query_obj["limit"] = query_obj["limit"] if "limit" in query_obj else 100
    query_obj["order"] = query_obj["order"] if "order" in query_obj else "asc"

    sorted_id_list = util.sort_objects(obj_list, config_obj["log_grouped"]["returnfields"],
                                                  "count", query_obj["order"])

    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(obj_list):
        return {"error_list":[{"error_code":"invalid-parameter-value", "field":"offset"}]}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])

    res_obj = {"logs":[], "recordstotal":len(obj_list)}
    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = obj_list[obj_id]
        res_obj["logs"].append(obj)



    #res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
    #    "total_length":len(obj_list), "sort":query_obj["sort"], "order":query_obj["order"]}

    return res_obj

