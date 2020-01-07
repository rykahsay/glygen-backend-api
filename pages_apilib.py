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




def home_init(config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("pages_home_init",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
  
    res_obj = {"version":[], "statistics":[]}
    for doc in dbh["c_version"].find({}):
        doc.pop("_id")
        res_obj["version"].append(doc)
  
    for doc in dbh["c_stat"].find({}):
        doc.pop("_id")
        res_obj["statistics"].append(doc)


    return res_obj 



