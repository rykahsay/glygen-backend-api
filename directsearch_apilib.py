import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict


import errorlib
import util

import protein_apilib
import glycan_apilib
import usecases_apilib

def protein(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #glycan.attached is not implemented in c_protein jsons yet
    if "glycan" in query_obj:
        if "relation" in query_obj["glycan"]:
            if query_obj["glycan"]["relation"] not in ["attached", "binding", "any"]:
                return {"error_list":[{"error_code":"invalid-parameter-value", "field":"glycan.relation"}]}

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_search_direct", query_obj,config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = protein_apilib.get_mongo_query(query_obj)
    #return mongo_query
    
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    results_dict = {}
    i = 0
    for obj in dbh[collection].find(mongo_query):
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        if main_id not in obj:
            continue
        results_dict[obj[main_id]] = obj

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    return res_obj



def gene(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("gene_search_direct", query_obj,config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = protein_apilib.get_mongo_query(query_obj)
    #return mongo_query
    
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    results_dict = {}
    i = 0
    for obj in dbh[collection].find(mongo_query):
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        if main_id not in obj:
            continue
        results_dict[obj[main_id]] = obj

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    return res_obj




def get_results_batch(results_dict, query_obj, config_obj):

    id_list = sorted(results_dict.keys())
    max_batch_size = config_obj["max_batch_size"]
    batch_size = query_obj["limit"] if "limit" in query_obj else max_batch_size
    batch_size = max_batch_size if batch_size > max_batch_size else batch_size

    offset = query_obj["offset"] - 1 if "offset" in query_obj else 0
    end = offset + batch_size
    end = len(id_list) if end > len(id_list) else end

    batch_obj = {"limit":batch_size,"offset":offset + 1, "total_hits":len(id_list)}
    for k in ["limit", "offset"]:
        if k in query_obj:
            query_obj.pop(k)
    query_info = {"query":query_obj, "batch":batch_obj}

    res_obj = {"queryinfo":query_info, "results":[]}
    for main_id in id_list[offset:end]:
        res_obj["results"].append(results_dict[main_id])

    return res_obj



def glycan(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Clean query object
    key_list = query_obj.keys()
    for key in key_list:
        flag_list = []
        #flag_list.append(key in ["query_type", "operation"])
        flag_list.append(str(query_obj[key]).strip() == "")
        flag_list.append(query_obj[key] == [])
        flag_list.append(query_obj[key] == {})
        if True in flag_list:
            query_obj.pop(key)

    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_search_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    residue_list = []
    for o in dbh["c_searchinit"].find_one({})["glycan"]["composition"]:
        residue_list.append(o["residue"])


    #If residue is not in query, add it with default range in query
    seen = {}
    default_min, default_max = 0, 0
    if "composition" in query_obj:
        for o in query_obj["composition"]:
            res = o["residue"]
            seen[res] = True
            if res == "default":
                default_min, default_max = o["min"], o["max"]
                query_obj["composition"].remove(o)

        for res in residue_list:
            if res not in seen:
                o = {"residue":res, "min":default_min, "max":default_max}
                query_obj["composition"].append(o)
        


    mongo_query = glycan_apilib.get_mongo_query(query_obj)

    #return mongo_query
   
    collection = "c_glycan"
    main_id = "glytoucan_ac"
    results_dict = {}
    i = 0
    for obj in dbh[collection].find(mongo_query):
        i += 1
        if i > config_obj["max_results_count"]["glycan"]:
            break
        if main_id not in obj:
            continue
        results_dict[obj[main_id]] = obj

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    return res_obj




def glycan_to_biosynthesis_enzymes(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_to_biosynthesis_enzymes_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    collection = "c_glycan"    
    results = []
    
    mongo_query = usecases_apilib.get_mongo_query("glycan_to_biosynthesis_enzymes",  query_obj)
    obj_one = dbh[collection].find_one(mongo_query)
    if obj_one == None:
        error_list.append({"error_code":"non-existent-record"})
        return {"error_list":error_list}


    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    seen = {}
    for o in obj_one["enzyme"]:
        canon = o[main_id]
        if canon not in seen:
            obj_two = dbh[collection].find_one({main_id:canon})
            seen[canon] = True
            i += 1
            if i > config_obj["max_results_count"]["protein"]:
                break
            results_dict[canon] = obj_two

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    return res_obj


def glycan_to_glycoproteins(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_to_glycoproteins_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_glycan"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("glycan_to_glycoproteins",  query_obj)
    obj_one = dbh[collection].find_one(mongo_query)
    if obj_one == None:
        error_list.append({"error_code":"non-existent-record"})
        return {"error_list":error_list}


    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    seen = {}
    for o in obj_one["glycoprotein"]:
        canon = o[main_id]
        if canon not in seen:
            obj_two = dbh[collection].find_one({main_id:canon})
            seen[canon] = True
            i += 1
            if i > config_obj["max_results_count"]["protein"]:
                break
            results_dict[canon] = obj_two

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj
    


def biosynthesis_enzyme_to_glycans(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("biosynthesis_enzyme_to_glycans_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_glycan"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("biosynthesis_enzyme_to_glycans", query_obj)
    results_dict = {}
    i = 0
    collection = "c_glycan"
    main_id = "glytoucan_ac"
    for obj_two in dbh[collection].find(mongo_query):
        if main_id not in obj_two:
            continue
        glytoucan_ac = obj_two[main_id]
        if i > config_obj["max_results_count"]["glycan"]:
            break
        results_dict[glytoucan_ac] = obj_two

    res_obj = get_results_batch(results_dict, query_obj, config_obj)

    return res_obj


def protein_to_homologs(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_to_homologs_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_protein"
    results = []
    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]
    }
    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    for obj_one in dbh[collection].find(mongo_query):
        for o in obj_one["orthologs"]:
            canon = o[main_id]
            obj_two = dbh[collection].find_one({"uniprot_canonical_ac":canon})
            i += 1
            if i > config_obj["max_results_count"]["protein"]:
                break
            results_dict[canon] = obj_two
    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj


def species_to_glycosyltransferases(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("species_to_glycosyltransferases_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_protein"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("species_to_glycosyltransferases", query_obj)
        
    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    for obj_one in dbh[collection].find(mongo_query):
        canon = obj_one[main_id]
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        results_dict[canon] = obj_one


    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj



def species_to_glycohydrolases(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("species_to_glycohydrolases_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_protein"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("species_to_glycohydrolases", query_obj)
    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    for obj_one in dbh[collection].find(mongo_query):
        canon = obj_one[main_id]
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        results_dict[canon] = obj_one


    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj


def species_to_glycoproteins(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("species_to_glycoproteins_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_protein"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("species_to_glycoproteins", query_obj)
    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    for obj_one in dbh[collection].find(mongo_query):
        canon = obj_one[main_id]
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        results_dict[canon] = obj_one

    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj


def disease_to_glycosyltransferases(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("disease_to_glycosyltransferases_direct", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_protein"
    results = []
    mongo_query = usecases_apilib.get_mongo_query("disease_to_glycosyltransferases", query_obj)
    results_dict = {}
    i = 0
    collection = "c_protein"
    main_id = "uniprot_canonical_ac"
    for obj_one in dbh[collection].find(mongo_query):
        canon = obj_one[main_id]
        i += 1
        if i > config_obj["max_results_count"]["protein"]:
            break
        results_dict[canon] = obj_one


    res_obj = get_results_batch(results_dict, query_obj, config_obj)
    
    return res_obj


