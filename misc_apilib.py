import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict

from flask import Flask, request, jsonify, Response, stream_with_context

import zlib
import gzip
import struct           


import smtplib
from email.mime.text import MIMEText
import errorlib
import util

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import IUPAC




def misc_bcolist(config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    
    out_obj = {}
    for doc in dbh["c_bco"].find({}):
        if "bco_id" in doc:
            bco_id = doc["bco_id"]
            if "io_domain" in doc:
                if "output_subdomain" in doc["io_domain"]:
                    if doc["io_domain"]["output_subdomain"] != []:
                        file_name = doc["io_domain"]["output_subdomain"][0]["uri"]["filename"]
                        out_obj[bco_id] = file_name

    return out_obj


