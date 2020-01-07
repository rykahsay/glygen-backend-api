import os
import json
import string
import csv
import traceback
import auth_apilib as apilib
import errorlib
import util

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]


@app.route('/auth/userid/', methods=['GET', 'POST'])
def auth_userid():
   
    res_obj = {}
    try:
        res_obj = apilib.auth_userid(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("auth_userid", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




@app.route('/auth/contact/', methods=['GET', 'POST'])
def auth_contact():

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
            res_obj = apilib.auth_contact(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("auth_contact", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





