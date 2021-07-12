import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict
from bson import json_util, ObjectId
import collections

import errorlib
import util


def search(query_obj, config_obj):
     
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    q_list = []
    for q in query_obj["glytoucan_ac_list"]:
        q_list.append(q)

    format_list = ["iupac", "wurcs","glycam","smiles_isomeric","inchi","glycoct", "byonic"]
    mongo_query = {"glytoucan_ac":{"$in": q_list}}
    coll = "c_glycan"
    prj_obj = {"glytoucan_ac":1}
    for f in format_list:
        prj_obj[f] = 1

    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
            
    res_obj = {
        "cache_info":{
            "query":query_obj
            ,"ts":ts
        }
        ,"results":[]
    }
    for doc in dbh[coll].find(mongo_query,prj_obj):
        obj = {"glytoucan_ac":doc["glytoucan_ac"]}
        for f in format_list:
            obj[f] = doc[f]
        res_obj["results"].append(obj)


    return res_obj

