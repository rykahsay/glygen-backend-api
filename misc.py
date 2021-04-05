import os
import json
import string
import csv
import traceback
import misc_apilib as apilib
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


@app.route('/misc/validate/', methods=['GET', 'POST'])
def misc_validate():

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
            res_obj = apilib.validate(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_validate", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/propertylist/', methods=['GET', 'POST'])
def misc_propertylist():

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
            res_obj = apilib.propertylist(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_propertylist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code

@app.route('/misc/pathlist/', methods=['GET', 'POST'])
def misc_pathlist():

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
            res_obj = apilib.pathlist(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_pathlist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





@app.route('/misc/messagelist/', methods=['GET', 'POST'])
def misc_messagelist():

    res_obj = {}
    try:
        res_obj = apilib.messagelist(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_messagelist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/verlist/', methods=['GET', 'POST'])
def misc_verlist():


    res_obj = {}
    try:
        res_obj = apilib.verlist(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_verlist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/gtclist/', methods=['GET', 'POST'])
def misc_gtclist():


    res_obj = {}
    try:
        res_obj = apilib.gtclist(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_gtclist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/bcolist/', methods=['GET', 'POST'])
def misc_bcolist():


    res_obj = {}
    try:
        res_obj = apilib.bcolist(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_bcolist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/testurls/', methods=['GET', 'POST'])
def testurls():


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
            res_obj = apilib.testurls(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_bcolist", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/misc/testrecords/', methods=['GET', 'POST'])
def testrecords():


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
            res_obj = apilib.testrecords(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("misc_testrecords", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


