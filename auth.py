import os
import json
import string
import csv
import traceback
import auth_apilib as apilib

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
db_obj = config_obj[config_obj["server"]]["dbinfo"]


@app.route('/auth/userid/', methods=['GET', 'POST'])
def auth_userid():
   
    res_obj = {}
    try:
        res_obj = apilib.auth_userid(db_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("auth_userid", traceback.format_exc(), path_obj)
    return jsonify(res_obj)


@app.route('/auth/logging/', methods=['GET', 'POST'])
def auth_logging():

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
            res_obj = apilib.auth_logging(query_obj, db_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("auth_logging", traceback.format_exc(), path_obj)


    return jsonify(res_obj)


@app.route('/auth/contact/', methods=['GET', 'POST'])
def auth_contact():

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
            res_obj = apilib.auth_contact(query_obj, config_obj)
    except Exception, e:
        res_obj = apilib.get_error_obj("auth_contact", traceback.format_exc(), path_obj)

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
