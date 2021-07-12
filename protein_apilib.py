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
    record_list = []
    record_type = "protein"
    prj_obj = {"uniprot_canonical_ac":1}
    for obj in dbh[collection].find(mongo_query,prj_obj):
        record_list.append(obj["uniprot_canonical_ac"])

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
            "search_type":"search_simple"
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

    return res_obj




def protein_search(query_obj, config_obj):


    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("protein_search", query_obj,config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query(query_obj)
    #return mongo_query

    #path_obj = config_obj[config_obj["server"]]["htmlpath"]
    #blast_db = path_obj["datareleasespath"] + "data/v-%s/blastdb/canonicalsequences"
    #blast_db = blast_db % (config_obj["datarelease"])
    #cmd = "%s -db %s -query %s -evalue %s -outfmt %s"
    #cmd = cmd % (path_obj["blastp"], blast_db,"tmp/q.fasta", 0.1, 7)


    collection = "c_protein"
    record_list = []
    record_type = "protein"
    prj_obj = {"uniprot_canonical_ac":1}
    for obj in dbh[collection].find(mongo_query,prj_obj):
        record_list.append(obj["uniprot_canonical_ac"])

    
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
            "search_type":"search"
        }
        util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
    res_obj = {"list_id":list_id}

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
    #mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    mongo_query = {"uniprot_canonical_ac":{'$regex':query_obj["uniprot_canonical_ac"], 
        '$options': 'i'}} 
    obj = dbh[collection].find_one(mongo_query)
    if obj == None:
        return {"error_list":[{"error_code":"non-existent-cluster for cluster type=%s, uniprot_canonical_ac=%s" % (query_obj["cluster_type"], query_obj["uniprot_canonical_ac"])}]}


    selected_cls_id = ""
    for cls_id in obj["clusterlist"]:
        
        if cls_id.find(query_obj["cluster_type"]) != -1:
            selected_cls_id = cls_id
            break


    if selected_cls_id == "":
        return {"error_list":[{"error_code":"non-existent-cluster-type"}]}

    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if selected_cls_id == "":
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}


    collection = "c_alignment"
    mongo_query = {"cls_id":selected_cls_id}
    #return mongo_query
    obj = dbh[collection].find_one(mongo_query)


    if obj == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}

    #If the object has a property that is not in the specs, remove it
    
    util.clean_obj(obj, config_obj["removelist"]["c_alignment"], "c_alignment")
   
    #make canoncal sequence first in the list
    new_list_one = []
    new_list_two = []
    canon_list = []
    for o in obj["sequences"]:
        canon_list.append(o["uniprot_ac"])
        if o["uniprot_ac"] == query_obj["uniprot_canonical_ac"]:
            new_list_one.append(o)
        else:
            new_list_two.append(o)
    obj["sequences"] = new_list_one + new_list_two
    new_obj = obj

    obj["details"] = []
    sec_list = [
        "uniprot_canonical_ac",
        "ptm_annotation", "glycation", "snv", "site_annotation", "glycosylation",
        "site_annotation", "glycosylation", "mutagenesis", "phosphorylation"
    ]
    collection = "c_protein"
    mongo_query = {"uniprot_canonical_ac":{"$in": canon_list}}
    for canon_obj in  dbh[collection].find(mongo_query):
        tmp_obj = {}
        for sec in sec_list:
            tmp_obj[sec] = canon_obj[sec]
        obj["details"].append(tmp_obj)

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
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"].upper()}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"].upper()}}
        ]
    }
    obj = dbh[collection].find_one(mongo_query)
    q = {"record_id":{'$regex': query_obj["uniprot_canonical_ac"].upper(), "$options":"i"}}
    history_obj = dbh["c_idtrack"].find_one(q)


    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if obj == None:
        post_error_list.append({"error_code":"non-existent-record"})
        res_obj = {"error_list":post_error_list}
        if history_obj != None:
            res_obj["reason"] = history_obj["history"]
        return res_obj


    url = config_obj["urltemplate"]["uniprot"] % (obj["uniprot_canonical_ac"])
    obj["uniprot_id"] = obj["uniprot_id"] if "uniprot_id" in obj else ""
    obj["uniprot"] = {
        "uniprot_canonical_ac":obj["uniprot_canonical_ac"], 
        "uniprot_id":obj["uniprot_id"],
        "url":url,
        "length": obj["sequence"]["length"]
    }
    obj["history"] = history_obj["history"] if history_obj != None else []

    #for o in obj["gene"]:
    #    if len(obj["synonyms"]["gene"]["uniprotkb"]) > 1:
    #        o["name"] += "; " + "; ".join(obj["synonyms"]["gene"]["uniprotkb"][1:]) + ";"
    truncate_go_terms(obj)
    util.clean_obj(obj, config_obj["removelist"]["c_protein"], "c_protein")

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


    query_term = "\"%s\"" % (query_obj["term"])

    cond_objs = []
    if query_obj["term_category"] == "any":
        return {'$text': { '$search': query_term}}
    elif query_obj["term_category"] == "glycan":
        cond_objs.append({"glycosylation.glytoucan_ac":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "protein":
        cond_objs.append({"uniprot_canonical_ac":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"gene_names.name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"protein_names.name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"function.annotation":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"glycosylation.type" : {'$regex':query_obj["term"],'$options': 'i'}})

    
    elif query_obj["term_category"] == "gene":
        cond_objs.append({"gene_names.name":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"gene.locus.evidence.id":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "disease":
        prefix_list = [
            "disease.recommended_name", 
            "disease.synonyms",
            "expression_disease.disease.recommended_name",
            "expression_disease.disease.synonyms",
            "snv.disease.recommended_name", 
            "snv.disease.synonyms",
        ]
        for prefix in prefix_list:
            f_one, f_two = prefix + ".name", prefix + ".id"
            cond_objs.append({f_one:{'$regex': query_obj["term"], '$options': 'i'}})
            cond_objs.append({f_two:{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "pathway":
        cond_objs.append({"pathway.id":{'$regex': query_obj["term"], '$options': 'i'}})
        cond_objs.append({"pathway.name":{'$regex': query_obj["term"], '$options': 'i'}})
    elif query_obj["term_category"] == "organism":
        cond_objs.append({"species.name":{'$regex': query_obj["term"], '$options': 'i'}})

    mongo_query = {} if cond_objs == [] else { "$or": cond_objs }

    return mongo_query



def get_mongo_query(query_obj):

                        

    cond_objs = []
    #uniprot_canonical_ac
    if "uniprot_canonical_ac" in query_obj:
        qid_list = query_obj["uniprot_canonical_ac"].replace(" ", "").split(",")
        cond_objs.append(
            {
                "$or":[
                    {"uniprot_canonical_ac":{'$in': qid_list}},
                    {"uniprot_ac":{'$in': qid_list}},
                    {"uniprot_id":{'$in': qid_list}},
                    {"isoforms.isoform_ac":{'$in': qid_list}} 
                ]
            }
        )

    #protein_name
    if "protein_name" in query_obj:
        query_obj["protein_name"] = query_obj["protein_name"].replace("(", "\(").replace(")", "\)")
        query_obj["protein_name"] = query_obj["protein_name"].replace("[", "\[").replace("]", "\]")
        cond_objs.append({"protein_names.name":{'$regex': query_obj["protein_name"], '$options': 'i'}})

    #binding_glycan_id
    if "binding_glycan_id" in query_obj:
        q = {"interactions.interactor_id":{'$regex': query_obj["binding_glycan_id"], '$options': 'i'}}
        cond_objs.append(q)

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
        cond_objs.append({"gene_names.name" : {'$regex': query_obj["gene_name"], '$options': 'i'}})
    if "recommended_gene_name" in query_obj:
        q_val = '^%s$' % (query_obj["recommended_gene_name"])
        cond_objs.append({"gene_names.name" : {'$regex': q_val, '$options': 'i'}})
        cond_objs.append({"gene_names.type" : {'$eq': "recommended"}})

    #pathway_id
    if "pathway_id" in query_obj:
        cond_objs.append({"pathway.id" : {'$regex': query_obj["pathway_id"], '$options': 'i'}})

    #pmid
    if "pmid" in query_obj:
        cond_objs.append({"publication.reference.id" : {'$regex': query_obj["pmid"], '$options': 'i'}})

    #glycosylation_type
    if "glycosylation_type" in query_obj:
        cond_objs.append({"glycosylation.type" : {'$regex': query_obj["glycosylation_type"], '$options': 'i'}})

    #attached_glycan_id
    if "attached_glycan_id" in query_obj:
        q_str = query_obj["attached_glycan_id"]
        g_list = q_str.replace(" ", ",").split(",")
        q_one = {
                "$or":[
                    {"glycosylation.glytoucan_ac":{"$in": g_list}},
                    {"glycosylation.glytoucan_ac":{'$regex': q_str, '$options': 'i'}}
                ]
        }
        cond_objs.append(q_one)
    
    #disease name
    if "disease_name" in query_obj:
        or_list = [
            {"disease.recommended_name.name":{'$regex':query_obj["disease_name"],'$options':'i'}},
            {"disease.synonyms.name":{'$regex':query_obj["disease_name"],'$options':'i'}}
        ]
        cond_objs.append({'$or':or_list})

    #disease ID
    if "disease_id" in query_obj:
        or_list = [
            {"disease.recommended_name.id":{'$regex':query_obj["disease_id"],'$options':'i'}},
            {"disease.synonyms.id":{'$regex':query_obj["disease_id"],'$options':'i'}},
        ]
        cond_objs.append({'$or':or_list})

    #glycosylation_evidence
    if "glycosylation_evidence" in query_obj:
        if query_obj["glycosylation_evidence"] == "predicted":
            cond_objs.append({"glycosylation": {'$gt': []}})
            cond_objs.append({"glycosylation.site_category": {'$ne':"reported"}})
            cond_objs.append({"glycosylation.site_category": {'$ne':"reported_with_glycan"}})
        elif query_obj["glycosylation_evidence"] == "reported":
            cond_objs.append({"glycosylation": {'$gt': []}})
            cond_objs.append({"glycosylation.site_category":{"$regex":"reported","$options":"i"}})
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















def get_protein_list_object(obj):


    uniprot_canonical_ac = obj["uniprot_canonical_ac"]
    mass = -1
    if "mass" in obj:
        if "chemical_mass" in obj["mass"]:
            mass = obj["mass"]["chemical_mass"]
       
    protein_name, protein_names_uniprotkb, protein_names_refseq = "", "", ""
    if "protein_names" in obj:
        protein_name = util.extract_name(obj["protein_names"], "recommended", "UniProtKB")
        protein_names_uniprotkb = util.extract_name(obj["protein_names"], "all", "UniProtKB")
        protein_names_refseq = util.extract_name(obj["protein_names"], "all", "RefSeq")


    refseq_ac, refseq_name = "", ""
    if "refseq" in obj:
        refseq_ac = obj["refseq"]["ac"] if "ac" in obj["refseq"] else ""
        refseq_name = obj["refseq"]["name"] if "name" in obj["refseq"] else ""

    gene_name, gene_names_uniprotkb, gene_names_refseq = "", "", ""
    if "gene_names" in obj:
        gene_name = util.extract_name(obj["gene_names"], "recommended", "UniProtKB")
        gene_names_uniprotkb = util.extract_name(obj["gene_names"], "all", "UniProtKB")
        gene_names_refseq = util.extract_name(obj["gene_names"], "all", "RefSeq")



    organism_name, tax_id = "", 0
    if "species" in obj:
        if len(obj["species"]) > 0:
            organism_name = obj["species"][0]["name"] if "name" in obj["species"][0] else ""
            tax_id = obj["species"][0]["taxid"] if "taxid" in obj["species"][0] else 0
   
    disease_list = []
    if "disease" in obj:
        for o in obj["disease"]:
            disease_id = o["recommended_name"]["id"]
            disease_name = o["recommended_name"]["name"]
            resource = o["recommended_name"]["resource"]
            disease_list.append("%s (%s:%s)" % (disease_name, resource, disease_id))
    disease = "; ".join(disease_list)


    pathway_list = []
    if "pathway" in obj:
        for o in obj["pathway"]:
            pathway_id = o["id"]
            pathway_name = o["name"]
            pathway_list.append("%s (%s)" % (pathway_name, pathway_id))
    pathway = "; ".join(pathway_list)


    function_list = []
    if "function" in obj:
        for o in obj["function"]:
            ann = o["annotation"]
            badge_list= []
            for e in o["evidence"]:
                badge_list.append(e["database"])
            function_list.append("%s, [%s]" % (ann,", ".join(badge_list)))
    function = "; ".join(function_list)
    
    publication_count = 0
    if "publication" in obj:
        publication_count = len(obj["publication"])
  
    predicted_glycosites =  0
    reported_n_glycosites, reported_o_glycosites = 0,0
    reported_n_glycosites_with_glycan, reported_o_glycosites_with_glycan = 0,0

    if "glycosylation" in obj:
        for o in obj["glycosylation"]:
            #if o["position"] == "":
            #    continue
            site_type = o["type"].lower()

            if o["site_category"] == "predicted":
                predicted_glycosites += 1
            elif site_type == "n-linked" and o["site_category"] == "reported":
                reported_n_glycosites += 1
            elif site_type == "o-linked" and o["site_category"] == "reported":
                reported_o_glycosites += 1
            elif site_type == "n-linked" and o["site_category"] == "reported_with_glycan":
                reported_n_glycosites_with_glycan += 1
            elif site_type == "o-linked" and o["site_category"] == "reported_with_glycan":
                reported_o_glycosites_with_glycan += 1

    o = {
        "uniprot_canonical_ac":uniprot_canonical_ac
        ,"mass": mass
        ,"protein_name":protein_name
        ,"gene_name":gene_name
        ,"organism":organism_name
        ,"refseq_name": refseq_name
        ,"refseq_ac": refseq_ac
        ,"gene_names_uniprotkb":gene_names_uniprotkb
        ,"gene_names_refseq":gene_names_refseq
        ,"protein_names_uniprotkb":protein_names_uniprotkb
        ,"protein_names_refseq":protein_names_refseq
        ,"tax_id":tax_id
        ,"disease":disease
        ,"pathway":pathway
        ,"publication_count":publication_count
        ,"function":function
        ,"predicted_glycosites":predicted_glycosites
        ,"reported_n_glycosites":reported_n_glycosites
        ,"reported_o_glycosites":reported_o_glycosites
        ,"reported_n_glycosites_with_glycan":reported_n_glycosites_with_glycan
        ,"reported_o_glycosites_with_glycan":reported_o_glycosites_with_glycan
    }


    return o



