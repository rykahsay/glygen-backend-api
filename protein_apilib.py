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


def protein_search_init(config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_searchinit",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_searchinit"

    res_obj =  dbh[collection].find_one({})

    return res_obj["protein"]



def protein_search_simple(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_search_simple", query_obj,config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_simple_mongo_query(query_obj)
    #print mongo_query

    collection = "c_protein"
    cache_collection = "c_proteincache"
    
    i = 0
    results = []
    for obj in dbh[collection].find(mongo_query):
        i += 1
        #break, otherwise BSON gets too large
        if i > config_obj["max_results_count"]["protein"]:
            break
        
        uniprot_canonical_ac = obj["uniprot_canonical_ac"]
        mass = -1
        if "mass" in obj:
            if "chemical_mass" in obj["mass"]:
                mass = obj["mass"]["chemical_mass"]
       
        full_name, short_name = "", ""
        if "recommendedname" in obj:
            full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
            short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        refseq_ac, refseq_name = "", ""
        if "refseq" in obj:
            refseq_ac = obj["refseq"]["ac"] if "ac" in obj["refseq"] else ""
            refseq_name = obj["refseq"]["name"] if "name" in obj["refseq"] else ""

        gene_name = ""
        if "gene" in obj:
            if len(obj["gene"]) > 0:
                gene_name = obj["gene"][0]["name"] if "name" in obj["gene"][0] else ""
        
        results.append({
            "uniprot_canonical_ac":uniprot_canonical_ac
            ,"mass": mass 
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":obj["species"][0]["name"]
            ,"refseq_name": refseq_name
            ,"refseq_ac": refseq_ac
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




def protein_search(query_obj, config_obj):


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
    error_list = errorlib.get_errors_in_query("protein_search", query_obj,config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query(query_obj)
    #return mongo_query
    

    collection = "c_protein"
    cache_collection = "c_proteincache"

    results = []
    i = 0
    n = dbh[collection].find(mongo_query).count()
    for obj in dbh[collection].find(mongo_query):
        i += 1
        #break, otherwise BSON gets too large
        if i > config_obj["max_results_count"]["protein"]:
            break

        uniprot_canonical_ac = obj["uniprot_canonical_ac"]
        mass = -1
        if "mass" in obj:
            if "chemical_mass" in obj["mass"]:
                mass = obj["mass"]["chemical_mass"]
       
        full_name, short_name = "", ""
        if "recommendedname" in obj:
            full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
            short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        refseq_ac, refseq_name = "", ""
        if "refseq" in obj:
            refseq_ac = obj["refseq"]["ac"] if "ac" in obj["refseq"] else ""
            refseq_name = obj["refseq"]["name"] if "name" in obj["refseq"] else ""

        gene_name = ""
        if "gene" in obj:
            if len(obj["gene"]) > 0:
                gene_name = obj["gene"][0]["name"] if "name" in obj["gene"][0] else ""
        organism_name = ""
        if "species" in obj:
            if len(obj["species"]) > 0:
                organism_name = obj["species"][0]["name"] if "name" in obj["species"][0] else ""
        
        o = {
            "uniprot_canonical_ac":uniprot_canonical_ac
            ,"mass": mass
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":organism_name
            ,"refseq_name": refseq_name
            ,"refseq_ac": refseq_ac
            ,"hit_score":0
        }
        

        #attach sort order to sort by exact match
        for f in query_obj:
            val_list = [o["uniprot_canonical_ac"].lower(), o["refseq_ac"].lower()]
            val_list += [o["protein_name_long"].lower(),o["protein_name_short"].lower()]
            val_list += [o["gene_name"].lower()]
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


def protein_list(query_obj, config_obj):
     
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_list", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    cache_collection = "c_proteincache"


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

    if query_obj["sort"] == "hit_score":
        sorted_id_list = range(0, len(cached_obj["results"]))
    else:
        sorted_id_list = util.sort_objects(cached_obj["results"], 
                config_obj["protein_list"]["returnfields"],
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

    for ind in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][ind]
        if "hit_score" in obj:
            obj.pop("hit_score")
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]) )

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}

    return res_obj



def protein_alignment(query_obj, config_obj):


    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_alignment", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    collection = "c_cluster"
    mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    obj = dbh[collection].find_one(mongo_query)
    
    selected_cls_id = ""
    for cls_id in obj["clusterlist"]:
        if cls_id.find(query_obj["cluster_type"]) != -1:
            selected_cls_id = cls_id
            break

    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if selected_cls_id == "":
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}


    collection = "c_alignment"
    mongo_query = {"cls_id":selected_cls_id}
    obj = dbh[collection].find_one(mongo_query)

    if obj == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}

    #If the object has a property that is not in the specs, remove it
    remove_prop_list = ["_id"]
    for key in remove_prop_list:
        if key in obj:
            obj.pop(key)

    util.clean_obj(obj)
    new_obj = obj


    return obj






