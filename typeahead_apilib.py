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
        for obj in dbh[collection].find(mongo_query):
            if obj["glytoucan_ac"].lower().find(query_obj["value"].lower()) != -1:
                res_obj.append(obj["glytoucan_ac"])
            for o in obj["crossref"]:
                if o["id"].lower().find(query_obj["value"].lower()) != -1:
                    res_obj.append(o["id"])
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
        mongo_query = {"uniprot_canonical_ac":{'$regex': query_obj["value"], '$options': 'i'}}
        for obj in dbh[collection].find(mongo_query):
            res_obj.append(obj["uniprot_canonical_ac"])
            if len(sorted(set(res_obj))) >= query_obj["limit"]:
                return sorted(set(res_obj))

    if query_obj["field"] == "go_id":
        q_obj = {'$regex': query_obj["value"], '$options': 'i'}
        mongo_query = {"go_annotation.categories.go_terms.id":q_obj}
        for obj in dbh[collection].find(mongo_query):
            for cat_obj in obj["go_annotation"]["categories"]:
                for term_obj in cat_obj["go_terms"]:
                    if term_obj["id"].lower().find(query_obj["value"].lower()) != -1:
                        res_obj.append(term_obj["id"])
                        if len(sorted(set(res_obj))) >= query_obj["limit"]:
                            return sorted(set(res_obj))
    if query_obj["field"] == "go_term":
        q_obj = {'$regex': query_obj["value"], '$options': 'i'}
        mongo_query = {"go_annotation.categories.go_terms.name":q_obj}
        for obj in dbh[collection].find(mongo_query):
            for cat_obj in obj["go_annotation"]["categories"]:
                for term_obj in cat_obj["go_terms"]:
                    if term_obj["name"].lower().find(query_obj["value"].lower()) != -1:
                        res_obj.append(term_obj["name"])
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

        for obj in dbh[collection].find(mongo_query):
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




