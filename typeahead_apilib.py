import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict


from pymongo import MongoClient
from pymongo.errors import ConnectionFailure





def glycan_typeahead(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["glytoucan_ac", "motif_name", "enzyme_uniprot_canonical_ac"]
                                                                       
    max_query_value_len = 1000
    required_keys = ["field", "value", "limit"]
    for key in required_keys:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}
    
    if is_int(query_obj["limit"]) == False:
        return {"error_code":"invalid-parameter-value"}
    if query_obj["field"] not in field_list:
        return {"error_code":"invalid-field-for-typeahead"}
    if len(query_obj["value"]) > max_query_value_len:
        return {"error_code":"invalid-parameter-value-length"}



    res_obj = []
    mongo_query = {}
    if query_obj["field"] == "glytoucan_ac":
        mongo_query = {"glytoucan_ac":{'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["glytoucan_ac"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))
    elif query_obj["field"] == "enzyme_uniprot_canonical_ac":
        mongo_query = {"enzyme.uniprot_canonical_ac": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["enzyme"]:
                if o["uniprot_canonical_ac"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["uniprot_canonical_ac"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))
    elif query_obj["field"] == "motif_name":
        mongo_query = {"motifs.name": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["motifs"]:
                if o["name"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["name"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))

        
    return sorted(set(res_obj))



def protein_typeahead(query_obj, db_obj):



    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["uniprot_canonical_ac", "uniprot_id", "refseq_ac", 
                    "protein_name", "gene_name", "pathway_id", "pathway_name", "disease_name"] 


    max_query_value_len = 1000
    required_keys = ["field", "value", "limit"]
    for key in required_keys:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}

    if is_int(query_obj["limit"]) == False:
        return {"error_code":"invalid-parameter-value"}
    if query_obj["field"] not in field_list:
        return {"error_code":"invalid-field-for-typeahead"}
    if len(query_obj["value"]) > max_query_value_len:
        return {"error_code":"invalid-parameter-value-length"}



    res_obj = []
    mongo_query = {}
    if query_obj["field"] == "uniprot_canonical_ac":
        mongo_query = {"uniprot_canonical_ac":{'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["uniprot_canonical_ac"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))
    if query_obj["field"] == "uniprot_id":
        mongo_query = {"uniprot_id":{'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["uniprot_id"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))
    if query_obj["field"] == "refseq_ac":
        mongo_query = {"refseq.ac":{'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["refseq"]["ac"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))
    elif query_obj["field"] == "gene_name":
        mongo_query = {"gene.name": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["gene"]:
                if o["name"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["name"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))
    elif query_obj["field"] == "protein_name":
        mongo_query = {"recommendedname.full": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["recommendedname"]["full"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))
        #mongo_query = {"recommendedname.short": {'$regex': query_obj["value"], '$options': 'i'}}
        #for obj in dbh[collection].find(mongo_query):
        #    res_obj.append(obj["recommendedname"]["short"])
        #    if len(sorted(set(res_obj))) >= query_obj["limit"]:
        #        return sorted(set(res_obj))
    elif query_obj["field"] == "disease_name":
        mongo_query = {"disease.name": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["disease"]:
                if o["name"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["name"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))
    elif query_obj["field"] == "pathway_name":
        mongo_query = {"pathway.name": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["pathway"]:
                if o["name"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["name"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))
    elif query_obj["field"] == "pathway_id":
        mongo_query = {"pathway.id": {'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            for o in obj["pathway"]:
                if o["id"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["id"])
                    if len(sorted(set(res_obj))) >= query_obj["limit"]:
                        return sorted(set(res_obj))
    return sorted(set(res_obj))



def dump_debug_log(out_string):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return



def get_random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))



def get_error_obj(error_code, error_log, path_obj):
    
    error_id = get_random_string(6) 
    log_file = path_obj["apierrorlogpath"] + "/" + error_code + "-" + error_id + ".log"
    with open(log_file, "w") as FW:
        FW.write("%s" % (error_log))
    return {"error_code": "exception-error-" + error_id}




def is_valid_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True


def is_float(input):
      
    try:
        num = float(input)
    except ValueError:
        return False
    return True


                  
def is_int(input):
    try:
        num = int(input)
    except ValueError:
        return False
    return True
