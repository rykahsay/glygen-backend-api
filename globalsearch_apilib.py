import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict
from bson import json_util, ObjectId


import errorlib
import util
import protein_apilib



def globalsearch_search(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("globalsearch_search", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    
    #Load search config and plug in values
    search_obj = json.loads(open("./conf/global_search.json", "r").read())
    query_obj["term"] = query_obj["term"].replace("(", "\\(").replace(")", "\\)")

    for obj in search_obj:
        if "$text" in obj["mongoquery"]:
            obj["mongoquery"] = {'$text': { '$search': '\"' + query_obj["term"] + '\"'}}
        elif "$or" in obj["mongoquery"]:
            for o in obj["mongoquery"]["$or"]:
                for k in o:
                    if "$regex" in o[k]:
                        o[k]["$regex"] = query_obj["term"]
        elif "$and" in obj["mongoquery"]:
            for o in obj["mongoquery"]["$and"]:
                if "$or" in o:
                    for oo in o["$or"]:
                        for k in oo:
                            if "$regex" in oo[k]:
                                oo[k]["$regex"] = query_obj["term"]
                elif "$text" in o:
                    obj["mongoquery"]["$and"][0] = {'$text': { '$search': '\"' + query_obj["term"] + '\"'}}
                else:
                    for k in o:
                        if "$regex" in o[k]:
                            o[k]["$regex"] = query_obj["term"]
        
        else:
            for k in obj["mongoquery"]:
                o = obj["mongoquery"][k]
                if "$regex" in o:
                    o["$regex"] = query_obj["term"]
                elif "$eq" in o:     
                    o["$eq"] = query_obj["term"]


    #Filter cached global search results
    res_obj = {
        "exact_match": [],
        "other_matches": {"total_match_count":0}
    }
    seen_exact_match = {}
    
    results_dict = {}
    for obj in search_obj:
        key_one, key_two = obj["searchname"].split(".")
        if key_one not in res_obj["other_matches"]:
            res_obj["other_matches"][key_one] = {key_two:{}}
        if key_one not in results_dict:
            results_dict[key_one] = {"all":[]}
        if key_two not in results_dict[key_one]:
            results_dict[key_one][key_two] = []

        target_collection = obj["targetcollection"]
        cache_collection = "c_cache"
        qry_obj = obj["mongoquery"]

        prj_obj = config_obj["projectedfields"][target_collection] 


        doc_list = list(dbh[target_collection].find(qry_obj,prj_obj)) if key_two != "all" else []

        for doc in doc_list:
            doc.pop("_id")
            record_type, record_id, record_name = "", "", ""
            if target_collection == "c_protein":
                list_obj = protein_apilib.get_protein_list_object(doc)
                #results_dict[key_one][key_two].append(list_obj)
                #results_dict[key_one]["all"].append(list_obj)
                #results.append(list_obj)
                record_type, record_id = "protein", doc["uniprot_canonical_ac"]
                record_name = list_obj["protein_name"]
                canon, ac = record_id, record_id.split("-")[0]
                record_id_list = [canon]
                record_id_list_lower = [canon.lower(), ac.lower()]

                results_dict[key_one]["all"] += record_id_list
                results_dict[key_one][key_two] += record_id_list
                if query_obj["term"].lower() in record_id_list_lower:
                    if record_id not in seen_exact_match:
                        exact_obj = {"id":record_id, "type":record_type, "name":record_name}
                        res_obj["exact_match"].append(exact_obj)
                        seen_exact_match[record_id] = True 
            elif target_collection == "c_glycan":
                list_obj = get_glycan_list_record(doc)
                #results_dict[key_one]["all"].append(list_obj)
                #results.append(list_obj)
                #results_dict[key_one][key_two].append(list_obj)
                record_type, record_id = "glycan", doc["glytoucan_ac"]
                record_name = record_id
                record_id_list = [record_id]
                record_id_list_lower = [record_id.lower()]
                results_dict[key_one]["all"].append(record_id)
                results_dict[key_one][key_two].append(record_id)
                if query_obj["term"].lower() in record_id_list_lower:
                    if record_id not in seen_exact_match:
                        exact_obj = {"id":record_id, "type":record_type, "name":record_name}
                        res_obj["exact_match"].append(exact_obj)
                        seen_exact_match[record_id] = True


        if len(results_dict[key_one][key_two]) > 0:
            record_type = key_one
            record_type = "protein" if record_type == "glycoprotein" else record_type
            ts = datetime.datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S %Z%z")
            random_string = util.get_random_string(128)
            hash_obj = hashlib.md5(random_string)
            list_id = hash_obj.hexdigest()
            res = dbh[cache_collection].delete_many({"list_id":list_id})
            result_count = len(results_dict[key_one][key_two])
            partition_count = result_count/config_obj["cache_batch_size"]
            for i in xrange(0,partition_count+1):
                start = i*config_obj["cache_batch_size"]
                end = start + config_obj["cache_batch_size"]
                end = result_count if end > result_count else end
                if start < result_count:
                    results_part = results_dict[key_one][key_two][start:end]
                    cache_info = {
                        "query":query_obj,
                        "ts":ts,
                        "record_type":record_type,
                        "search_type":"search"
                        }
                    util.cache_record_list(dbh,list_id,results_part,cache_info,
                            cache_collection,config_obj)
            #hit_count = len(results_dict[key_one][key_two])
            hit_count = len(set(results_dict[key_one][key_two]))
            res_obj["other_matches"][key_one][key_two] = {
                "list_id":list_id, 
                "count":hit_count
            }
            res_obj["other_matches"]["total_match_count"] += len(results_dict[key_one][key_two])
        else:
            res_obj["other_matches"][key_one][key_two] = {"list_id":"", "count":0}
    


    return res_obj


def get_glycan_list_record(in_obj):

    out_obj = {}
    out_obj["glytoucan_ac"] = in_obj["glytoucan_ac"]
    out_obj["mass"]  = in_obj["mass"] if "mass" in in_obj else -1
    out_obj["mass_pme"]  = in_obj["mass_pme"] if "mass_pme" in in_obj else -1
    n = in_obj["number_monosaccharides"] if "number_monosaccharides" in in_obj else -1    
    out_obj["number_monosaccharides"] = n

    for k in ["mass", "mass_pme", "number_monosaccharides"]:
        if out_obj[k] == -1:
            out_obj.pop(k)



    out_obj["iupac"] = in_obj["iupac"] if "iupac" in in_obj else ""
    out_obj["glycoct"] = in_obj["glycoct"] if "glycoct" in in_obj else ""

    seen = {"uniprot_canonical_ac":{}, "enzyme":{}}
    if "glycoprotein" in in_obj:
        for xobj in in_obj["glycoprotein"]:
            seen["uniprot_canonical_ac"][xobj["uniprot_canonical_ac"].lower()] = True
        
    if "enzyme" in in_obj:
        for xobj in in_obj["enzyme"]:
            seen["enzyme"][xobj["gene"].lower()] = True
    
    out_obj["number_proteins"] = len(seen["uniprot_canonical_ac"].keys())
    out_obj["number_enzymes"] = len(seen["enzyme"].keys()) 

    return out_obj








