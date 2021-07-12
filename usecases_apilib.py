import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from pytz import timezone
from bson import json_util, ObjectId

import errorlib
import util

import protein_apilib


def search_init(config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_search_init",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_searchinit"

    res_obj =  dbh[collection].find_one({})
    if res_obj == None or "usecases" not in res_obj:
        return {"error_list":[{"error_code":"non-existent-search-init"}]}

    return res_obj["usecases"]



def glycan_to_biosynthesis_enzymes(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    mongo_query = get_mongo_query("glycan_to_biosynthesis_enzymes",  query_obj)
    #return mongo_query


    collection = "c_glycan"    
    cache_collection = "c_cache"

    search_type = "glycan_to_biosynthesis_enzymes"
    record_type = "protein"
    record_list = []
    prj_obj = {"enzyme":1}
    obj = dbh[collection].find_one(mongo_query, prj_obj)
    seen = {}
    if obj != None:
        for o in obj["enzyme"]:
            if o["uniprot_canonical_ac"] not in seen:
                seen[o["uniprot_canonical_ac"]] = True
                tax_id = o["tax_id"]
                if query_obj["tax_id"] == 0:
                    record_list.append(o["uniprot_canonical_ac"])
                elif tax_id == query_obj["tax_id"]:
                    record_list.append(o["uniprot_canonical_ac"])

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}
    
    

    return res_obj


def glycan_to_glycoproteins(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("glycan_to_glycoproteins",  query_obj)
    #return mongo_query

    collection = "c_glycan"    
    cache_collection = "c_cache"


    search_type = "glycan_to_glycoproteins"
    record_type = "protein"
    record_list = []
    seen = {}
    prj_obj = {"glycoprotein":1}
    for obj in dbh[collection].find(mongo_query, prj_obj):
        for o in obj["glycoprotein"]:
            if o["uniprot_canonical_ac"] not in seen:
                seen[o["uniprot_canonical_ac"]] = True
                tax_id = o["tax_id"]
                if query_obj["tax_id"] == 0:
                    record_list.append(o["uniprot_canonical_ac"])
                elif tax_id == query_obj["tax_id"]:
                    record_list.append(o["uniprot_canonical_ac"])

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}



    return res_obj

def glycan_to_enzyme_gene_loci(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("glycan_to_enzyme_gene_loci", query_obj)
    #return mongo_query
        
    collection = "c_glycan"    
    cache_collection = "c_cache"

    results = []
    prj_obj = {"enzyme":1}
    for obj in dbh[collection].find(mongo_query, prj_obj):
        for o in obj["enzyme"]:
            plist_obj,tax_id = get_genelocus_list_fields(dbh, o["uniprot_canonical_ac"])
            if plist_obj == {}:
                continue
            if query_obj["tax_id"] == 0:
                results.append(plist_obj)
            elif tax_id == query_obj["tax_id"]:
                results.append(plist_obj)

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
    if len(results) == 0:
        res_obj = {"list_id":""}
    else:
        ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        hash_obj = hashlib.md5(json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        search_results_obj = {}
        search_results_obj["list_id"] = list_id
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":"gene_locus",
            "search_type":"glycan_to_enzyme_gene_loci"
        }
        search_results_obj["cache_info"] = cache_info
        search_results_obj["results"] = results
        result = dbh[cache_collection].delete_many({"list_id":list_id})
        result = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id

    return res_obj


def biosynthesis_enzyme_to_glycans(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_two", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("biosynthesis_enzyme_to_glycans", query_obj)
    #return mongo_query


    collection = "c_glycan"
    cache_collection = "c_cache"

    search_type = "biosynthesis_enzyme_to_glycans"
    record_type = "glycan"      
    record_list = []
    prj_obj = {"glytoucan_ac":1}
    for obj in dbh[collection].find(mongo_query, prj_obj):
        record_list.append(obj["glytoucan_ac"])

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj


def protein_to_glycosequons(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_seven", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    #mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]
    }
    #return mongo_query


    collection = "c_protein"    
    cache_collection = "c_cache"

    obj = dbh[collection].find_one(mongo_query)
    tmp_list = obj["site_annotation"] if obj != None else []
    results = []
    for o in tmp_list:
        if o["annotation"] == "n_glycosylation_sequon":
            results.append(o)
    

    res_obj = {}
    if len(results) == 0:
        res_obj = {"list_id":""}
    else:
        ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        hash_obj = hashlib.md5(json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        search_results_obj = {}
        search_results_obj["list_id"] = list_id
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":"glycosequon",
            "search_type":"protein_to_glycosequons"
        }
        search_results_obj["cache_info"] = cache_info
        search_results_obj["results"] = results
        result = dbh[cache_collection].delete_many({"list_id":list_id})
        result = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id

    return res_obj



def protein_to_orthologs(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_three", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    #mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]   
    }
    #return mongo_query


    collection = "c_protein"    
    cache_collection = "c_cache"

    results = []
    obj = dbh[collection].find_one(mongo_query)
    
    results = obj["orthologs"] if obj != None else []

    res_obj = {}
    if len(results) == 0:
        res_obj = {"list_id":""}
    else:
        ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        hash_obj = hashlib.md5(json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        search_results_obj = {}
        search_results_obj["list_id"] = list_id
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":"ortholog",
            "search_type":"protein_to_orthologs"
        }
        search_results_obj["cache_info"] = cache_info
        search_results_obj["results"] = results
        result = dbh[cache_collection].delete_many({"list_id":list_id})
        result = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id

    return res_obj



def species_to_glycosyltransferases(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_four", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycosyltransferases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_cache"

    search_type = "species_to_glycosyltransferases"
    record_type = "protein"
    record_list = []
    for obj in dbh[collection].find(mongo_query, config_obj["projectedfields"][collection]):
        record_list.append(obj["uniprot_canonical_ac"])

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj


def species_to_glycohydrolases(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_four", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycohydrolases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_cache"

    search_type = "species_to_glycohydrolases"
    record_type = "protein"
    record_list = []
    for obj in dbh[collection].find(mongo_query, config_obj["projectedfields"][collection]):
        record_list.append(obj["uniprot_canonical_ac"])


    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj



def species_to_glycoproteins(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_five", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycoproteins",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_cache"


    search_type = "species_to_glycoproteins"
    record_type = "protein"
    record_list = []
    for obj in dbh[collection].find(mongo_query, config_obj["projectedfields"][collection]):
        record_list.append(obj["uniprot_canonical_ac"])


    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj


def disease_to_glycosyltransferases(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_six", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    mongo_query = get_mongo_query("disease_to_glycosyltransferases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_cache"


    search_type = "disease_to_glycosyltransferases"
    record_type = "protein"
    record_list = []
    for obj in dbh[collection].find(mongo_query, config_obj["projectedfields"][collection]):
        record_list.append(obj["uniprot_canonical_ac"])


    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    list_id = ""
    if len(record_list) != 0:
        hash_obj = hashlib.md5(record_type + "_" + json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        cache_info = {
            "query":query_obj,
            "ts":ts,
            "record_type":record_type,
            "search_type":search_type
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj



def genelocus_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    cache_collection = "c_cache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}


    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}


    default_hash = {"offset":1, "limit":20, "sort":"gene_name", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}


    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"cache_info":cached_obj["cache_info"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
	return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj



def glycosequon_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
    cache_collection = "c_cache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}

    default_hash = {"offset":1, "limit":20, "sort":"id", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}

    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"cache_info":cached_obj["cache_info"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
        return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj




def ortholog_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
    cache_collection = "c_cache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}

    default_hash = {"offset":1, "limit":20, "sort":"id", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}

    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"cache_info":cached_obj["cache_info"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
	return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj


def get_protein_list_fields(dbh, uniprot_canonical_ac):

    collection = "c_protein"
    obj = dbh[collection].find_one({"uniprot_canonical_ac":uniprot_canonical_ac})
    plist_obj = protein_apilib.get_protein_list_object(obj)
    return plist_obj, obj["species"][0]["taxid"]

def get_glycan_list_fields(dbh, glytoucan_ac):
  
    collection = "c_glycan"
    obj = dbh[collection].find_one({"glytoucan_ac":glytoucan_ac})

    seen = {"enzyme":{}, "glycoprotein":{}}
    for o in obj["glycoprotein"]:
        seen["glycoprotein"][o["uniprot_canonical_ac"].lower()] = True
    for o in obj["enzyme"]:
        seen["enzyme"][o["uniprot_canonical_ac"].lower()] = True

    mass = obj["mass"] if "mass" in obj else -1
    mass_pme = obj["mass_pme"] if "mass_pme" in obj else -1

    return {
        "glytoucan_ac":glytoucan_ac
        ,"mass":mass
        ,"mass_pme":mass_pme
        ,"number_monosaccharides": obj["number_monosaccharides"]
        ,"number_enzymes":len(seen["enzyme"].keys()) 
        ,"number_proteins":len(seen["glycoprotein"].keys()) 
        ,"iupac": obj["iupac"] if "iupac" in obj else ""
        ,"glycoct": obj["glycoct"]
    }


def get_genelocus_list_fields(dbh, uniprot_canonical_ac):

    collection = "c_protein"
    obj = dbh[collection].find_one({"uniprot_canonical_ac":uniprot_canonical_ac})
    protein_name = util.extract_name(obj["protein_names"], "recommended", "UniProtKB")
    gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
    organism = obj["species"][0]["name"] if obj["species"] != [] else ""
    tax_id = obj["species"][0]["taxid"] if obj["species"] != [] else 0
    gene_url = obj["gene"][0]["url"]
    for o in obj["isoforms"]:
        if o["isoform_ac"] == uniprot_canonical_ac:
            if o["locus"] == {}:
                return {}, tax_id
            plist_obj = {
                "uniprot_canonical_ac":uniprot_canonical_ac
                ,"protein_name":protein_name
                ,"gene_name":gene_name
                ,"gene_link":gene_url
                ,"tax_id":tax_id
                ,"organism":organism
                ,"chromosome":o["locus"]["chromosome"]
                ,"start_pos":o["locus"]["start_pos"]
                ,"end_pos":o["locus"]["end_pos"]
            }
            return plist_obj, tax_id





def get_mongo_query(svc_name, query_obj):

    svc_grp = [
            []
            ,["glycan_to_biosynthesis_enzymes","glycan_to_glycoproteins", "glycan_to_enzyme_gene_loci"]
            ,["biosynthesis_enzyme_to_glycans"]
            ,["species_to_glycosyltransferases"]
            ,["species_to_glycohydrolases"]
            ,["species_to_glycoproteins"]
            ,["disease_to_glycosyltransferases"]
    ] 


    cond_objs = []
    if svc_name in svc_grp[1]:
        #For this services, only search by glytoucan_ac, tax_id filtering is done to the proteins
        if "glytoucan_ac" in query_obj:
            cond_objs.append({"glytoucan_ac":{'$eq': query_obj["glytoucan_ac"]}})
    elif svc_name in svc_grp[2]:
        if "uniprot_canonical_ac" in query_obj:
            #cond_objs.append({"enzyme.uniprot_canonical_ac": {'$eq': query_obj["uniprot_canonical_ac"]}})
            cond_objs.append({"enzyme.uniprot_canonical_ac": {'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}})

        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                tax_id_q_obj = {
                    "$or":[
                        {"species.taxid": {'$eq': query_obj["tax_id"]}},
                        {"species.taxid": {'$eq': str(query_obj["tax_id"])}}
                    ]
                }
                cond_objs.append(tax_id_q_obj)
                #cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
    elif svc_name in svc_grp[3]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                tax_id_q_obj = {
                    "$or":[
                        {"species.taxid": {'$eq': query_obj["tax_id"]}},
                        {"species.taxid": {'$eq': str(query_obj["tax_id"])}}
                    ]   
                }
                cond_objs.append(tax_id_q_obj)
                #cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            cond_objs.append({"keywords": "glycosyltransferase-activity"}) 
    elif svc_name in svc_grp[4]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                tax_id_q_obj = {
                    "$or":[
                        {"species.taxid": {'$eq': query_obj["tax_id"]}},
                        {"species.taxid": {'$eq': str(query_obj["tax_id"])}}
                    ]
                }
                cond_objs.append(tax_id_q_obj)
                #cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            cond_objs.append({"keywords": "glycohydrolase-activity"})
    elif svc_name in svc_grp[5]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                tax_id_q_obj = {
                    "$or":[
                        {"species.taxid": {'$eq': query_obj["tax_id"]}},
                        {"species.taxid": {'$eq': str(query_obj["tax_id"])}}
                    ]
                }
                cond_objs.append(tax_id_q_obj)
                #cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            if query_obj["evidence_type"] == "predicted":
                cond_objs.append({"glycosylation": {'$gt':[]}})
                cond_objs.append({"glycosylation.site_category": {'$ne':"reported"}})
                cond_objs.append({"glycosylation.site_category": {'$ne':"reported_with_glycan"}})
            elif query_obj["evidence_type"] == "reported":
                cond_objs.append({"glycosylation": {'$gt': []}})
                cond_objs.append({"glycosylation.site_category":{"$regex":"reported","$options":"i"}})
            elif query_obj["evidence_type"] == "both":
                cond_objs.append({"glycosylation": {'$gt': []}})
            elif query_obj["evidence_type"] == "none":
                #to return empty list
                cond_objs.append({"glycosylation.evidence.database": {'$eq':"XYZzyz"}})
    elif svc_name in svc_grp[6]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                tax_id_q_obj = {
                    "$or":[
                        {"species.taxid": {'$eq': query_obj["tax_id"]}},
                        {"species.taxid": {'$eq': str(query_obj["tax_id"])}}
                    ]
                }
                cond_objs.append(tax_id_q_obj)
                #cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            if query_obj["do_name"] > 0:
                q_one = {"disease.recommended_name.name": {'$regex': query_obj["do_name"], '$options': 'i'}}
                q_two = {"disease.synonyms.name": {'$regex': query_obj["do_name"], '$options': 'i'}}
                cond_objs.append({"$or":[q_one, q_two]})
            cond_objs.append({"keywords": "glycosyltransferase-activity"})
    mongo_query = {} if cond_objs == [] else { "$and": cond_objs }
    return mongo_query




def sort_objects(obj_list, field_name, order_type):

    seen = {
        "uniprot_canonical_ac":{} 
        ,"protein_name":{} 
        ,"gene_name":{}
        ,"chromosome":{}
        ,"start_pos":{}
        ,"end_pos":{}
        ,"organism":{}
        ,"tax_id":{}
    }

    grid_obj = {
        "uniprot_canonical_ac":[]
        ,"protein_name":[]
        ,"gene_name":[]
        ,"chromosome":[]
        ,"start_pos":[]
        ,"end_pos":[]
        ,"organism":[]
        ,"tax_id":[]
    }
    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        grid_obj[field_name].append({"index":i, field_name:obj[field_name]})

    reverse_flag = True if order_type == "desc" else False
    key_list = []
    sorted_obj_list = sorted(grid_obj[field_name], key=lambda x: x[field_name], reverse=reverse_flag)
    for o in sorted_obj_list:
            key_list.append(o["index"])
    return key_list








