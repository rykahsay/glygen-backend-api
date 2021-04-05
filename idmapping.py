import os
import json
import string
import csv
import traceback
import idmapping_apilib as apilib
import errorlib
import util
import cgi
import datetime
import pytz

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]

@app.route('/idmapping/search_init/', methods=['GET', 'POST'])
def search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("idmapping_search_init", traceback.format_exc(), path_obj)
    
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




@app.route('/idmapping/search/', methods=['GET', 'POST'])
def search():
 

    form_dict = cgi.FieldStorage()
    record_type = form_dict["recordtype"].value
    input_namespace = form_dict["input_namespace"].value
    output_namespace = form_dict["output_namespace"].value
    input_idlist = []
    if "userfile" in form_dict:
        file_buffer = form_dict["userfile"].file.read()
        file_buffer = file_buffer.replace("\r", "\n")
        file_buffer = file_buffer.replace("\n\n", "\n")
        line_list = file_buffer.split("\n")
        for line in line_list:
            if line.strip() != "" and line.strip() not in input_idlist:
                input_idlist.append(line.strip())

    if "input_idlist" in form_dict:
        if form_dict["input_idlist"].value.strip() != "":
            for word in form_dict["input_idlist"].value.split(","):
                if word.strip() not in input_idlist:
                    input_idlist.append(word.strip())

    query_obj = {"input_idlist":input_idlist, "recordtype":record_type, 
        "input_namespace":input_namespace, "output_namespace":output_namespace}


    res_obj = {}
    try:
        res_obj = apilib.search(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("idmapping_search", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/idmapping/list/', methods=['GET', 'POST'])
def idmapping_list():
   
    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "": 
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            res_obj = util.get_cached_records_direct(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("idmapping_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