def protein_detail(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_detail", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}


    collection = "c_protein"

    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]
    }
    obj = dbh[collection].find_one(mongo_query)

    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if obj == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}


    url = config_obj["urltemplate"]["uniprot"] % (obj["uniprot_canonical_ac"])
    obj["uniprot_id"] = obj["uniprot_id"] if "uniprot_id" in obj else ""
    obj["uniprot"] = {
        "uniprot_canonical_ac":obj["uniprot_canonical_ac"], 
        "uniprot_id":obj["uniprot_id"],
        "url":url,
        "length": obj["sequence"]["length"]
    }

    #If the object has a property that is not in the specs, remove it
    remove_prop_list = ["uniprot_canonical_ac", "uniprot_ac", "uniprot_id", "_id"]
    for key in remove_prop_list:
        if key in obj:
            obj.pop(key)
    obj["mass"].pop("monoisotopic_mass")


    truncate_go_terms(obj)
    util.clean_obj(obj)

    #return util.order_obj(obj, config_obj["objectorder"]["protein"])
    return obj



def truncate_go_terms(obj):
    
    if "categories" not in obj["go_annotation"]:
        return
    for o in obj["go_annotation"]["categories"]:
        tmp_list = []
        o["go_terms"] = sorted(o["go_terms"], key = lambda i: i['name'].lower())
        n = 0
        for t in o["go_terms"]:
            n += 1
            if n > 5:
                break
            tmp_list.append(t)
        o["go_terms"] = tmp_list
       
    return




