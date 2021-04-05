import os
import json
import string
import csv
import traceback
import motif_apilib as apilib
import errorlib
import util

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]





@app.route('/motif/detail/', methods=['GET', 'POST'])
def motif_detail():
   
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
            res_obj = apilib.motif_detail(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("motif_detail", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/motif/list/', methods=['GET', 'POST'])
def motif_list():

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
            res_obj = util.get_cached_motif_records_direct(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("motif_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code







