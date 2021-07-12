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




def motif_detail(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("motif_detail", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    collection = "c_motif"


    default_hash = {"offset":1, "limit":20, "sort":"glytoucan_ac", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
    
    mongo_query = {}
    if "motif_ac" in query_obj:
        mongo_query = {"motif_ac":{'$eq': query_obj["motif_ac"]}}
    elif "glytoucan_ac" in query_obj:
        mongo_query = {"glytoucan_ac":{'$eq': query_obj["glytoucan_ac"]}}
   
    if mongo_query == {}:
        return {"error_list":[{"error_code":"bad-query"}]}


    motif_doc = dbh[collection].find_one(mongo_query)
    
    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if motif_doc == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}

    
    url = config_obj["urltemplate"]["motif"] % (motif_doc["motif_ac"])
    glytoucan_url = config_obj["urltemplate"]["glytoucan"] % (motif_doc["glytoucan_ac"])
    motif_doc["motif"] = {
        "accession":motif_doc["motif_ac"], 
        "url":url,
        "glytoucan_ac":motif_doc["glytoucan_ac"],
        "glytoucan_url":glytoucan_url
    }

    prop_list = ["motif", "glytoucan","name",  "mass", "publication"]
    prop_list += ["synonym", "crossref","keywords", "reducing_end","aglycon","reducing_end",
        "alignment_method"
    ]

    res_obj = {}
    for k in motif_doc:
        if k in prop_list:
            res_obj[k] = motif_doc[k]

    mongo_query = {"motifs.id": {'$eq': motif_doc["motif_ac"]}}
    doc_list = dbh["c_glycan"].find(mongo_query)
    results = get_parent_glycans(motif_doc["motif_ac"], doc_list, res_obj)

    sorted_id_list = util.sort_objects(results, config_obj["glycan_list"]["returnfields"], 
                                        query_obj["sort"], query_obj["order"])
    #check for post-access error, error_list should be empty upto this line
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(results):
        post_error_list.append({"error_code":"invalid-parameter-value", "field":"offset"})
        return {"error_list":post_error_list}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for i in sorted_id_list[start_index:stop_index]:
        res_obj["results"].append(results[i])

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(results), "sort":query_obj["sort"], "order":query_obj["order"]}
    res_obj["query"] = query_obj

    return util.order_obj(res_obj, config_obj["objectorder"]["glycan"])



def get_parent_glycans(motif_ac, doc_list, res_obj):

    results = []
    for doc in doc_list:
        if "motifs" in doc:
            for o in doc["motifs"]:
                if "name" not in res_obj and o["id"] == motif_ac:
                    res_obj["name"] = o["name"]

        glytoucan_ac = doc["glytoucan_ac"]
        seen = {"uniprot_canonical_ac":{}, "enzyme":{}}
        if "glycoprotein" in doc:
            for o in doc["glycoprotein"]:
                seen["uniprot_canonical_ac"][o["uniprot_canonical_ac"].lower()] = True

        if "enzyme" in doc:
            for o in doc["enzyme"]:
                seen["enzyme"][o["gene"].lower()] = True

        mass = doc["mass"] if "mass" in doc else -1
        number_monosaccharides = doc["number_monosaccharides"] if "number_monosaccharides" in doc else -1
        iupac = doc["iupac"] if "iupac" in doc else ""
        glycoct = doc["glycoct"] if "glycoct" in doc else ""
        results.append({
            "glytoucan_ac":glytoucan_ac
            ,"mass": mass 
            ,"number_monosaccharides": number_monosaccharides
            ,"number_proteins": len(seen["uniprot_canonical_ac"].keys())
            ,"number_enzymes": len(seen["enzyme"].keys()) 
            ,"iupac": iupac
            ,"glycoct": glycoct
        })


    return results







