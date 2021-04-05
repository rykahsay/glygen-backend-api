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


def commonquery_search(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
    
    result_type = query_obj["result_type"]
    operation = query_obj["complex_query"]["operation"]
    q_list = query_obj["complex_query"]["query_list"]
    master_dict, final_id_list = run_query_list(q_list, config_obj, result_type, operation, 1)

    cache_dict = {"protein_list":"c_cache", "glycan_list":"c_cache", "count_list":""}
    cache_collection = cache_dict[result_type] 


    res_obj = {}
    if result_type == "count_list":
        res_obj = []
        coll_dict = {}
        for key in ["glycan", "protein", "gene", "organism", "pathway", "enzyme", "glycoprotein"]:
            coll_dict[key] = []

        for record_id in final_id_list:
            obj = master_dict[record_id]
            coll_dict["protein"].append(obj["uniprot_canonical_ac"])
            coll_dict["gene"].append(obj["gene_name"])
            coll_dict["organism"].append(obj["organism"])
            coll_dict["glycan"] += obj["glycanlist"]
            coll_dict["pathway"] += obj["pathwayidlist"]
            if obj["is_enzyme"] == True:
                coll_dict["enzyme"].append(obj["uniprot_canonical_ac"])
            if obj["is_glycoprotein"] == True:
                coll_dict["glycoprotein"].append(obj["uniprot_canonical_ac"])
        for key in ["glycan", "protein", "gene", "organism", "pathway", "enzyme", "glycoprotein"]:
            tmp_lst = list(sorted(set(coll_dict[key])))
            o = {"name":key, "count":len(tmp_lst)}
            res_obj.append(o)

    elif result_type in ["protein_list", "glycan_list"]:
        results = []
        for record_id in final_id_list:
            obj = master_dict[record_id]
            for k in ["is_enzyme", "glycanlist", "is_glycoprotein", "pathwayidlist"]:
                if k in obj:
                    obj.pop(k)
            results.append(obj)
        if len(results) == 0:
            res_obj = {"list_id":""}
        else:
            ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
            hash_obj = hashlib.md5(json.dumps(query_obj))
            list_id = hash_obj.hexdigest()
            search_results_obj = {}
            search_results_obj["list_id"] = list_id
            search_results_obj["query"] = query_obj
            search_results_obj["query"]["execution_time"] = ts
            search_results_obj["results"] = results
            result = dbh[cache_collection].delete_many({"list_id":list_id})
            result = dbh[cache_collection].insert_one(search_results_obj)
            res_obj["list_id"] = list_id

    return res_obj


def run_query_list(query_list, config_obj, result_type, operation, nest_layer):


    master_dict = {}
    id_grid = []
    for obj in query_list:
        if "glycan_query" in obj:
            q_obj = obj["glycan_query"]
            res_obj = commonquery_search_glycan(q_obj, config_obj, result_type)
            if res_obj != {}:
                master_dict.update(res_obj)
                tmp_lst = res_obj.keys()
                id_grid.append(tmp_lst)
        if "protein_query" in obj:
            q_obj = obj["protein_query"]
            res_obj = commonquery_search_protein(q_obj, config_obj, result_type)
            if res_obj != {}:
                master_dict.update(res_obj)
                tmp_lst = res_obj.keys()
                id_grid.append(tmp_lst)
        if "complex_query" in obj:
            q_list = obj["complex_query"]["query_list"]
            op = obj["complex_query"]["operation"]
            inner_master_dict, inner_final_id_list = run_query_list(q_list,config_obj,result_type, op, nest_layer + 1)
            if inner_master_dict != {}:
                master_dict.update(inner_master_dict)
                id_grid.append(inner_final_id_list)

        final_id_list = id_grid[0]
        for tmp_lst in id_grid[1:]:
            if operation.lower() == "or":
                final_id_list = list(set(final_id_list).union(set(tmp_lst)))
            elif operation.lower() == "and":
                final_id_list = list(set(final_id_list).intersection(set(tmp_lst)))
            elif operation.lower() == "nand":
                diff_one = set(final_id_list) - set(tmp_lst)
                diff_two = set(tmp_lst) - set(final_id_list)
                final_id_list = list(diff_one.union(diff_two))

    return master_dict, final_id_list



def commonquery_search_glycan(query_obj, config_obj, result_type):

    collection = "c_glycan"
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    query_obj = clean_glycan_query(dbh, query_obj, config_obj)

    error_list = errorlib.get_errors_in_query("commonquery_search_glycan", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    mongo_query = get_glycan_mongo_query(query_obj)
    
    res_obj = {}
    seen = {}
    prj_obj = {"glytoucan_ac":1, "glycoprotein":1}
    for obj in dbh[collection].find(mongo_query,prj_obj):
        if result_type == "glycan_list":
            glytoucan_ac = obj["glytoucan_ac"]
            res_obj[glytoucan_ac] = get_glycan_list_record(obj)
        elif result_type in ["protein_list", "count_list"]:
            if "glycoprotein" in obj:
                for xobj in obj["glycoprotein"]:
                    canon = xobj["uniprot_canonical_ac"]
                    o = dbh["c_protein"].find_one({"uniprot_canonical_ac":canon})
                    if o != None and canon not in seen:
                        res_obj[canon] = get_protein_list_record(o)
                        seen[canon] = True
    return res_obj





def commonquery_search_protein(query_obj, config_obj, result_type):

    collection = "c_protein"
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    query_obj = clean_protein_query(dbh, query_obj, config_obj)

    error_list = errorlib.get_errors_in_query("commonquery_search_protein", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    mongo_query = get_protein_mongo_query(query_obj)
    res_obj = {}
    seen = {}
    prj_obj = {"uniprot_canonical_ac":1, "glycosylation":1}
    for obj in dbh[collection].find(mongo_query, prj_obj):
        if result_type in ["protein_list", "count_list"]:
            canon = obj["uniprot_canonical_ac"]
            res_obj[canon] = get_protein_list_record(obj)
        elif result_type == "glycan_list":
            if "glycosylation" in obj:
                for xobj in obj["glycosylation"]:
                    glytoucan_ac = xobj["glytoucan_ac"]
                    o = dbh["c_glycan"].find_one({"glytoucan_ac":glytoucan_ac})
                    if o != None and glytoucan_ac not in seen:
                        res_obj[glytoucan_ac] = get_glycan_list_record(o)
                        seen[glytoucan_ac] = True
    return res_obj






def get_glycan_mongo_query(query_obj):

    cond_objs = []
    #glytoucan_ac
    if "glytoucan_ac" in query_obj:
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("[", "\\[")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("]", "\\]")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace("(", "\\(")
        query_obj["glytoucan_ac"] = query_obj["glytoucan_ac"].replace(")", "\\)")
        cond_objs.append(
            {
                "$or":[
                    {"glytoucan_ac":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}},
                    {"iupac":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}},
                    {"wurcs":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}},
                    {"glycoct":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}},
                    {"smiles_isomeric":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}},
                    {"crossref.id":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}}
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
                operation = query_obj["organism"]["operation"].lower()
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
        cond_objs.append({"publication.reference.id" : {'$regex': query_obj["pmid"], '$options': 'i'}})


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
            if o["max"] > 0:
                cond_objs.append({"composition.residue": {'$eq': o["residue"]}})
            else:
                cond_objs.append({"composition.residue": {'$ne': o["residue"]}})

    operation = query_obj["operation"].lower() if "operation" in query_obj else "and"
    mongo_query = {} if cond_objs == [] else { "$"+operation+"": cond_objs }
    return mongo_query






