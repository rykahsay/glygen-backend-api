import os
import json
import string
import csv
import traceback
import typeahead_apilib as apilib
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


@app.route('/typeahead/', methods=['GET', 'POST'])
def typeahead():

    res_obj = []
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            field_list_one = ["glytoucan_ac", "motif_name", "enzyme_uniprot_canonical_ac", 
                    "glycan_pmid", "enzyme"]
            field_list_two = ["uniprot_canonical_ac", "uniprot_id", "refseq_ac", 
                                "protein_name", "gene_name", "pathway_id", "pathway_name", 
                                "disease_name","disease_id", 
                                "go_id", "go_term", "protein_pmid"] 
            tmp_obj_one, tmp_obj_two = [], []
            if query_obj["field"] in field_list_one:
                tmp_obj_one = apilib.glycan_typeahead(query_obj, config_obj)
            if query_obj["field"] in field_list_two:
                tmp_obj_two = apilib.protein_typeahead(query_obj, config_obj)
            if "error_list" in tmp_obj_one:
                res_obj = tmp_obj_one
            elif "error_list" in tmp_obj_two: 
                res_obj = tmp_obj_two
            else:
                res_obj = tmp_obj_one + tmp_obj_two
    except Exception, e:
        res_obj = errorlib.get_error_obj("typeahead", traceback.format_exc(), path_obj)
       

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code





@app.route('/categorized_typeahead/', methods=['GET', 'POST'])
def categorized_typeahead():

    res_obj = []
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            tmp_obj = apilib.categorized_typeahead(query_obj, config_obj)
            if "error_list" in tmp_obj:
                res_obj = tmp_obj
            else:
                res_obj = tmp_obj
    except Exception, e:
        res_obj = errorlib.get_error_obj("categorized_typeahead", traceback.format_exc(), path_obj)
   
   
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/global_typeahead/', methods=['GET', 'POST'])
def global_typeahead():

    res_obj = []
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code": "missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code": "invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            tmp_obj = apilib.global_typeahead(query_obj, config_obj)
            if "error_list" in tmp_obj:
                res_obj = tmp_obj
            else:
                res_obj = tmp_obj
    except Exception, e:
        res_obj = errorlib.get_error_obj("global_typeahead", traceback.format_exc(), path_obj)


    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code

