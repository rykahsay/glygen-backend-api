import os
import json
import string
import csv
import traceback
import supersearch_apilib as apilib
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
supersearch_config_obj = json.loads(open("./conf/supersearch.json", "r").read())
config_obj["ignored_path_list"] = supersearch_config_obj["ignored_path_list"]
config_obj["path_map"] = supersearch_config_obj["path_map"]
config_obj["ignored_edges"] = json.loads(open("./conf/edgerules.json", "r").read())

@app.route('/supersearch/search_init/', methods=['GET', 'POST'])
def search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("supersearch_search_init", traceback.format_exc(), path_obj)
    
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




@app.route('/supersearch/search/', methods=['GET', 'POST'])
def supersearch_search():
   
    res_obj = {}
    try:
	query_value = util.get_arg_value("query", request.method)
        if query_value == "": 
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            res_obj = apilib.supersearch_search(query_obj, config_obj, False, False)
    except Exception, e:
        res_obj = errorlib.get_error_obj("supersearch_search", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/supersearch/reason/', methods=['GET', 'POST'])
def supersearch_reason():

    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            res_obj = apilib.supersearch_search(query_obj, config_obj, True, False)
    except Exception, e:
        res_obj = errorlib.get_error_obj("supersearch_search", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




@app.route('/supersearch/list/', methods=['GET', 'POST'])
def supersearch_list():
   
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
        res_obj = errorlib.get_error_obj("supersearch_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




