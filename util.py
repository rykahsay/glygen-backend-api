import os
import string
import json
import random
from flask import request
from collections import OrderedDict
import gzip
import io

import pymongo
import errorlib
import datetime
import pytz
import hashlib


def connect_to_mongodb(db_obj):

    try:
        client = pymongo.MongoClient('mongodb://localhost:27017',
            username=db_obj["mongodbuser"],
            password=db_obj["mongodbpassword"],
            authSource=db_obj["mongodbname"],
            authMechanism='SCRAM-SHA-1',
            serverSelectionTimeoutMS=10000
        )
        client.server_info()
        dbh = client[db_obj["mongodbname"]]
        return dbh, {}
    except pymongo.errors.ServerSelectionTimeoutError as err:
        return {}, {"error_list":[{"error_code": "open-connection-failed"}]}
    except pymongo.errors.OperationFailure as err:
        return {}, {"error_list":[{"error_code": "mongodb-auth-failed"}]}



def get_random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def is_valid_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True

def isint(value):
  try:
    int(value)
    return True
  except ValueError:
    return False

def get_hit_score(doc, cache_info):

    search_query = cache_info["query"]
    if "concept_query_list" in cache_info["query"]:
        search_query = cache_info["query"]["concept_query_list"]
    record_type = cache_info["record_type"]
    search_type = cache_info["search_type"]

    cond_match_freq = {}
    if record_type == "glycan":
        glytoucan_ac = doc["glytoucan_ac"]
        cond = "glycan_exact_match"
        if search_type == "search_simple":
            if glytoucan_ac.lower() == search_query["term"].lower():
                cond_match_freq[cond] = 1
        elif search_type == "search":
            if "glycan_identifier" in search_query:
                val_list = []
                for k in ["glytoucan_ac","iupac", "glycoct"]:
                    if k in doc:
                        if doc[k] != "":
                            val_list.append(doc[k].lower())
                q_val_list = search_query["glycan_identifier"]["glycan_id"].lower().split(",")
                if len(list(set(q_val_list).intersection(val_list))) > 0:
                    cond_match_freq[cond] = 1
        
        if doc["number_proteins"] > 0:
            cond_match_freq["glycan_has_glycoprotein"] = doc["number_proteins"]
        if doc["number_enzymes"] > 0:
            cond_match_freq["glycan_has_enzyme"] = doc["number_enzymes"]
        if doc["number_species"] > 0:
            cond_match_freq["glycan_has_species"] = doc["number_species"]
        if len(doc["publication"].split(";")) > 0:
            cond_match_freq["glycan_has_publication"] = len(doc["publication"].split(";"))
        if doc["keywords"].find("fully_determined") != -1:
            cond_match_freq["glycan_fully_determined"] = 1
        #Disease association (5 points) 
    elif record_type == "protein":
        val_list = []
        p_list = ["uniprot_canonical_ac","protein_names_refseq","refseq_name",
                "protein_names_uniprotkb","protein_name","gene_names_refseq",
                "gene_names_uniprotkb","gene_name"]
        for p in p_list:
            val_list.append(doc[p].lower())
        
        qval_list = []
        if search_type == "supersearch":
            for q_obj in search_query:
                if "unaggregated_list" in q_obj["query"]:
                    for o in q_obj["query"]["unaggregated_list"]:
                        if "string_value" in o:
                            p,v = o["path"].split(".")[-1], o["string_value"]
                            if p in p_list:
                                qval_list.append(v)
        else:
            for f in search_query:
                if type(search_query[f]) is unicode:
                    qval_list.append(search_query[f].lower())
        
        cond = "protein_exact_match"
        for qval in qval_list:
            if qval in val_list:
                if cond not in cond_match_freq:
                    cond_match_freq[cond] = 0
                cond_match_freq[cond] += 1
        p_list = ["reported_n_glycosites_with_glycan", "reported_o_glycosites_with_glycan",
            "reported_n_glycosites", "reported_o_glycosites", "predicted_glycosites",
            "publication_count"
        ]
        for p in p_list:
            n = doc[p]
            if n > 0:
                cond = "protein_" + p
                cond_match_freq[cond] = n
        #Has reported glycosite+ fully-determined glycan structure (4 points)
    elif record_type == "site":
        for p in ["glycosylation", "mutagenesis", "snv"]:
            if len(doc[p]) > 0:
                cond = "site_has_" + p
                cond_match_freq[cond] = 1

    score_dict = json.loads(open("./conf/hit_scoring.json", "r").read())
    score = 0.1
    for cond in cond_match_freq:
        freq = cond_match_freq[cond]
        score += score_dict[cond] + round(float(freq)/100.00,3)


    return round(float(score), 3)


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
    
    return




