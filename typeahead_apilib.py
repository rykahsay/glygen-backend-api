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


def global_typeahead(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("global_typeahead",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    path_dict = {
        "protein":{
            "uniprot_canonical_ac":{
                "type":"string"
            },
            "uniprot_id":{
                "type":"string"
            },
            "crossref.id":{
                "type":"objlist"
            },
            "protein_names.name":{
                "type":"objlist"
            },
            "gene_names.name":{
                "type":"objlist"
            },
            "refseq.ac":{
                "type":"objlist"
            },
            "publication.reference.id":{
                "type":"objlistobjlist"
            },
            "disease.synonyms.name":{
                "type":"objlistobjlist"
            },
            "disease.recommended_name.name":{
                "type":"objlist"
            },
            "go_annotation.categories.go_terms.id":{
                "type":"goterms"
            },
            "go_annotation.categories.go_terms.name":{
                "type":"goterms"
            }
        },
        "glycan":{
            "glytoucan_ac":{
                "type":"string"
            },
            "crossref.id":{
                "type":"objlist"
            },
            "enzyme.uniprot_canonical_ac":{
                "type":"objlist"
            },
            "enzyme.gene":{
                "type":"objlist"
            },
            "motifs.name":{
                "type":"objlist"
            },
            "publication.reference.id":{
                "type":"objlistobjlist"
            }
        }
    }
   
    record_type_list = path_dict.keys()
    if "target" in query_obj:
        if query_obj["target"] in path_dict:
            record_type_list = [query_obj["target"]]


    res_obj = []
    for record_type in record_type_list:
        for path in path_dict[record_type]:
            prop_list = path.split(".")
            path_obj = path_dict[record_type][path]
            mongo_query = {path:{'$regex': query_obj["value"], '$options': 'i'}}
            prj_obj = {prop_list[0]:1}
            coll = "c_" + record_type
            for doc in dbh[coll].find(mongo_query, prj_obj):
                if path_obj["type"] == "string":
                    val = doc[prop_list[0]]
                    if val.lower().find(query_obj["value"].lower()) != -1:
                        if val not in res_obj:
                            res_obj.append(val)
                            if len(res_obj) >= query_obj["limit"]:
                                return sorted(res_obj)
                elif path_obj["type"] == "objlist":
                    for o in doc[prop_list[0]]:
                        val = o[prop_list[1]]
                        if path == "gene_names.name":
                            for val in o[prop_list[1]].split(";"):
                                val = val.replace(".", "").strip() 
                                if val.lower().find(query_obj["value"].lower()) != -1:
                                    if val not in res_obj:
                                        res_obj.append(val)
                                        if len(res_obj) >= query_obj["limit"]:
                                            return sorted(res_obj)
                        else:
                            val = o[prop_list[1]]
                            if len(prop_list) == 3:
                                val = o[prop_list[1]][prop_list[2]]
                            if val.lower().find(query_obj["value"].lower()) != -1:
                                if val not in res_obj:
                                    res_obj.append(val)
                                    if len(res_obj) >= query_obj["limit"]:
                                        return sorted(res_obj)
                elif path_obj["type"] == "objlistobjlist":
                    for o in doc[prop_list[0]]:
                        for oo in o[prop_list[1]]:
                            val = oo[prop_list[2]]
                            if val.lower().find(query_obj["value"].lower()) != -1:
                                if val not in res_obj:
                                    res_obj.append(val)
                                    if len(res_obj) >= query_obj["limit"]:
                                        return sorted(res_obj)
                elif path_obj["type"] == "goterms":
                    for cat_obj in doc["go_annotation"]["categories"]:
                        for term_obj in cat_obj["go_terms"]:
                            val = term_obj[prop_list[-1]]
                            if val.lower().find(query_obj["value"].lower()) != -1:
                                if val not in res_obj:
                                    res_obj.append(val)
                                    if len(res_obj) >= query_obj["limit"]:
                                        return sorted(res_obj)


    return sorted(set(res_obj))



def glycan_typeahead(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("typeahead_glycan",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    collection = "c_glycan"


    res_obj = []
    mongo_query = {}
    if query_obj["field"] == "glytoucan_ac":
        cond_list = [
            {"glytoucan_ac":{'$regex': query_obj["value"], '$options': 'i'}},
            {"crossref.id":{"$regex": query_obj["value"], "$options":"i"}}
        ]
        mongo_query = { "$or":cond_list}
        prj_obj = {"glytoucan_ac":1, "crossref":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            val = obj["glytoucan_ac"]
            if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                res_obj.append(val)
                if len(res_obj) >= query_obj["limit"]:
                    return sorted(res_obj)
            for o in obj["crossref"]:
                val = o["id"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] == "enzyme":
        cond_list = [
            {"enzyme.uniprot_canonical_ac": {'$regex': query_obj["value"], '$options': 'i'}},
            {"enzyme.gene": {'$regex': query_obj["value"], '$options': 'i'}},
        ]
        mongo_query = { "$or":cond_list}
        prj_obj = {"enzyme":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for o in obj["enzyme"]:
                for val in [o["uniprot_canonical_ac"], o["gene"]]:
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)
    elif query_obj["field"] == "enzyme_uniprot_canonical_ac":
        mongo_query = {"enzyme.uniprot_canonical_ac": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"enzyme":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for o in obj["enzyme"]:
                val = o["uniprot_canonical_ac"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] == "motif_name":
        mongo_query = {"motifs.name": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"motifs":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for o in obj["motifs"]:
                val = o["name"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] ==  "glycan_pmid":
        mongo_query = {"publication.reference.id": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"publication":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for o in obj["publication"]:
                for oo in o["reference"]:
                    val = oo["id"]
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)

        
    return sorted(set(res_obj))



def protein_typeahead(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("typeahead_protein",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
  
    collection = "c_protein"


    res_obj = []
    mongo_query = {}
    if query_obj["field"] == "uniprot_canonical_ac":
        mongo_query = {
            "$or":[
                {"uniprot_canonical_ac":{'$regex': query_obj["value"], '$options': 'i'}},
                {"uniprot_id":{'$regex': query_obj["value"], '$options': 'i'}}
            ]
        }
        prj_obj = {"uniprot_canonical_ac":1, "uniprot_id":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            val = obj["uniprot_canonical_ac"]
            if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                res_obj.append(val)
                if len(res_obj) >= query_obj["limit"]:
                    return sorted(res_obj)
            val = obj["uniprot_id"]
            if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                res_obj.append(val)
                if len(res_obj) >= query_obj["limit"]:
                    return sorted(res_obj)
    if query_obj["field"] == "go_id":
        q_obj = {'$regex': query_obj["value"], '$options': 'i'}
        mongo_query = {"go_annotation.categories.go_terms.id":q_obj}
        prj_obj = {"go_annotation":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for cat_obj in obj["go_annotation"]["categories"]:
                for term_obj in cat_obj["go_terms"]:
                    val = term_obj["id"]
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)
    if query_obj["field"] == "go_term":
        q_obj = {'$regex': query_obj["value"], '$options': 'i'}
        mongo_query = {"go_annotation.categories.go_terms.name":q_obj}
        prj_obj = {"go_annotation":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for cat_obj in obj["go_annotation"]["categories"]:
                for term_obj in cat_obj["go_terms"]:
                    val = term_obj["name"]
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)
    if query_obj["field"] == "uniprot_id":
        mongo_query = {"uniprot_id":{'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"uniprot_id":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            val = obj["uniprot_id"]
            if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                res_obj.append(val)
                if len(res_obj) >= query_obj["limit"]:
                    return sorted(res_obj)
    if query_obj["field"] == "refseq_ac":
        mongo_query = {"refseq.ac":{'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"refseq":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            val = obj["refseq"]["ac"] if "ac" in obj["refseq"] else ""
            if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                res_obj.append(val)
                if len(res_obj) >= query_obj["limit"]:
                    return sorted(res_obj)
    elif query_obj["field"] == "gene_name":
        mongo_query = {"gene_names.name": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"gene":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["gene"]:
                if o["name"].lower().find(query_obj["value"].lower()) != -1:
                    for name_part in o["name"].split(";"):
                        val = name_part.replace(".", "").strip()
                        if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                            res_obj.append(val)
                            if len(res_obj) >= query_obj["limit"]:
                                return sorted(res_obj)
    elif query_obj["field"] == "protein_name":
        mongo_query = {"protein_names.name": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"protein_names":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["protein_names"]:
                val = o["name"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] == "disease_name":
        mongo_query = {
            "$or":[
            {"disease.recommended_name.name": {'$regex': query_obj["value"], '$options': 'i'}}
            ,{"disease.synonyms.name": {'$regex': query_obj["value"], '$options': 'i'}}
            ]
        }
        prj_obj = {"disease":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["disease"]:
                val_list = []
                if "recommended_name" in o:
                    val_list.append(o["recommended_name"]["name"])
                if "synonyms" in o:
                    for oo in o["synonyms"]:
                        val_list.append(oo["name"])
                for val in val_list:
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        val = val.split("[")[0]
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)
    elif query_obj["field"] == "disease_id":
        mongo_query = {
            "$or":[
            {"disease.recommended_name.id": {'$regex': query_obj["value"], '$options': 'i'}}
            ,{"disease.synonyms.id": {'$regex': query_obj["value"], '$options': 'i'}}
            ]
        }
        prj_obj = {"disease":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["disease"]:
                val_list = []
                if "recommended_name" in o:
                    val_list.append(o["recommended_name"]["id"])
                if "synonyms" in o:
                    for oo in o["synonyms"]:
                        val_list.append(oo["id"])
                for val in val_list:
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        val = val.split("[")[0]
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj)
    elif query_obj["field"] == "pathway_name":
        mongo_query = {"pathway.name": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"pathway":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["pathway"]:
                val = o["name"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] == "pathway_id":
        mongo_query = {"pathway.id": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"pathway":1}
        for obj in dbh[collection].find(mongo_query,prj_obj):
            for o in obj["pathway"]:
                val = o["id"]
                if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                    res_obj.append(val)
                    if len(res_obj) >= query_obj["limit"]:
                        return sorted(res_obj)
    elif query_obj["field"] ==  "protein_pmid":
        mongo_query = {"publication.reference.id": {'$regex': query_obj["value"], '$options': 'i'}}
        prj_obj = {"publication":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for o in obj["publication"]:
                for oo in o["reference"]:
                    val = oo["id"]
                    if val.lower().find(query_obj["value"].lower()) != -1 and val not in res_obj:
                        res_obj.append(val)
                        if len(res_obj) >= query_obj["limit"]:
                            return sorted(res_obj) 
    
    return sorted(set(res_obj))




def categorized_typeahead(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("categorized_typeahead",query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
  
    collection = "c_protein"

    mongo_query = {}
    if query_obj["field"] == "go_term":
        mongo_query = {"go_annotation.categories.go_terms.name":{'$regex': query_obj["value"], '$options': 'i'}}
        hit_dict = {}
        seen = {}
        total = 0
        limit_one = query_obj["total_limit"]
        limit_two = query_obj["categorywise_limit"]

        prj_obj = {"go_annotation":1}
        for obj in dbh[collection].find(mongo_query, prj_obj):
            for cat_obj in obj["go_annotation"]["categories"]:
                cat = cat_obj["name"]
                for term_obj in cat_obj["go_terms"]:
                    term = term_obj["name"]
                    if term.lower().find(query_obj["value"].lower()) != -1:
                        if cat not in hit_dict:
                            hit_dict[cat] = []
                            seen[cat] = {}
                        if term not in seen[cat] and len(hit_dict[cat]) < limit_two:
                            o = {"label":term, "category":cat}
                            hit_dict[cat].append(o)
                            seen[cat][term] = True
                            total += 1
                        if total >= limit_one:
                            break
    res_obj = []
    for cat in hit_dict:
        for o in hit_dict[cat]:
            res_obj.append(o)

    return res_obj




