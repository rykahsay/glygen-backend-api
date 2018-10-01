import os
import json
import string
import csv
import traceback
import protein_apilib as apilib

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
db_obj = config_obj[config_obj["server"]]["dbinfo"]


@app.route('/protein/search_init/', methods=['GET', 'POST'])
def protein_search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.protein_search_init(db_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("protein_search_init", traceback.format_exc(), path_obj)
    
    return jsonify(res_obj)





@app.route('/protein/search/', methods=['GET', 'POST'])
def protein_search():

    res_obj = {}
    try:
        query_value = get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_code": "missing-query-key-in-query-json"}
        elif apilib.is_valid_json(query_value) == False:
            res_obj = {"error_code": "invalid-query-json"}
        else:
            query_obj = json.loads(query_value)
            trim_object(query_obj)
            res_obj = apilib.protein_search(query_obj, db_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("protein_search", traceback.format_exc(), path_obj)

    return jsonify(res_obj)


@app.route('/protein/list/', methods=['GET', 'POST'])
def protein_list():
   
    res_obj = {}
    try:
	query_value = get_arg_value("query", request.method)
        if query_value == "": 
            res_obj = {"error_code": "missing-query-key-in-query-json"}
        elif apilib.is_valid_json(query_value) == False:
            res_obj = {"error_code": "invalid-query-json"}
        else:
            query_obj = json.loads(query_value)
            trim_object(query_obj)
            res_obj = apilib.protein_list(query_obj, db_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("protein_list", traceback.format_exc(), path_obj)
    
    return jsonify(res_obj)



@app.route('/protein/detail/<uniprot_canonical_ac>/', methods=['GET', 'POST'])
def protein_detail(uniprot_canonical_ac):

    res_obj = {}
    try:
        if uniprot_canonical_ac in ["", "empty"]:
            res_obj = {"error_code":"missing-parameter"}
        else:
            query_obj = {"uniprot_canonical_ac":uniprot_canonical_ac}
            trim_object(query_obj)
            res_obj = apilib.protein_detail(query_obj, db_obj)    
    except Exception, e:
        res_obj = apilib.get_error_obj("protein_detail", traceback.format_exc(), path_obj)

    return jsonify(res_obj)



def get_arg_value(arg, method):

    if method == "GET":
        if request.args.get(arg):
            return request.args.get(arg)
    elif method == "POST":
        if arg in request.values:
            if request.values[arg]:
                return request.values[arg]
    return ""



def trim_object(obj):
        
    for key in obj:
        if type(obj[key]) is unicode:
            obj[key] = obj[key].strip()
