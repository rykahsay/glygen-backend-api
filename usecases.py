import os
import json
import string
import csv
import traceback
import usecases_apilib as apilib
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


@app.route('/usecases/search_init/', methods=['GET', 'POST'])
def usecases_search_init():
  
    res_obj = {}
    try:
        res_obj = apilib.usecases_search_init(config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("usecases_search_init", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/glycan_to_biosynthesis_enzymes/<tax_id>/<glytoucan_ac>/', methods=['GET', 'POST'])
def glycan_to_biosynthesis_enzymes(tax_id, glytoucan_ac):


    res_obj = {}
    try:
        if glytoucan_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"glytoucan_ac"}]}
        elif tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"glytoucan_ac":glytoucan_ac, "tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.glycan_to_biosynthesis_enzymes(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_to_biosynthesis_enzymes", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/glycan_to_glycoproteins/<tax_id>/<glytoucan_ac>/', methods=['GET', 'POST'])
def glycan_to_glycoproteins(tax_id, glytoucan_ac):
    
    res_obj = {}
    try:
        if glytoucan_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"glytoucan_ac"}]}
        elif tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"glytoucan_ac":glytoucan_ac, "tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.glycan_to_glycoproteins(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_to_glycoproteins", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/glycan_to_enzyme_gene_loci/<tax_id>/<glytoucan_ac>/', methods=['GET', 'POST'])
def glycan_to_enzyme_gene_loci(tax_id, glytoucan_ac):

    res_obj = {}
    try:
        if glytoucan_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"glytoucan_ac"}]}
        elif tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"glytoucan_ac":glytoucan_ac, "tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.glycan_to_enzyme_gene_loci(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycan_to_enzyme_gene_loci", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code
    

@app.route('/usecases/biosynthesis_enzyme_to_glycans/<tax_id>/<uniprot_canonical_ac>/', methods=['GET', 'POST'])
def biosynthesis_enzyme_to_glycans(tax_id, uniprot_canonical_ac):

    res_obj = {}
    try:
        if uniprot_canonical_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"uniprot_canonical_ac"}]}
        elif tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"uniprot_canonical_ac":uniprot_canonical_ac, "tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.biosynthesis_enzyme_to_glycans(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("biosynthesis_enzyme_to_glycans", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/usecases/protein_to_orthologs/<uniprot_canonical_ac>/', methods=['GET', 'POST'])
def protein_to_orthologs(uniprot_canonical_ac):

    res_obj = {}
    try:
        if uniprot_canonical_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"uniprot_canonical_ac"}]}
        else:
            query_obj = {"uniprot_canonical_ac":uniprot_canonical_ac}
            util.trim_object(query_obj)
            res_obj = apilib.protein_to_orthologs(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_to_orthologs", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/usecases/protein_to_glycosequons/<uniprot_canonical_ac>/', methods=['GET', 'POST'])
def protein_to_glycosequons(uniprot_canonical_ac):

    res_obj = {}
    try:
        if uniprot_canonical_ac in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"uniprot_canonical_ac"}]}
        else:
            query_obj = {"uniprot_canonical_ac":uniprot_canonical_ac}
            util.trim_object(query_obj)
            res_obj = apilib.protein_to_glycosequons(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("protein_to_glycosequons", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/usecases/species_to_glycosyltransferases/<tax_id>/', methods=['GET', 'POST'])
def species_to_glycosyltransferases(tax_id):

    res_obj = {}
    try:
        if tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.species_to_glycosyltransferases(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("species_to_glycosyltransferases", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/species_to_glycohydrolases/<tax_id>/', methods=['GET', 'POST'])
def species_to_glycohydrolases(tax_id):

    res_obj = {}
    try:
        if tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.species_to_glycohydrolases(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("species_to_glycohydrolases", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/species_to_glycoproteins/<tax_id>/<evidence_type>/', methods=['GET', 'POST'])
def species_to_glycoproteins(tax_id, evidence_type):

    res_obj = {}
    try:
        if evidence_type in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"evidence_type"}]}
        elif tax_id in ["", "empty"]:
            res_obj = {"error_list":[{"error_code":"missing-parameter", "field":"tax_id"}]}
        elif util.isint(tax_id) == False:
            res_obj = {"error_list":[{"error_code":"invalid-parameter-value", "field":"tax_id"}]}
        else:
            query_obj = {"evidence_type":evidence_type, "tax_id":int(tax_id)}
            util.trim_object(query_obj)
            res_obj = apilib.species_to_glycoproteins(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("species_to_glycoproteins", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code



@app.route('/usecases/disease_to_glycosyltransferases/', methods=['GET', 'POST'])
def disease_to_glycosyltransferases():

    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "": 
            res_obj = {"error_list":[{"error_code":"missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code":"invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            res_obj = apilib.disease_to_glycosyltransferases(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("disease_to_glycosyltransferases", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




@app.route('/usecases/genelocus_list/', methods=['GET', 'POST'])
def genelocus_list():
   
    res_obj = {}
    try:
	query_value = util.get_arg_value("query", request.method)
        if query_value == "": 
            res_obj = {"error_list":[{"error_code":"missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code":"invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            res_obj = apilib.genelocus_list(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("genelocus_list", traceback.format_exc(), path_obj)
    
    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/ortholog_list/', methods=['GET', 'POST'])
def ortholog_list():

    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code":"missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code":"invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            res_obj = apilib.ortholog_list(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("ortholog_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code


@app.route('/usecases/glycosequon_list/', methods=['GET', 'POST'])
def glycosequon_list():

    res_obj = {}
    try:
        query_value = util.get_arg_value("query", request.method)
        if query_value == "":
            res_obj = {"error_list":[{"error_code":"missing-query-key-in-query-json"}]}
        elif util.is_valid_json(query_value) == False:
            res_obj = {"error_list":[{"error_code":"invalid-query-json"}]}
        else:
            query_obj = json.loads(query_value)
            util.trim_object(query_obj)
            res_obj = apilib.glycosequon_list(query_obj, config_obj)
    except Exception, e:
        res_obj = errorlib.get_error_obj("glycosequon_list", traceback.format_exc(), path_obj)

    http_code = 500 if "error_list" in res_obj else 200
    return jsonify(res_obj), http_code




