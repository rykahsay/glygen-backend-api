import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from pytz import timezone
from collections import OrderedDict
from bson import json_util, ObjectId

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


def search_init(db_obj):
    

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
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


def glycan_to_biosynthesis_enzymes(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["glytoucan_ac", "tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("glycan_to_biosynthesis_enzymes",  query_obj)
    #return mongo_query


    results = []
    obj = dbh[collection].find_one(mongo_query)
    seen = {}
    for o in obj["enzyme"]:
        if o["uniprot_canonical_ac"] not in seen:
            seen[o["uniprot_canonical_ac"]] = True
            plist_obj,tax_id = get_protein_list_fields(dbh, o["uniprot_canonical_ac"])
            if query_obj["tax_id"] == 0:
                results.append(plist_obj)
            elif tax_id == query_obj["tax_id"]:
                results.append(plist_obj)

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


def glycan_to_glycoproteins(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}


    field_list = ["glytoucan_ac", "tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj
    
    mongo_query = get_mongo_query("glycan_to_glycoproteins",  query_obj)
    #return mongo_query

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

def glycan_to_enzyme_gene_loci(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"    
    cache_collection = "c_genelocuscache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}


    field_list = ["glytoucan_ac", "tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj
    
    mongo_query = get_mongo_query("glycan_to_enzyme_gene_loci", query_obj)
    #return mongo_query

    results = []
    for obj in dbh[collection].find(mongo_query):
        for o in obj["enzyme"]:
            plist_obj,tax_id = get_genelocus_list_fields(dbh, o["uniprot_canonical_ac"])
            if query_obj["tax_id"] == 0:
                results.append(plist_obj)
            elif tax_id == query_obj["tax_id"]:
                results.append(plist_obj)


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


def biosynthesis_enzyme_to_glycans(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"    
    cache_collection = "c_glycancache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["uniprot_canonical_ac", "tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("biosynthesis_enzyme_to_glycans", query_obj)
    #return mongo_query

    results = []
    for obj in dbh[collection].find(mongo_query):
        results.append(get_glycan_list_fields(dbh, obj["glytoucan_ac"]))

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



def protein_to_orthologs(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"    
    cache_collection = "c_orthologcache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["uniprot_canonical_ac"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = {"uniprot_canonical_ac":query_obj["uniprot_canonical_ac"]}
    #return mongo_query

    if dbh[collection].find(mongo_query).count() == 0:
        return {"error_code":"non-existent-record"}

    results = []
    obj = dbh[collection].find_one(mongo_query)
    results = obj["orthologs"]


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



def species_to_glycosyltransferases(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("species_to_glycosyltransferases",  query_obj)
    #return mongo_query

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


def species_to_glycohydrolases(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["tax_id"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("species_to_glycohydrolases",  query_obj)
    #return mongo_query

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


def species_to_glycoproteins(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["tax_id", "evidence_type"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("species_to_glycoproteins",  query_obj)
    #return mongo_query

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


def disease_to_glycosyltransferases(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"    
    cache_collection = "c_proteincache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_list = ["tax_id", "do_name"]
    validation_obj = validate_query_obj(query_obj, field_list)
    if "error_code" in validation_obj:
        return validation_obj

    mongo_query = get_mongo_query("disease_to_glycosyltransferases",  query_obj)
    #return mongo_query

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



def genelocus_list(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    cache_collection = "c_genelocuscache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = 1000
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
        res_obj["results"].append(order_obj(obj))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj


def ortholog_list(query_obj, db_obj):

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    cache_collection = "c_orthologcache"
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj = {}
    #check if submitted fields are allowed and contain valid values
    field_list = ["id", "offset", "limit", "sort", "order"]
    max_query_value_len = 1000
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
        res_obj["results"].append(order_obj(obj))

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
        ,"iupac": obj["iupac"]
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
    gene_url = "https://www.genenames.org/cgi-bin/gene_symbol_report?hgnc_id=%s" % (gene_name)

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
        if "glytoucan_ac" in query_obj:
            cond_objs.append({"glytoucan_ac":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}})
        #if "tax_id" in query_obj:
        #    if query_obj["tax_id"] > 0:
        #        cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})
    elif svc_name in svc_grp[2]:
        if "uniprot_canonical_ac" in query_obj:
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



def dump_debug_log(out_string):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return


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



def order_obj(jsonObj):

    ordrHash = {"glytoucan_ac":1, "mass":2, "iupac":3, "wurcs":4, "glycoct":5,
                        "species":6, "classification":7,"glycoprotein":8,
                                    "enzyme":9, "crossref":10}
    for k1 in jsonObj:
        ordrHash[k1] = ordrHash[k1] if k1 in ordrHash else 1000
        if type(jsonObj[k1]) is dict:
            for k2 in jsonObj[k1]:
                ordrHash[k2] = ordrHash[k2] if k2 in ordrHash else 1000
                if type(jsonObj[k1][k2]) is dict:
                    for k3 in jsonObj[k1][k2]:
                        ordrHash[k3] = ordrHash[k3] if k3 in ordrHash else 1000
                    jsonObj[k1][k2] = OrderedDict(sorted(jsonObj[k1][k2].items(),
                        key=lambda x: float(ordrHash.get(x[0]))))
                elif type(jsonObj[k1][k2]) is list:
                    for j in xrange(0, len(jsonObj[k1][k2])):
                        if type(jsonObj[k1][k2][j]) is dict:
                            for k3 in jsonObj[k1][k2][j]:
                                ordrHash[k3] = ordrHash[k3] if k3 in ordrHash else 1000
                                jsonObj[k1][k2][j] = OrderedDict(sorted(jsonObj[k1][k2][j].items(), 
                                    key=lambda x: float(ordrHash.get(x[0]))))
            jsonObj[k1] = OrderedDict(sorted(jsonObj[k1].items(),
                key=lambda x: float(ordrHash.get(x[0]))))

    return OrderedDict(sorted(jsonObj.items(), key=lambda x: float(ordrHash.get(x[0]))))



def validate_query_obj(query_obj, field_list):


    # Check submitted fields are in field_list and have valid length
    max_query_value_len = 1000
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}


    # Check all required field, and make sure they have valid values 
    # field_list is expected to contain required fields
    for field in field_list:
        if field not in query_obj:
            return {"error_code":"missing-parameter"}
        if str(query_obj[field]).strip() == "":
            return {"error_code":"invalid-parameter-value-length"}

    return {}






def get_random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_error_obj(error_code, error_log, path_obj):
        
    error_id = get_random_string(6) 
    log_file = path_obj["apierrorlogpath"] + "/" + error_code + "-" + error_id + ".log"
    with open(log_file, "w") as FW:
        FW.write("%s" % (error_log))
    return {"error_code": "exception-error-" + error_id}


def is_valid_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True




                  
def is_int(input):
    try:
        num = int(input)
    except ValueError:
        return False
    return True