def order_obj(json_obj, ordr_dict):

    for k1 in json_obj:
        ordr_dict[k1] = ordr_dict[k1] if k1 in ordr_dict else 1000
        if type(json_obj[k1]) is dict:
            for k2 in json_obj[k1]:
                ordr_dict[k2] = ordr_dict[k2] if k2 in ordr_dict else 1000
                if type(json_obj[k1][k2]) is dict:
                    for k3 in json_obj[k1][k2]:
                        ordr_dict[k3] = ordr_dict[k3] if k3 in ordr_dict else 1000
                    json_obj[k1][k2] = OrderedDict(sorted(json_obj[k1][k2].items(),
                        key=lambda x: float(ordr_dict.get(x[0]))))
                elif type(json_obj[k1][k2]) is list:
                    for j in xrange(0, len(json_obj[k1][k2])):
                        if type(json_obj[k1][k2][j]) is dict:
                            for k3 in json_obj[k1][k2][j]:
                                ordr_dict[k3] = ordr_dict[k3] if k3 in ordr_dict else 1000
                                json_obj[k1][k2][j] = OrderedDict(sorted(json_obj[k1][k2][j].items(),
                                    key=lambda x: float(ordr_dict.get(x[0]))))
            json_obj[k1] = OrderedDict(sorted(json_obj[k1].items(),
                key=lambda x: float(ordr_dict.get(x[0]))))

    return OrderedDict(sorted(json_obj.items(), key=lambda x: float(ordr_dict.get(x[0]))))



def order_list(list_obj, ordr_dict):

    for val in list_obj:
        if val not in ordr_dict:
            ordr_dict[val] = 10000

    return sorted(list_obj, key=lambda ordr: ordr_dict[ordr], reverse=False)



def sort_objects(obj_list, return_fields, field_name, order_type):

    field_list = return_fields["float"] + return_fields["int"] + return_fields["string"]
    grid_obj = {}
    for f in field_list:
        grid_obj[f] = []

    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        if field_name in return_fields["float"]:
            if field_name not in obj:
                obj[field_name] = -1.0
            grid_obj[field_name].append({"index":i, field_name:float(obj[field_name])})
        elif field_name in return_fields["string"]:
            if field_name not in obj:
                obj[field_name] = ""
            grid_obj[field_name].append({"index":i, field_name:obj[field_name]})
        elif field_name in return_fields["int"]:
            if field_name not in obj:
                obj[field_name] = -1
            grid_obj[field_name].append({"index":i, field_name:int(obj[field_name])})

    reverse_flag = True if order_type == "desc" else False
    key_list = []
    sorted_obj_list = sorted(grid_obj[field_name], key=lambda x: x[field_name], reverse=reverse_flag)
    for o in sorted_obj_list:
            key_list.append(o["index"])
    return key_list

def extract_name(obj_list, name_type, resource):
   
    if obj_list == []:
        return ""
    
    name_list_dict = {"recommended":[], "synonym":[]}
    for obj in obj_list:
        if obj["resource"] == resource:
            name_list_dict[obj["type"]].append(obj["name"])


    
    if name_type == "recommended" and name_list_dict["recommended"] == []:
        name_list_dict["recommended"] += name_list_dict["synonym"]


    if name_type == "all":
        return "; ".join(name_list_dict["recommended"] + name_list_dict["synonym"])
    else:
        return "; ".join(name_list_dict[name_type])




