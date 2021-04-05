import os
import json
import string
import csv
import traceback
import data_apilib as apilib
import errorlib
import util

from flask import Flask, request, jsonify, Response
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

global config_obj
global path_obj
config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]

@app.route('/data/download/', methods=['GET', 'POST'])
def data_download():

    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "": 
            error_list = [{"error_code":"missing-query-key-in-query-json"}]
            res_obj = {"error_list":error_list}
        elif util.is_valid_json(query_value) == False:
            error_list = [{"error_code":"invalid-query-json"}]
            res_obj = {"error_list":error_list}
        else:
            query_obj = json.loads(query_value)
	    util.trim_object(query_obj)
            res_obj = apilib.data_download(query_obj, config_obj)
            if type(res_obj) is not dict:
                return res_obj
    except Exception, e:
        res_obj = errorlib.get_error_obj("data_download", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code







