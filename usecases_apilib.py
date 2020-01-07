import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from pytz import timezone
from bson import json_util, ObjectId

import errorlib
import util



def search_init(config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    collection = "c_glycan"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {"glycan_mass":{}, "number_monosaccharides":{}, 
                "organism":[], "glycan_type":[]}
    min_mass = 10000000.0
    max_mass = -min_mass
    min_monosaccharides = 100000
    max_monosaccharides = -min_monosaccharides

    seen = {"glycan_type":{}, "organism":{}}
    for obj in dbh[collection].find({}):
        glytoucan_ac = obj["glytoucan_ac"]
        if "mass" in obj:
            obj["mass"] = float(obj["mass"])
            min_mass = round(obj["mass"], 2) if obj["mass"] < min_mass else min_mass
            max_mass = round(obj["mass"], 2) if obj["mass"] > max_mass else max_mass
        
        if "number_monosaccharides" in obj:
            min_monosaccharides = obj["number_monosaccharides"] if obj["number_monosaccharides"] < min_monosaccharides else min_monosaccharides
            max_monosaccharides = obj["number_monosaccharides"] if obj["number_monosaccharides"] > max_monosaccharides else max_monosaccharides

        if "species" in obj:
            for o in obj["species"]:
                org_name = o["name"] + " (Taxonomy ID: " + str(o["taxid"]) + ")"
                seen["organism"][org_name] = True
        
        if "classification" in obj:
            for o in obj["classification"]:
                type_name = o["type"]["name"]
                subtype_name = o["subtype"]["name"]
                if type_name not in seen["glycan_type"]:
                    seen["glycan_type"][type_name] = {}
                if subtype_name not in seen["glycan_type"][type_name]:
                    seen["glycan_type"][type_name][subtype_name] = True 

    res_obj["glycan_mass"]["min"] = min_mass
    res_obj["glycan_mass"]["max"] = max_mass
    res_obj["number_monosaccharides"]["min"] = min_monosaccharides
    res_obj["number_monosaccharides"]["max"] = max_monosaccharides 

    for type_name in seen["glycan_type"]:
        o = {"name":type_name,"subtype":[]}
        for subtype_name in seen["glycan_type"][type_name]:
            o["subtype"].append(subtype_name)
        res_obj["glycan_type"].append(o)
    
    for org_name in seen["organism"]:
        res_obj["organism"].append(org_name)

    return res_obj


def glycan_to_biosynthesis_enzymes(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    mongo_query = get_mongo_query("glycan_to_biosynthesis_enzymes",  query_obj)
    #return mongo_query


    collection = "c_glycan"    
    cache_collection = "c_proteincache"

    results = []
    obj = dbh[collection].find_one(mongo_query)
    seen = {}
    if obj != None:
        for o in obj["enzyme"]:
            if o["uniprot_canonical_ac"] not in seen:
                seen[o["uniprot_canonical_ac"]] = True
                plist_obj,tax_id = get_protein_list_fields(dbh, o["uniprot_canonical_ac"])
                if query_obj["tax_id"] == 0:
                    results.append(plist_obj)
                elif tax_id == query_obj["tax_id"]:
                    results.append(plist_obj)

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
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


def glycan_to_glycoproteins(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("glycan_to_glycoproteins",  query_obj)
    #return mongo_query

    collection = "c_glycan"    
    cache_collection = "c_proteincache"


    results = []
    seen = {}
    for obj in dbh[collection].find(mongo_query):
        for o in obj["glycoprotein"]:
            if o["uniprot_canonical_ac"] not in seen:
                seen[o["uniprot_canonical_ac"]] = True
                plist_obj,tax_id = get_protein_list_fields(dbh, o["uniprot_canonical_ac"])
                if query_obj["tax_id"] == 0:
                    results.append(plist_obj)
                elif tax_id == query_obj["tax_id"]:
                    results.append(plist_obj)

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
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

def glycan_to_enzyme_gene_loci(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_one", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("glycan_to_enzyme_gene_loci", query_obj)
    #return mongo_query
        
    collection = "c_glycan"    
    cache_collection = "c_genelocuscache"

    results = []
    for obj in dbh[collection].find(mongo_query):
        for o in obj["enzyme"]:
            plist_obj,tax_id = get_genelocus_list_fields(dbh, o["uniprot_canonical_ac"])
            if query_obj["tax_id"] == 0:
                results.append(plist_obj)
            elif tax_id == query_obj["tax_id"]:
                results.append(plist_obj)

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
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


def biosynthesis_enzyme_to_glycans(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_two", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("biosynthesis_enzyme_to_glycans", query_obj)
    #return mongo_query


    collection = "c_glycan"
    cache_collection = "c_glycancache"

    results = []
    for obj in dbh[collection].find(mongo_query):
        results.append(get_glycan_list_fields(dbh, obj["glytoucan_ac"]))

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")


    res_obj = {}
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


def protein_to_glycosequons(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_seven", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    #mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]
    }
    #return mongo_query


    collection = "c_protein"    
    cache_collection = "c_glycosequonscache"

    obj = dbh[collection].find_one(mongo_query)
    tmp_list = obj["site_annotation"] if obj != None else []
    results = []
    for o in tmp_list:
        if o["annotation"] == "n_glycosylation_sequon":
            results.append(o)
    

    res_obj = {}
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



def protein_to_orthologs(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_three", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    #mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    mongo_query = {
        "$or":[
            {"uniprot_canonical_ac":{'$eq': query_obj["uniprot_canonical_ac"]}},
            {"uniprot_ac":{'$eq': query_obj["uniprot_canonical_ac"]}}
        ]   
    }
    #return mongo_query


    collection = "c_protein"    
    cache_collection = "c_orthologcache"

    results = []
    obj = dbh[collection].find_one(mongo_query)
    
    results = obj["orthologs"] if obj != None else []

    res_obj = {}
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



def species_to_glycosyltransferases(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_four", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycosyltransferases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_proteincache"

    results = []
    for obj in dbh[collection].find(mongo_query):
        full_name, short_name, gene_name, organism, refseq_ac, refseq_name = "", "", "", "", "", ""
        if "recommendedname" in obj:
            full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
            short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        if "gene" in obj:
            gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
        if "species" in obj:
            organism = obj["species"][0]["name"] if obj["species"] != [] else ""
        if "refseq" in obj:
            refseq_ac = obj["refseq"]["ac"] if "ac" in obj["refseq"] else ""
            refseq_name = obj["refseq"]["name"] if "name" in obj["refseq"] else ""

        results.append({
            "uniprot_canonical_ac":obj["uniprot_canonical_ac"]
            ,"mass": obj["mass"]["chemical_mass"]
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":organism
            ,"refseq_name": refseq_name
            ,"refseq_ac": refseq_ac
        })

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
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


def species_to_glycohydrolases(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_four", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycohydrolases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_proteincache"


    results = []
    for obj in dbh[collection].find(mongo_query):
	full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
        short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
        organism = obj["species"][0]["name"] if obj["species"] != [] else ""
        refseq_ac = obj["refseq"]["ac"]
        refseq_name = obj["refseq"]["name"]
        results.append({
            "uniprot_canonical_ac":obj["uniprot_canonical_ac"]
            ,"mass": obj["mass"]["chemical_mass"]
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":organism
            ,"refseq_ac":refseq_ac
            ,"refseq_name":refseq_name
        })

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
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


def species_to_glycoproteins(query_obj, config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_five", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    mongo_query = get_mongo_query("species_to_glycoproteins",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_proteincache"


    results = []
    for obj in dbh[collection].find(mongo_query):
        full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
        short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
        organism = obj["species"][0]["name"] if obj["species"] != [] else ""
        refseq_ac = obj["refseq"]["ac"]
        refseq_name = obj["refseq"]["name"]
        results.append({
            "uniprot_canonical_ac":obj["uniprot_canonical_ac"]
            ,"mass": obj["mass"]["chemical_mass"]
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":organism
            ,"refseq_name": refseq_name
            ,"refseq_ac": refseq_ac
        })


    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")

    res_obj = {}
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


def disease_to_glycosyltransferases(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
 
    #Collect errors 
    error_list = errorlib.get_errors_in_query("usecases_group_six", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    
    mongo_query = get_mongo_query("disease_to_glycosyltransferases",  query_obj)
    #return mongo_query

    collection = "c_protein"    
    cache_collection = "c_proteincache"


    results = []
    for obj in dbh[collection].find(mongo_query):
    	full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
        short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
        organism = obj["species"][0]["name"] if obj["species"] != [] else ""
        refseq_ac = obj["refseq"]["ac"]
        refseq_name = obj["refseq"]["name"]
        results.append({
            "uniprot_canonical_ac":obj["uniprot_canonical_ac"]
            ,"mass": obj["mass"]["chemical_mass"]
            ,"protein_name_long":full_name
            ,"protein_name_short":short_name
            ,"gene_name":gene_name
            ,"organism":organism
            ,"refseq_name": refseq_name
            ,"refseq_ac": refseq_ac
        })    

    query_obj["organism"] = {"id":query_obj["tax_id"], "name":config_obj["taxid2name"][str(query_obj["tax_id"])]}
    query_obj.pop("tax_id")
    res_obj = {}
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



def genelocus_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    cache_collection = "c_genelocuscache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}

    default_hash = {"offset":1, "limit":20, "sort":"id", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}

    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"query":cached_obj["query"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
	return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj



def glycosequon_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
    cache_collection = "c_glycosequonscache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}

    default_hash = {"offset":1, "limit":20, "sort":"id", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}

    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"query":cached_obj["query"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
        return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj




def ortholog_list(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj
    cache_collection = "c_orthologcache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = config_obj["max_query_value_len"]
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    #Check for required parameters
    key_list = ["id"]
    for key in key_list:
        if key not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[key]).strip() == "":
            return {"error_code":"invalid-parameter-value"}


    cached_obj = dbh[cache_collection].find_one({"list_id":query_obj["id"]})
    if cached_obj == None:
        return {"error_code":"non-existent-search-results"}

    default_hash = {"offset":1, "limit":20, "sort":"id", "order":"asc"}
    for key in default_hash:
        if key not in query_obj:
            query_obj[key] = default_hash[key]
        else:
            #check type for submitted int fields
            if key in ["offset", "limit"]:
                if type(query_obj[key]) is not int:
                    return {"error_code":"invalid-parameter-value"}
            #check type for submitted selection fields
            if key in ["order"]:
                if query_obj[key] not in ["asc", "desc"]:
                    return {"error_code":"invalid-parameter-value"}

    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"])
    res_obj = {"query":cached_obj["query"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
	return {"error_code":"invalid-parameter-value"}

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(util.order_obj(obj, config_obj["objectorder"]["protein"]))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj


def get_protein_list_fields(dbh, uniprot_canonical_ac):

    collection = "c_protein"
    obj = dbh[collection].find_one({"uniprot_canonical_ac":uniprot_canonical_ac})
    
    full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
    short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
    gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
    organism = obj["species"][0]["name"] if obj["species"] != [] else ""
    refseq_ac = obj["refseq"]["ac"]
    refseq_name = obj["refseq"]["name"]
    plist_obj = {
        "uniprot_canonical_ac":uniprot_canonical_ac
        ,"mass": obj["mass"]["chemical_mass"] 
        ,"protein_name_long":full_name
        ,"protein_name_short":short_name
        ,"gene_name":gene_name
        ,"organism":organism
        ,"refseq_ac":refseq_ac
        ,"refseq_name":refseq_name
    }
    return plist_obj, obj["species"][0]["taxid"]

def get_glycan_list_fields(dbh, glytoucan_ac):
  
    collection = "c_glycan"
    obj = dbh[collection].find_one({"glytoucan_ac":glytoucan_ac})

    seen = {"enzyme":{}, "glycoprotein":{}}
    for o in obj["glycoprotein"]:
        seen["glycoprotein"][o["uniprot_canonical_ac"].lower()] = True
    for o in obj["enzyme"]:
        seen["enzyme"][o["uniprot_canonical_ac"].lower()] = True

    return {
        "glytoucan_ac":glytoucan_ac
        ,"mass":obj["mass"]
        ,"number_monosaccharides": obj["number_monosaccharides"]
        ,"number_enzymes":len(seen["enzyme"].keys()) 
        ,"number_proteins":len(seen["glycoprotein"].keys()) 
        ,"iupac": obj["iupac"] if "iupac" in obj else ""
        ,"glycoct": obj["glycoct"]
    }


def get_genelocus_list_fields(dbh, uniprot_canonical_ac):

    collection = "c_protein"
    obj = dbh[collection].find_one({"uniprot_canonical_ac":uniprot_canonical_ac})
    
    protein_name = ""
    if "recommendedname" in obj:
        if "full" in obj["recommendedname"]:
            protein_name = obj["recommendedname"]["full"]
    gene_name = obj["gene"][0]["name"] if obj["gene"] != [] else ""
    organism = obj["species"][0]["name"] if obj["species"] != [] else ""
    tax_id = obj["species"][0]["taxid"] if obj["species"] != [] else 0
    gene_url = obj["gene"][0]["url"]



    for o in obj["isoforms"]:
        if o["isoform_ac"] == uniprot_canonical_ac:
            plist_obj = {
                "uniprot_canonical_ac":uniprot_canonical_ac
                ,"protein_name":protein_name
                ,"gene_name":gene_name
                ,"gene_link":gene_url
                ,"tax_id":tax_id
                ,"organism":organism
                ,"chromosome":o["locus"]["chromosome"]
                ,"start_pos":o["locus"]["start_pos"]
                ,"end_pos":o["locus"]["end_pos"]
            }
            return plist_obj, tax_id



def get_mongo_query(svc_name, query_obj):

    svc_grp = [
            []
            ,["glycan_to_biosynthesis_enzymes","glycan_to_glycoproteins", "glycan_to_enzyme_gene_loci"]
            ,["biosynthesis_enzyme_to_glycans"]
            ,["species_to_glycosyltransferases"]
            ,["species_to_glycohydrolases"]
            ,["species_to_glycoproteins"]
            ,["disease_to_glycosyltransferases"]
    ] 


    cond_objs = []
    if svc_name in svc_grp[1]:
        #For this services, only search by glytoucan_ac, tax_id filtering is done to the proteins
        if "glytoucan_ac" in query_obj:
            cond_objs.append({"glytoucan_ac":{'$eq': query_obj["glytoucan_ac"]}})
    elif svc_name in svc_grp[2]:
        if "uniprot_canonical_ac" in query_obj:
            #cond_objs.append({"enzyme.uniprot_canonical_ac": {'$eq': query_obj["uniprot_canonical_ac"]}})
            cond_objs.append({"enzyme.uniprot_canonical_ac": {'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}})

        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
    elif svc_name in svc_grp[3]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            cond_objs.append({"keywords": "glycosyltransferase-activity"}) 
    elif svc_name in svc_grp[4]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            cond_objs.append({"keywords": "glycohydrolase-activity"})
    elif svc_name in svc_grp[5]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            if query_obj["evidence_type"] == "predicted":
                cond_objs.append({"glycosylation": {'$gt':[]}})
                #cond_objs.append({"glycosylation.evidence.database": {'$eq':"UniProtKB"}})
                #cond_objs.append({"glycosylation.evidence": {'$size': 1}})
                cond_objs.append({"glycosylation.evidence.database": {'$ne':"UniCarbKB"}})
                cond_objs.append({"glycosylation.evidence.database": {'$ne':"PDB"}})
                cond_objs.append({"glycosylation.evidence.database": {'$ne':"PubMed"}})
            elif query_obj["evidence_type"] == "reported":
                or_list = [
                    {"glycosylation.evidence.database": {'$eq':"UniCarbKB"}}
                    ,{"glycosylation.evidence.database": {'$eq':"PubMed"}}
                    ,{"glycosylation.evidence.database": {'$eq':"PDB"}}
                ]
                cond_objs.append({'$or':or_list})
            elif query_obj["evidence_type"] == "both":
                cond_objs.append({"glycosylation": {'$gt': []}})
    elif svc_name in svc_grp[6]:
        if "tax_id" in query_obj:
            if query_obj["tax_id"] > 0:
                cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
            if query_obj["do_name"] > 0:
                cond_objs.append({"disease.name": {'$regex': query_obj["do_name"], '$options': 'i'}})
            cond_objs.append({"keywords": "glycosyltransferase-activity"})
    mongo_query = {} if cond_objs == [] else { "$and": cond_objs }
    return mongo_query




def sort_objects(obj_list, field_name, order_type):

    seen = {
        "uniprot_canonical_ac":{} 
        ,"protein_name":{} 
        ,"gene_name":{}
        ,"chromosome":{}
        ,"start_pos":{}
        ,"end_pos":{}
        ,"organism":{}
        ,"tax_id":{}
    }

    grid_obj = {
        "uniprot_canonical_ac":[]
        ,"protein_name":[]
        ,"gene_name":[]
        ,"chromosome":[]
        ,"start_pos":[]
        ,"end_pos":[]
        ,"organism":[]
        ,"tax_id":[]
    }


    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        grid_obj[field_name].append({"index":i, field_name:obj[field_name]})


    reverse_flag = True if order_type == "desc" else False
    key_list = []
    sorted_obj_list = sorted(grid_obj[field_name], key=lambda x: x[field_name], reverse=reverse_flag)
    for o in sorted_obj_list:
            key_list.append(o["index"])
    return key_list








