import os
import json
import string
import csv
import traceback
import typeahead_apilib as apilib

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
app = Flask(__name__)
CORS(app)


global config_obj
global path_obj

config_obj = json.loads(open("./conf/config.json", "r").read())
path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
db_obj =  config_obj[config_obj["server"]]["dbinfo"]


@app.route('/typeahead/', methods=['GET', 'POST'])
def typeahead():

    res_obj = []
    try:
        query_value = get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_code": "missing-query-key-in-query-json"}
        elif apilib.is_valid_json(query_value) == False:
            res_obj = {"error_code": "invalid-query-json"}
        else:
            query_obj = json.loads(query_value)
            trim_object(query_obj)
            field_list_one = ["glytoucan_ac", "motif_name", "enzyme_uniprot_canonical_ac"]
            field_list_two = ["uniprot_canonical_ac", "uniprot_id", "refseq_ac", 
                                "protein_name", "gene_name", "pathway_id", "pathway_name", "disease_name"] 
            tmp_obj_one, tmp_obj_two = [], []
            if query_obj["field"] in field_list_one:
                tmp_obj_one = apilib.glycan_typeahead(query_obj, db_obj)
            if query_obj["field"] in field_list_two:
                tmp_obj_two = apilib.protein_typeahead(query_obj, db_obj)
            if "error_code" in tmp_obj_one:
                res_obj = tmp_obj_one
            elif "error_code" in tmp_obj_two: 
                res_obj = tmp_obj_two
            else:
                res_obj = tmp_obj_one + tmp_obj_two
    except Exception, e:
        res_obj = apilib.get_error_obj("typeahead", traceback.format_exc(), path_obj)
        
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
