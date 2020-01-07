import os
import json
import string
import csv
import traceback
import protein_apilib as apilib
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


@app.route('/protein/search_init/', methods=['GET', 'POST'])
def protein_search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.protein_search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_search_init", traceback.format_exc(), path_obj)
   
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/protein/search_simple/', methods=['GET', 'POST'])
def protein_search_simple():

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
            res_obj = apilib.protein_search_simple(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_search_simple", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





@app.route('/protein/search/', methods=['GET', 'POST'])
def protein_search():

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
            res_obj = apilib.protein_search(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_search", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/protein/list/', methods=['GET', 'POST'])
def protein_list():
   
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
            res_obj = apilib.protein_list(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/protein/detail/<uniprot_canonical_ac>/', methods=['GET', 'POST'])
def protein_detail(uniprot_canonical_ac):

    res_obj = {}
    try:
        if uniprot_canonical_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"uniprot_canonical_ac"}]}
        else:
            query_obj = {"uniprot_canonical_ac":uniprot_canonical_ac}
            util.trim_object(query_obj)
            res_obj = apilib.protein_detail(query_obj, config_obj)    
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_detail", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/protein/alignment/', methods=['GET', 'POST'])
def protein_alignment():

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
            res_obj = apilib.protein_alignment(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_alignment", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




