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


def glycan_search_init(config_obj):
   
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    error_list = errorlib.get_errors_in_query("glycan_searchinit",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    collection = "c_searchinit"
    res_obj =  dbh[collection].find_one({})

    return res_obj["glycan"]



def glycan_search_simple(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_search_simple", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    mongo_query = get_simple_mongo_query(query_obj)
    #print mongo_query

    collection = "c_glycan"
    cache_collection = "c_glycancache"
    i = 0
    results = []
    for obj in dbh[collection].find(mongo_query):
        i += 1
        #break, otherwise BSON gets too large
        if i > config_obj["max_results_count"]["glycan"]:
            break
        obj = json.loads(json_util.dumps(obj))
        glytoucan_ac = obj["glytoucan_ac"]
        
        fobj = {}
        for key in obj:
            if type(obj[key]) is list and len(obj[key]) > 0:
                fobj[key] = obj[key]
            elif isinstance(obj[key], basestring) and obj[key].strip() != "":
                fobj[key] = obj[key]
        #results[glytoucan_ac] = fobj
        seen = {"uniprot_canonical_ac":{}, "enzyme":{}}
        if "glycoprotein" in obj:
            for xobj in obj["glycoprotein"]:
                seen["uniprot_canonical_ac"][xobj["uniprot_canonical_ac"].lower()] = True
        
        if "enzyme" in obj:
            for xobj in obj["enzyme"]:
                seen["enzyme"][xobj["gene"].lower()] = True

        mass = obj["mass"] if "mass" in obj else -1
        mass_pme = obj["mass_pme"] if "mass_pme" in obj else -1

        number_monosaccharides = obj["number_monosaccharides"] if "number_monosaccharides" in obj else -1
        iupac = obj["iupac"] if "iupac" in obj else ""
        glycoct = obj["glycoct"] if "glycoct" in obj else ""

        results.append({
            "glytoucan_ac":glytoucan_ac
            ,"mass": mass 
            ,"mass_pme": mass_pme
            ,"number_monosaccharides": number_monosaccharides
            ,"number_proteins": len(seen["uniprot_canonical_ac"].keys()) 
            ,"number_enzymes": len(seen["enzyme"].keys()) 
            ,"iupac": iupac
            ,"glycoct": glycoct
        })




    res_obj = {}
    if len(results) == 0:
        res_obj = {"list_id":""}
    else:
        ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        hash_obj = hashlib.md5(json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
    
        res = dbh[cache_collection].delete_many({"list_id":list_id})
        result_count = len(results)
        partition_count = result_count/config_obj["cache_batch_size"]
        for i in xrange(0,partition_count+1):
            start = i*config_obj["cache_batch_size"]
            end = start + config_obj["cache_batch_size"]
            end = result_count if end > result_count else end
            if start < result_count:
                results_part = results[start:end]
                search_results_obj = {}
                search_results_obj["list_id"] = list_id
                search_results_obj["query"] = query_obj
                search_results_obj["query"]["execution_time"] = ts
                search_results_obj["results"] = results_part
                res = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id


    return res_obj




def glycan_search(query_obj, config_obj):

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
    error_list = errorlib.get_errors_in_query("glycan_search", query_obj, config_obj)
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
        


    mongo_query = get_mongo_query(query_obj)
    #return mongo_query
    
    collection = "c_glycan"
    cache_collection = "c_glycancache"
    
    i = 0
    results = []
    for obj in dbh[collection].find(mongo_query):
        i += 1

        #break, otherwise BSON gets too large
        
        if i > config_obj["max_results_count"]["glycan"]:
            break
        obj = json.loads(json_util.dumps(obj))
        glytoucan_ac = obj["glytoucan_ac"]
        if "composition" in query_obj:
            if query_obj["composition"] != []:
                if passes_composition_filter(obj["composition"], query_obj) == False:
                    continue
        fobj = {}
	for key in obj:
            if type(obj[key]) is list and len(obj[key]) > 0:
                fobj[key] = obj[key]
            elif isinstance(obj[key], basestring) and obj[key].strip() != "":
                fobj[key] = obj[key]
        #results[glytoucan_ac] = fobj
        seen = {"uniprot_canonical_ac":{}, "enzyme":{}}
        if "glycoprotein" in obj:
            for xobj in obj["glycoprotein"]:
                seen["uniprot_canonical_ac"][xobj["uniprot_canonical_ac"].lower()] = True
        
        if "enzyme" in obj:
            for xobj in obj["enzyme"]:
                seen["enzyme"][xobj["gene"].lower()] = True

        mass = obj["mass"] if "mass" in obj else -1
        mass_pme = obj["mass_pme"] if "mass_pme" in obj else -1

        number_monosaccharides = obj["number_monosaccharides"] if "number_monosaccharides" in obj else -1
        iupac = obj["iupac"] if "iupac" in obj else ""
        glycoct = obj["glycoct"] if "glycoct" in obj else ""

        o = {
            "glytoucan_ac":glytoucan_ac
            ,"mass": mass 
            ,"mass_pme": mass_pme
            ,"number_monosaccharides": number_monosaccharides
            ,"number_proteins": len(seen["uniprot_canonical_ac"].keys()) 
            ,"number_enzymes": len(seen["enzyme"].keys()) 
            ,"iupac": iupac
            ,"glycoct": glycoct
            ,"hit_score":0
        }

        #attach sort order to sort by exact match
        for f in query_obj:
            val_list = [o["glytoucan_ac"].lower(), o["iupac"].lower()]
            val_list += [o["glycoct"].lower()]
            if type(query_obj[f]) is unicode:
                if query_obj[f].lower() in val_list:
                    o["hit_score"] = 1
        results.append(o)

    #sort results by hit_score
    results = sorted(results, key=lambda x: x["hit_score"], reverse=True)

    res_obj = {}
    if len(results) == 0:
        res_obj = {"list_id":""}
    else:
        ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
        hash_obj = hashlib.md5(json.dumps(query_obj))
        list_id = hash_obj.hexdigest()
        

        res = dbh[cache_collection].delete_many({"list_id":list_id})
        result_count = len(results)
        partition_count = result_count/config_obj["cache_batch_size"]
        for i in xrange(0,partition_count+1):
            start = i*config_obj["cache_batch_size"]
            end = start + config_obj["cache_batch_size"]
            end = result_count if end > result_count else end
            if start < result_count:
                results_part = results[start:end]
                search_results_obj = {}
                search_results_obj["list_id"] = list_id
                search_results_obj["query"] = query_obj
                search_results_obj["query"]["execution_time"] = ts
                search_results_obj["results"] = results_part
                res = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id


    return res_obj


def glycan_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_list", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    cache_collection = "c_glycancache"

    res_obj = {}
    default_hash = {"offset":1, "limit":20, "sort":"hit_score", "order":"desc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]


    #Get cached object
    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    cached_obj["results"] = []
    for doc in dbh[cache_collection].find({"list_id":query_obj["id"]}):
        cached_obj["results"] += doc["results"]


    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if cached_obj == None:
        post_error_list.append({"error_code":"non-existent-search-results"})
        return {"error_list":post_error_list}
    

    sorted_id_list = util.sort_objects(cached_obj["results"], config_obj["glycan_list"]["returnfields"],
                                        query_obj["sort"], query_obj["order"])
    res_obj = {"query":cached_obj["query"]}

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
        if "hit_score" in obj:
            obj.pop("hit_score")
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["glycan"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj




def glycan_detail(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("glycan_detail", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    collection = "c_glycan"

    mongo_query = {"glytoucan_ac":{'$eq': query_obj["glytoucan_ac"]}}
    obj = dbh[collection].find_one(mongo_query)
    
    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if obj == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}

    keys_to_remove = ["_id", "number_monosaccharides"]
    for key in keys_to_remove:
        if key in obj:
            obj.pop(key)

    url = config_obj["urltemplate"]["glytoucan"] % (obj["glytoucan_ac"])
    obj["glytoucan"] = {"glytoucan_ac":obj["glytoucan_ac"], "glytoucan_url":url}
    obj.pop("glytoucan_ac")

    #Remove 0 count residues
    tmp_list = []
    for o in obj["composition"]:
        if o["count"] > 0:
            tmp_list.append(o)
    obj["composition"] = tmp_list

    util.clean_obj(obj)

    return util.order_obj(obj, config_obj["objectorder"]["glycan"])


def glycan_image(query_obj, path_obj):

        img_file = path_obj["glycanimagespath"] +   query_obj["glytoucan_ac"].upper() +".png"
        if os.path.isfile(img_file) == False:
            img_file = path_obj["glycanimagespath"] +  "G0000000.png"
        return img_file




def get_simple_mongo_query(query_obj):


    query_term = "\"%s\"" % (query_obj["term"])

    cond_objs = []
    if query_obj["term_category"] == "any":
        return {'$text': { '$search': query_term}}
    elif query_obj["term_category"] == "glycan":
        cond_objs.append({"glytoucan_ac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"iupac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"wurcs":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"glycoct":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "protein":
        cond_objs.append({"glycoprotein.uniprot_canonical_ac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"glycoprotein.protein_name":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "enzyme":
        cond_objs.append({"enzyme.uniprot_canonical_ac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"enzyme.protein_name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"enzyme.gene":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "organism":
        cond_objs.append({"species.name":{'$regex': query_obj["term"], '$options': 'i'}})
    
    
    mongo_query = {} if cond_objs == [] else { "$or": cond_objs }
    return mongo_query





def get_mongo_query(query_obj):

    cond_objs = []
    #glytoucan_ac
    if "glytoucan_ac" in query_obj:
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("[", "\\[")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("]", "\\]")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("(", "\\(")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace(")", "\\)")
        qid_list = query_obj["glytoucan_ac"].split(",")
        qval = "^%s$" % (query_obj["glytoucan_ac"])
        cond_objs.append(
            {
                "$or":[
                    {"glytoucan_ac":{"$in": qid_list}},
                    {"crossref.id":{"$in": qid_list}}
                ]
            }
        )

    #mass
    if "mass" in query_obj:
        mass_field = "mass_pme" if query_obj["mass_type"].lower() != "native" else "mass"
        if "min" in query_obj["mass"]:
            cond_objs.append({mass_field:{'$gte': query_obj["mass"]["min"]}})
        if "max" in query_obj["mass"]:
            cond_objs.append({mass_field:{'$lte': query_obj["mass"]["max"]}})
    
    #number_monosaccharides
    if "number_monosaccharides" in query_obj:
        if "min" in query_obj["number_monosaccharides"]:
            cond_objs.append({"number_monosaccharides":{'$gte': query_obj["number_monosaccharides"]["min"]}})
        if "max" in query_obj["number_monosaccharides"]:
            cond_objs.append({"number_monosaccharides":{'$lte': query_obj["number_monosaccharides"]["max"]}})

    #organism
    if "organism" in query_obj:
        if "organism_list" in query_obj["organism"]:
            obj_list = []
            for o in query_obj["organism"]["organism_list"]:
                tax_id = o["id"]
                if tax_id > 0:
                    obj_list.append({"species.taxid": {'$eq': tax_id}})
            if obj_list != []:
                operation = query_obj["organism"]["operation"]
                cond_objs.append({"$"+operation+"":obj_list})



    #protein_identifier
    if "protein_identifier" in query_obj:
        cond_objs.append(
            {"$or":[
                {"glycoprotein.uniprot_canonical_ac": {'$regex': query_obj["protein_identifier"], '$options': 'i'}},
                {"glycoprotein.gene_name": {'$regex': query_obj["protein_identifier"], '$options': 'i'}}
                ]
            }
        )
    #glycan_motif
    if "glycan_motif" in query_obj:
        cond_objs.append({"motifs.name": {'$regex': query_obj["glycan_motif"], '$options': 'i'}}) 

    #glycan_type 
    if "glycan_type" in query_obj:
        cond_objs.append({"classification.type.name": {'$regex': query_obj["glycan_type"], '$options': 'i'}})
     
    #pmid
    if "pmid" in query_obj:
        cond_objs.append({"publication.pmid" : {'$regex': query_obj["pmid"], '$options': 'i'}})


    #glycan_subtype
    if "glycan_subtype" in query_obj:
        cond_objs.append({"classification.subtype.name": {'$regex': query_obj["glycan_subtype"], 
                                                            '$options': 'i'}})
    #enzyme
    if "enzyme" in query_obj:
        if "id" in query_obj["enzyme"]:
            cond_objs.append(
                {"$or":[
                        {"enzyme.gene": {'$regex': query_obj["enzyme"]["id"], '$options': 'i'}},
                        {"enzyme.uniprot_canonical_ac": {'$regex': query_obj["enzyme"]["id"], '$options': 'i'}}
                    ]
                })



    if "composition" in query_obj:
        for o in query_obj["composition"]:
            cond_objs.append({"composition.residue": {'$eq': o["residue"]}})
            #if o["max"] > 0:
            #    cond_objs.append({"composition.residue": {'$eq': o["residue"]}})
            #else:
            #    cond_objs.append({"composition.residue": {'$ne': o["residue"]}})

    operation = query_obj["operation"].lower() if "operation" in query_obj else "and"
    mongo_query = {} if cond_objs == [] else { "$"+operation+"": cond_objs }

    return mongo_query










def passes_composition_filter(comp_obj, query_obj):


    tv = []
    n_cond = 0
    for q in query_obj["composition"]:
        q_res, q_min, q_max = q["residue"], q["min"], q["max"]
        if q_max >= 0:
            n_cond += 1
            for o in comp_obj:
                o_res, o_count = o["residue"], o["count"]
                if o_res == q_res and o_count >= q_min and o_count <= q_max:
                    tv.append(True)
                    break
    
    return len(tv) == n_cond and list(set(tv)) == [True]


