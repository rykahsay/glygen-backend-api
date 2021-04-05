import os
import json
import string
import csv
import traceback
import site_apilib as apilib
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



@app.route('/site/search_init/', methods=['GET', 'POST'])
def search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.site_search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("site_search_init", traceback.format_exc(), path_obj)
    
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





@app.route('/site/detail/<site_id>/', methods=['GET', 'POST'])
def site_detail(site_id):

    res_obj = {}
    try:
        if site_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"site_id"}]}
        else:
            query_obj = {"site_id":site_id}
            util.trim_object(query_obj)
            res_obj = apilib.site_detail(query_obj, config_obj)    
    except Exception, e:
        res_obj = errorlib.get_error_obj("site_detail", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code