#######################
def clean_obj(obj, prop_list, obj_type):


    #First perform custom cleaning
    if obj_type == "c_protein":
        if "mass" in obj:
            if "monoisotopic_mass" in obj["mass"]:
                obj["mass"].pop("monoisotopic_mass")
        if "sequence" in obj:
            if "header" in obj["sequence"]:
                obj["sequence"].pop("header")
        if "isoforms" in obj:
            for o in obj["isoforms"]:
                if "header" in o["sequence"]:
                    o["sequence"].pop("header")

    for key in prop_list:
        if key in obj:
             obj.pop(key)


    #Now clean up empty valued properties
    if type(obj) is dict:
        key_list = obj.keys()
        for k1 in key_list:
            if obj[k1] in["", [], {}]:
                obj.pop(k1)
            elif type(obj[k1]) in [dict, list]:
                clean_obj(obj[k1], [], obj_type)
    elif type(obj) is list:
        for k1 in xrange(0, len(obj)):
            if obj[k1] in["", [], {}]:
                del obj[k1]
            elif type(obj[k1]) in [dict, list]:
                clean_obj(obj[k1], [], obj_type)
    
   
    return





def gzip_str(string_):
      
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode='w') as fo:
        fo.write(string_.encode())
    bytes_obj = out.getvalue()
    return bytes_obj



