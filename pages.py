import os
import json
import string
import csv
import traceback
import pages_apilib as apilib
import errorlib

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]


@app.route('/pages/home_init/', methods=['GET', 'POST'])
def home_init():
   
    res_obj = {}
    try:
        res_obj = apilib.home_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("home_init", traceback.format_exc(), path_obj)
   

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




