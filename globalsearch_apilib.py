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
            return {"error_list":[{"error_code":"invalid-globalsearch_query"}]}


    #Filter cached global search results
    res_obj = {
        "exact_match": [],
        "other_matches": {"total_match_count":0}
    }
    seen_exact_match = {}
    for obj in search_obj:
        target_collection = obj["targetcollection"]
        cache_collection = obj["cachecollection"]
        results = []
        for doc in dbh[target_collection].find(obj["mongoquery"]):
            doc.pop("_id")
            record_type, record_id, record_name = "", "", ""
            if cache_collection == "c_proteincache":
                list_obj = get_protein_list_record(doc)
                results.append(list_obj)
                record_type, record_id = "protein", doc["uniprot_canonical_ac"]
                record_name = list_obj["protein_name_long"]
            else:
                list_obj = get_glycan_list_record(doc)
                results.append(list_obj)
                record_type, record_id = "glycan", doc["glytoucan_ac"]
                record_name = record_id
            if record_id not in seen_exact_match and query_obj["term"].lower() == record_id.lower():
                exact_obj = {"id":record_id, "type":record_type, "name":record_name}
                res_obj["exact_match"].append(exact_obj)
                seen_exact_match[record_id] = True

        key_one, key_two = obj["searchname"].split(".")
        if key_one not in res_obj["other_matches"]:
            res_obj["other_matches"][key_one] = {key_two:{}}

        if len(results) > 0:
            ts = datetime.datetime.now(pytz.timezone("US/Eastern")).strftime("%Y-%m-%d %H:%M:%S %Z%z")
            random_string = util.get_random_string(128)
            hash_obj = hashlib.md5(random_string)
            list_id = hash_obj.hexdigest()
            search_results_obj = {}
            search_results_obj["list_id"] = list_id
            search_results_obj["query"] = query_obj
            search_results_obj["query"]["execution_time"] = ts
            search_results_obj["results"] = results
            result = dbh[cache_collection].delete_many({"list_id":list_id})
            result = dbh[cache_collection].insert_one(search_results_obj)
            res_obj["other_matches"][key_one][key_two] = {"list_id":list_id, "count":len(results)}
            res_obj["other_matches"]["total_match_count"] += len(results)
        else:
            res_obj["other_matches"][key_one][key_two] = {"list_id":"", "count":0}
    


    return res_obj


def get_glycan_list_record(in_obj):

    out_obj = {}
    out_obj["glytoucan_ac"] = in_obj["glytoucan_ac"]
    out_obj["mass"]  = in_obj["mass"] if "mass" in in_obj else -1
    n = in_obj["number_monosaccharides"] if "number_monosaccharides" in in_obj else -1    
    out_obj["number_monosaccharides"] = n

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





def get_protein_list_record(in_obj):



    out_obj = {}
    out_obj["uniprot_canonical_ac"] = in_obj["uniprot_canonical_ac"]
    out_obj["mass"] = -1
    if "mass" in in_obj:
        if "chemical_mass" in in_obj["mass"]:
            out_obj["mass"] = in_obj["mass"]["chemical_mass"]
    
    out_obj["protein_name_long"], out_obj["protein_name_long"] = "", ""
    if "recommendedname" in in_obj:
        full_name = in_obj["recommendedname"]["full"] if "full" in in_obj["recommendedname"] else ""
        short_name = in_obj["recommendedname"]["short"] if "short" in in_obj["recommendedname"] else ""
        out_obj["protein_name_long"] = full_name
        out_obj["protein_name_short"] = short_name
    
    out_obj["refseq_ac"], out_obj["refseq_name"] = "", ""
    if "refseq" in in_obj:
        out_obj["refseq_ac"] = in_obj["refseq"]["ac"] if "ac" in in_obj["refseq"] else ""
        out_obj["refseq_name"] = in_obj["refseq"]["name"] if "name" in in_obj["refseq"] else ""
    
    out_obj["gene_name"] = ""
    if "gene" in in_obj:
        if len(in_obj["gene"]) > 0:
            out_obj["gene_name"] = in_obj["gene"][0]["name"] if "name" in in_obj["gene"][0] else ""
    
    out_obj["organism"] = ""
    if "species" in in_obj:
        if len(in_obj["species"]) > 0:
            out_obj["organism"] = in_obj["species"][0]["name"] if "name" in in_obj["species"][0] else ""

    return out_obj