def get_cached_records_direct(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("cached_list", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    cache_collection = "c_cache"
    res_obj = {}
    default_hash = {"offset":1, "limit":20, "sort":"hit_score", "order":"desc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]

    #Get cached object
    mongo_query = {}
    if "id" in query_obj:
        mongo_query["list_id"] = query_obj["id"]
    cached_obj = dbh[cache_collection].find_one(mongo_query)

    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if cached_obj == None:
        post_error_list.append({"error_code":"non-existent-search-results"})
        return {"error_list":post_error_list}
  
    if "category" in query_obj:
        k = query_obj["category"] + "_legends"
        cached_obj["cache_info"]["legends"] = cached_obj["cache_info"][k]
        cached_obj["cache_info"].pop("mapped_legends")
        cached_obj["cache_info"].pop("unmapped_legends")


    cached_obj["results"] = [] 
    id_list = []
    for doc in dbh[cache_collection].find(mongo_query):
        for obj in doc["results"]:
            if "hit_score" not in obj:
                obj["hit_score"] = -1
            if "category" in query_obj:
                if query_obj["category"] == obj["category"]:
                    obj.pop("category")
                    cached_obj["results"].append(obj)
            else:
                cached_obj["results"].append(obj)
  
    res_obj = {"cache_info":cached_obj["cache_info"]}
    res_obj["results"] = []
    res_obj["pagination"] = {
        "offset":query_obj["offset"], 
        "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), 
        "sort":query_obj["sort"], 
        "order":query_obj["order"]
    }
    if len(cached_obj["results"]) == 0:
        return res_obj


    return_fields = {"string":[], "int":[], "float":[]}
    f_list = cached_obj["results"][0].keys() if cached_obj["results"] != []  else []
    for f in f_list:
        if type(cached_obj["results"][0][f]) is unicode:
            return_fields["string"].append(f)
        elif type(cached_obj["results"][0][f]) is int:
            return_fields["int"].append(f)
        elif type(cached_obj["results"][0][f]) is float:
            return_fields["float"].append(f)


    sorted_id_list = sort_objects(cached_obj["results"], return_fields,
                                        query_obj["sort"], query_obj["order"])

    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
        post_error_list.append({"error_code":"invalid-parameter-value", "field":"offset"})
        return {"error_list":post_error_list}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        for k in ["_id", "record_id"]:
            if k in obj:
                obj.pop(k)
        res_obj["results"].append(order_obj(obj, config_obj["objectorder"]["glycan"]))
    res_obj["pagination"]["total_length"] = len(cached_obj["results"])

    return res_obj



def get_cached_motif_records_direct(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("cached_list", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    res_obj = {}
    default_hash = {"offset":1, "limit":20, "sort":"hit_score", "order":"desc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]

    #Get cached object
    mongo_query = {"record_type":"motif"}
    cached_obj = {}
    cached_obj["results"] = [] 
    id_list = []
    for doc in dbh["c_list"].find(mongo_query):
        cached_obj["results"].append(doc)

    return_fields = {"string":[], "int":[], "float":[]}
    for f in cached_obj["results"][0].keys():
        if type(cached_obj["results"][0][f]) is unicode:
            return_fields["string"].append(f)
        elif type(cached_obj["results"][0][f]) is int:
            return_fields["int"].append(f)
        elif type(cached_obj["results"][0][f]) is float:
            return_fields["float"].append(f)


    sorted_id_list = sort_objects(cached_obj["results"], return_fields,
                                        query_obj["sort"], query_obj["order"])
    
    res_obj = {"cache_info":{"query":{}}}
    if len(cached_obj["results"]) == 0:
        return {}

    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
        post_error_list.append({"error_code":"invalid-parameter-value", "field":"offset"})
        return {"error_list":post_error_list}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []
    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        for k in ["_id", "record_id"]:
            if k in obj:
                obj.pop(k)
        res_obj["results"].append(order_obj(obj, config_obj["objectorder"]["glycan"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}

    return res_obj




def get_cached_records_indirect(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("cached_list", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    cache_collection = "c_cache"
    res_obj = {}
    default_hash = {"offset":1, "limit":20, "sort":"hit_score", "order":"desc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]

    #Get cached object
    mongo_query = {"list_id":query_obj["id"]}
    cached_obj = dbh[cache_collection].find_one(mongo_query)



    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if cached_obj == None:
        post_error_list.append({"error_code":"non-existent-search-results"})
        return {"error_list":post_error_list}
    
    id_list = []
    for doc in dbh[cache_collection].find(mongo_query):
        id_list += doc["results"]

    mongo_query = {"record_id":{"$in": id_list}}

    cached_obj.pop("_id")
    cached_obj["results"] = []
    for obj in dbh["c_list"].find(mongo_query):
        hit_score = get_hit_score(obj, cached_obj["cache_info"])
        obj["hit_score"] = hit_score
        cached_obj["results"].append(obj)


    #tmp_list = []
    #for o in cached_obj["results"]:
    #    tmp_list.append(o["record_id"])
    #for record_id in id_list:
    #    if record_id not in tmp_list:
    #        print record_id
    #return {}

    if len(cached_obj["results"]) == 0:
        return {}

    return_fields = {"string":[], "int":[], "float":[]}
    for f in cached_obj["results"][0].keys():
        if type(cached_obj["results"][0][f]) is unicode:
            return_fields["string"].append(f)
        elif type(cached_obj["results"][0][f]) is int:
            return_fields["int"].append(f)
        elif type(cached_obj["results"][0][f]) is float:
            return_fields["float"].append(f)


    sorted_id_list = sort_objects(cached_obj["results"], return_fields,
            query_obj["sort"], query_obj["order"])
    res_obj = {"cache_info":cached_obj["cache_info"]}
    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
        post_error_list.append({"error_code":"invalid-parameter-value", "field":"offset"})
        return {"error_list":post_error_list}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []
    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        for k in ["_id", "record_id"]:
            if k in obj:
                obj.pop(k)
        res_obj["results"].append(obj)
        #res_obj["results"].append(order_obj(obj, config_obj["objectorder"]["glycan"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}


    return res_obj






def cache_record_list(dbh,list_id, record_list, cache_info, cache_coll, config_obj):
    
    res = dbh[cache_coll].delete_many({"list_id":list_id})
    record_count = len(record_list)
    partition_count = record_count/config_obj["cache_batch_size"]
    for i in xrange(0,partition_count+1):
        start = i*config_obj["cache_batch_size"]
        end = start + config_obj["cache_batch_size"]
        end = record_count if end > record_count else end
        if start < record_count:
            cache_obj = {
                "list_id":list_id, 
                "cache_info":cache_info,
                "results":record_list[start:end]
            }
            res = dbh[cache_coll].insert_one(cache_obj)
        
    return