def get_protein_mongo_query(query_obj):

                        

    cond_objs = []
    #glytoucan_ac
    if "uniprot_canonical_ac" in query_obj:
        cond_objs.append({"uniprot_canonical_ac":{'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}})

    #protein_name
    if "protein_name" in query_obj:
        query_obj["protein_name"] = query_obj["protein_name"].replace("(", "\(").replace(")", "\)")
        query_obj["protein_name"] = query_obj["protein_name"].replace("[", "\[").replace("]", "\]")
        cond_objs.append({"protein_names.name":{'$regex': query_obj["protein_name"], '$options': 'i'}})

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

    #pathway_id
    if "pathway_id" in query_obj:
        cond_objs.append({"pathway.id" : {'$regex': query_obj["pathway_id"], '$options': 'i'}})

    #pmid
    if "pmid" in query_obj:
        cond_objs.append({"publication.reference.id" : {'$regex': query_obj["pmid"], '$options': 'i'}})

    #glycan
    if "glycan" in query_obj:
        if "glytoucan_ac" in query_obj["glycan"]:
            cond_objs.append({"glycosylation.glytoucan_ac": {'$regex': query_obj["glycan"]["glytoucan_ac"], 
                                                            '$options': 'i'}})
        if "relation" in query_obj["glycan"]:
            cond_objs.append({"glycosylation.glytoucan_ac": {'$regex': query_obj["glycan"]["relation"],
                                                                        '$options': 'i'}})
    
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
                operation = query_obj["glycosylated_aa"]["operation"].lower()
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



def clean_protein_query(dbh, query_obj, config_obj):

    #glycan.attached is not implemented in c_protein jsons yet
    if "glycan" in query_obj:
        if "relation" in query_obj["glycan"]:
            query_obj["glycan"].pop("relation")

    return query_obj



def clean_glycan_query(dbh, query_obj, config_obj):

    #Clean query object
    key_list = query_obj.keys()
    for key in key_list:
        flag_list = []
        flag_list.append(str(query_obj[key]).strip() == "")
        flag_list.append(query_obj[key] == [])
        flag_list.append(query_obj[key] == {})
        if True in flag_list:
            query_obj.pop(key)

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


    return query_obj


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


    out_obj = protein_apilib.get_protein_list_object(in_obj)

    out_obj["is_glycoprotein"] = False
    out_obj["glycanlist"] = []
    if "glycosylation" in in_obj:
        out_obj["is_glycoprotein"] = True
        for o in in_obj["glycosylation"]:
            if o["glytoucan_ac"] != "":
                out_obj["glycanlist"].append(o["glytoucan_ac"])

    out_obj["is_enzyme"] = False
    if "enzyme_annotation" in in_obj:
        if len(in_obj["enzyme_annotation"]) > 0:
            out_obj["is_enzyme"] = True

    out_obj["pathwayidlist"] = []
    if "pathway" in in_obj:
        for o in in_obj["pathway"]:
            if o["id"] != "":
                out_obj["pathwayidlist"].append(o["id"])

    return out_obj


