import os
import json
import string
import csv
import traceback
import directsearch_apilib as apilib
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


@app.route('/directsearch/glycan/', methods=['GET', 'POST'])
def glycan():

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
            res_obj = apilib.glycan(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_search_direct", traceback.format_exc(), path_obj)


    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/directsearch/protein/', methods=['GET', 'POST'])
def protein():

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
            res_obj = apilib.protein(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_search_direct", traceback.format_exc(), path_obj)


    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/directsearch/glycan_to_biosynthesis_enzymes/', methods=['GET', 'POST'])
def glycan_to_biosynthesis_enzymes():
    
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
            res_obj = apilib.glycan_to_biosynthesis_enzymes(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_to_biosynthesis_enzymes_direct", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/glycan_to_glycoproteins/', methods=['GET', 'POST'])
def glycan_to_glycoproteins():

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
            res_obj = apilib.glycan_to_glycoproteins(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("glycan_to_glycoproteins_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/biosynthesis_enzyme_to_glycans/', methods=['GET', 'POST'])
def biosynthesis_enzyme_to_glycans():

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
            res_obj = apilib.biosynthesis_enzyme_to_glycans(query_obj, config_obj)
    except Exception, e:        res_obj = errorlib.get_error_obj("glycan_to_glycoproteins_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/protein_to_homologs/', methods=['GET', 'POST'])
def protein_to_homologs():

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
            res_obj = apilib.protein_to_homologs(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("protein_to_homologs_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/species_to_glycosyltransferases/', methods=['GET', 'POST'])
def species_to_glycosyltransferases():

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
            res_obj = apilib.species_to_glycosyltransferases(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("species_to_glycosyltransferases_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code

@app.route('/directsearch/species_to_glycohydrolases/', methods=['GET', 'POST'])
def species_to_glycohydrolases():

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
            res_obj = apilib.species_to_glycohydrolases(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("species_to_glycohydrolases_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/species_to_glycoproteins/', methods=['GET', 'POST'])
def species_to_glycoproteins():

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
            res_obj = apilib.species_to_glycoproteins(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("species_to_glycoproteins_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/directsearch/disease_to_glycosyltransferases/', methods=['GET', 'POST'])
def disease_to_glycosyltransferases():

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
            res_obj = apilib.disease_to_glycosyltransferases(query_obj, config_obj)
    except Exception, e:        
        res_obj = errorlib.get_error_obj("disease_to_glycosyltransferases_direct", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





