import os
import json
import string
import csv
import traceback
import glycan_apilib as apilib
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


@app.route('/glycan/search_init/', methods=['GET', 'POST'])
def glycan_search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.glycan_search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_search_init", traceback.format_exc(), path_obj)
    
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/glycan/search_simple/', methods=['GET', 'POST'])
def glycan_search_simple():

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
            res_obj = apilib.glycan_search_simple(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_search_simple", traceback.format_exc(), path_obj)



    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/glycan/search/', methods=['GET', 'POST'])
def glycan_search():

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
            res_obj = apilib.glycan_search(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_search", traceback.format_exc(), path_obj)


    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/glycan/list/', methods=['GET', 'POST'])
def glycan_list():
   
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
            res_obj = util.get_cached_records_indirect(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/glycan/detail/<glytoucan_ac>/', methods=['GET', 'POST'])
def glycan_detail(glytoucan_ac):

    res_obj = {}
    try:
        if glytoucan_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"glytoucan_ac"}]}
        else:
            query_obj = {"glytoucan_ac":glytoucan_ac}
            util.trim_object(query_obj)
            res_obj = apilib.glycan_detail(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_detail", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/glycan/image/<glytoucan_ac>/', methods=['GET', 'POST'])
def glycan_image(glytoucan_ac):

    res_obj = {}
    try:
        if glytoucan_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"glytoucan_ac"}]}
        else:
            query_obj = {"glytoucan_ac":glytoucan_ac}
            img_file = apilib.glycan_image(query_obj, config_obj)
            return send_file(img_file, mimetype='image/png')
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_image", traceback.format_exc(), path_obj)


    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code