def get_simple_mongo_query(query_obj):


    #protein: uniprot_canonical_ac, gene, recommendedName,function
    #glycan:glycosylation
    #organism:species
    #disease:disease
    #pathway:pathway

    query_term = "\"%s\"" % (query_obj["term"])

    cond_objs = []
    if query_obj["term_category"] == "any":
        return {'$text': { '$search': query_term}}
    elif query_obj["term_category"] == "glycan":
        cond_objs.append({"glycosylation.glytoucan_ac":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "protein":
        cond_objs.append({"uniprot_canonical_ac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"gene.name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"recommendedName.full":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"recommendedName.short":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"function.annotation":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "disease":
        cond_objs.append({"disease.name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"disease.doid":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"disease.icd10":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "pathway":
        cond_objs.append({"pathway.id":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"pathway.name":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "organism":
        cond_objs.append({"species.name":{'$regex': query_obj["term"], '$options': 'i'}})

    mongo_query = {} if cond_objs == [] else { "$or": cond_objs }

    return mongo_query



def get_mongo_query(query_obj):

                        

    cond_objs = []
    #glytoucan_ac
    if "uniprot_canonical_ac" in query_obj:
        qid_list = query_obj["uniprot_canonical_ac"].split(",")
        cond_objs.append(
            {
                "$or":[
                    {"uniprot_canonical_ac":{'$in': qid_list}},
                    {"uniprot_ac":{'$in': qid_list}}
                ]
            }
        )

    #protein_name
    if "protein_name" in query_obj:
        query_obj["protein_name"] = query_obj["protein_name"].replace("(", "\(").replace(")", "\)")
        query_obj["protein_name"] = query_obj["protein_name"].replace("[", "\[").replace("]", "\]")
        cond_objs.append({"recommendedname.full":{'$regex': query_obj["protein_name"], '$options': 'i'}})

    #go_id
    if "go_id" in query_obj:
        q = {"go_annotation.categories.go_terms.id":{'$regex': query_obj["go_id"], '$options': 'i'}}
        cond_objs.append(q)
    
    #go_term
    if "go_term" in query_obj:
        q = {"go_annotation.categories.go_terms.name":{'$regex': query_obj["go_term"], '$options': 'i'}}
        cond_objs.append(q)

    #refseq_ac
    if "refseq_ac" in query_obj:
        cond_objs.append({"refseq.ac":{'$regex': query_obj["refseq_ac"], '$options': 'i'}})

    #mass
    if "mass" in query_obj:
        if "min" in query_obj["mass"]:
            cond_objs.append({"mass.chemical_mass":{'$gte': query_obj["mass"]["min"]}})
        if "max" in query_obj["mass"]:
            cond_objs.append({"mass.chemical_mass":{'$lte': query_obj["mass"]["max"]}})
    
    #organism
    if "organism" in query_obj:
        if "id" in query_obj["organism"]:
            if query_obj["organism"]["id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["organism"]["id"]}})

    #gene_name
    if "gene_name" in query_obj:
        cond_objs.append({"gene.name" : {'$regex': query_obj["gene_name"], '$options': 'i'}})

    #pathway_id
    if "pathway_id" in query_obj:
        cond_objs.append({"pathway.id" : {'$regex': query_obj["pathway_id"], '$options': 'i'}})

    #pmid
    if "pmid" in query_obj:
        cond_objs.append({"publication.pmid" : {'$regex': query_obj["pmid"], '$options': 'i'}})

    #glycan
    if "glycan" in query_obj:
        if "glytoucan_ac" in query_obj["glycan"]:
            and_list = []
            q_one = {
                "glycosylation.glytoucan_ac":
                    {'$regex':query_obj["glycan"]["glytoucan_ac"],'$options':'i'}
            }
            q_two = {"glycosylation.relation":{'$eq':query_obj["glycan"]["relation"]}}
            if query_obj["glycan"]["relation"] == "any":
                and_list = [q_one]
            elif query_obj["glycan"]["relation"] in ["attached", "binding"]:
                and_list = [q_one, q_two]
            cond_objs.append({'$and':and_list})

    #glycosylation_evidence
    if "glycosylation_evidence" in query_obj:
        if query_obj["glycosylation_evidence"] == "predicted":
            cond_objs.append({"glycosylation": {'$gt':[]}})
            cond_objs.append({"glycosylation.evidence.database": {'$ne':"UniCarbKB"}})
            cond_objs.append({"glycosylation.evidence.database": {'$ne':"PDB"}})
            cond_objs.append({"glycosylation.evidence.database": {'$ne':"PubMed"}})
        elif query_obj["glycosylation_evidence"] == "reported":
            or_list = [
                {"glycosylation.evidence.database": {'$eq':"UniCarbKB"}}
                ,{"glycosylation.evidence.database": {'$eq':"PubMed"}}
                ,{"glycosylation.evidence.database": {'$eq':"PDB"}}
            ]
            cond_objs.append({'$or':or_list})
        elif query_obj["glycosylation_evidence"] == "both":
            cond_objs.append({"glycosylation": {'$gt': []}})

    aa_map = {
        "A":"Ala",
        "R":"Arg",
        "N":"Asn",
        "D":"Asp",
        "C":"Cys",
        "E":"Glu",
        "Q":"Gln",
        "G":"Gly",
        "H":"His",
        "I":"Ile",
        "L":"Leu",
        "K":"Lys",
        "M":"Met",
        "F":"Phe",
        "P":"Pro",
        "S":"Ser",
        "T":"Thr",
        "W":"Trp",
        "Y":"Tyr",
        "V":"Val"
    }
    
    #glycosylated_aa
    if "glycosylated_aa" in query_obj:
        if "aa_list" in query_obj["glycosylated_aa"]:
            obj_list = []
            for aa in query_obj["glycosylated_aa"]["aa_list"]:
                aa_three = aa_map[aa] if aa in aa_map else aa
                obj_list.append({"glycosylation.residue": {'$eq': aa_three}})
            if obj_list != []:
                operation = query_obj["glycosylated_aa"]["operation"]
                cond_objs.append({"$"+operation+"":obj_list})


    #sequence
    if "sequence" in query_obj:
        if "aa_sequence" in query_obj["sequence"]:
            cond_objs.append({"sequence.sequence": {'$regex': query_obj["sequence"]["aa_sequence"],
                                                        '$options': 'i'}})
        #if "type" in query_obj["sequence"]:
        #    cond_objs.append({"sequence.type": {'$regex': query_obj["sequence"]["type"],
        #                                            '$options': 'i'}})


    operation = query_obj["operation"].lower() if "operation" in query_obj else "and"
    mongo_query = {} if cond_objs == [] else { "$"+operation+"": cond_objs }
       
    return mongo_query














