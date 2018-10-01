import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure



def protein_search_init(db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_searchinit"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj =  dbh[collection].find_one({})

    return res_obj["protein"]


def protein_search(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"
    cache_collection = "c_proteincache"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    field_grp1 = ["query_type", "operation", "gene_name",
            "uniprot_canonical_ac", "refseq_ac", "protein_name", "glycosylation_evidence", "pathway_id"]
    field_grp2 = ["mass"]
    field_grp3 = ["glycan"]
    field_grp4 = ["sequence"]
    field_grp5 = ["glycosylated_aa"]
    field_grp6 = ["tax_id"]
    #check if submitted fields are allowed and contain valid values
    field_list = field_grp1 + field_grp2 + field_grp3 + field_grp4 + field_grp5 + field_grp6
    max_query_value_len = 1000
    max_sequence_len = 1000

    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if field in field_grp1:
            if len(str(query_obj[field])) > max_query_value_len:
                return {"error_code":"invalid-parameter-value-length"}


    flag_list = []
    for field in query_obj:
        if field in ["query_type", "operation"]:
            continue
        if field in field_grp1:
            flag_list.append(query_obj[field] != "")
        elif field in field_grp2 + field_grp3 + field_grp4:
            flag_list.append(query_obj[field] != {})
        elif field in field_grp5:
            flag_list.append(query_obj[field] != [])
        elif field in field_grp6:
            if type(query_obj[field]) is not int:
                return {"error_code":"invalid-parameter-value"}

    for field1 in query_obj:
        if field1 in field_grp2:
            for field2  in query_obj[field1]:
                if field2 not in ["min", "max"]:
                    return {"error_code":"unexpected-field-in-query"}
                if type(query_obj[field1][field2]) is not float and type(query_obj[field1][field2]) is not int:
                    return {"error_code":"invalid-parameter-value"}
        if field1 in field_grp3:
           for field2  in query_obj[field1]:
                if field2 not in ["glytoucan_ac", "relation"]:
                    return {"error_code":"unexpected-field-in-query"}
                if len(str(query_obj[field1][field2])) > max_query_value_len:
                    return {"error_code":"invalid-parameter-value-length"}
        if field1 in field_grp4:
            for field2  in query_obj[field1]:
                if field2 not in ["aa_sequence", "type"]:
                    return {"error_code":"unexpected-field-in-query"}
                if len(str(query_obj[field1][field2])) > max_sequence_len:
                    return {"error_code":"invalid-parameter-value-length"}

    for field1 in field_grp1:
        if field1 not in query_obj:
		continue
	if field1 in ["query_type", "operation"]:
            query_obj.pop(field1)
        elif str(query_obj[field1]).strip() == "":
            query_obj.pop(field1)

    for field1 in field_grp2 + field_grp3 + field_grp4 + field_grp5:
        if field1 not in query_obj:
                continue
	if query_obj[field1] == {} or query_obj[field1] == []:
            query_obj.pop(field1)


    mongo_query = get_mongo_query(query_obj)
    #return mongo_query


    results = []
    for obj in dbh[collection].find(mongo_query):
        uniprot_canonical_ac = obj["uniprot_canonical_ac"]
        mass = -1
        if "mass" in obj:
            if "chemical_mass" in obj["mass"]:
                mass = obj["mass"]["chemical_mass"]
        
        full_name = obj["recommendedname"]["full"] if "full" in obj["recommendedname"] else ""
        short_name = obj["recommendedname"]["short"] if "short" in obj["recommendedname"] else ""
        refseq_ac = obj["refseq"]["ac"]
        refseq_name = obj["refseq"]["name"]

        gene_name = ""
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
        search_results_obj = {}
        search_results_obj["list_id"] = list_id
        search_results_obj["query"] = query_obj
        search_results_obj["query"]["execution_time"] = ts
        search_results_obj["results"] = results
        result = dbh[cache_collection].delete_many({"list_id":list_id})
        result = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id


    return res_obj


def protein_list(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    cache_collection = "c_proteincache"
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



def protein_detail(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_protein"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    #check if submitted fields are allowed and contain valid values
    field_list = ["uniprot_canonical_ac"]
    max_query_value_len = 1000
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    mongo_query = {"uniprot_canonical_ac":{'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}}
    obj = dbh[collection].find_one(mongo_query)

    if obj == None:
        return {"error_code":"non-existent-record"}
    
    #If the object has a property that is not in the specs, remove it
    remove_prop_list = ["orthologs"]
    for key in remove_prop_list:
        if key in obj:
            obj.pop(key)


    return order_obj(obj)



def get_mongo_query(query_obj):

                        

    cond_objs = []
    #glytoucan_ac
    if "uniprot_canonical_ac" in query_obj:
        cond_objs.append({"uniprot_canonical_ac":{'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}})

    #protein_name
    if "protein_name" in query_obj:
        cond_objs.append({"recommendedname.full":{'$regex': query_obj["protein_name"], '$options': 'i'}})

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
    if "tax_id" in query_obj:
        if query_obj["tax_id"] > 0:
            cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})

    #gene_name
    if "gene_name" in query_obj:
        cond_objs.append({"gene.name" : {'$regex': query_obj["gene_name"], '$options': 'i'}})

    #pathway_id
    if "pathway_id" in query_obj:
        cond_objs.append({"pathway.id" : {'$regex': query_obj["pathway_id"], '$options': 'i'}})

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


    #glycosylated_aa
    if "glycosylated_aa" in query_obj:
        for aa in query_obj["glycosylated_aa"]:
            cond_objs.append({"glycosylation.residue": {'$regex': aa, '$options': 'i'}})

    #sequence
    if "sequence" in query_obj:
        if "aa_sequence" in query_obj["sequence"]:
            cond_objs.append({"sequence.sequence": {'$regex': query_obj["sequence"]["aa_sequence"],
                                                        '$options': 'i'}})
        #if "type" in query_obj["sequence"]:
        #    cond_objs.append({"sequence.type": {'$regex': query_obj["sequence"]["type"],
        #                                            '$options': 'i'}})


    mongo_query = {} if cond_objs == [] else { "$and": cond_objs }
    return mongo_query




def dump_debug_log(out_string):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return


def sort_objects(obj_list, field_name, order_type):


    seen = {"uniprot_canonical_ac":{}, "mass":{}, "protein_name_short":{}, "protein_name_long":{}, 
            "organism":{}, "gene_name":{}, "refseq_ac":{}, "refseq_name":{}}
    grid_obj = {
            "uniprot_canonical_ac":[], "mass":[], "protein_name_short":[], 
            "protein_name_long":[],     
            "organism":[], "gene_name":[], "refseq_ac":[], "refseq_name":[]
    }
    field_set_float = ["mass"]
    field_set_string = ["uniprot_canonical_ac","protein_name_short", "protein_name_long", "organism", 
            "gene_name", "refseq_ac", "refseq_name"]
    field_set_int = []

    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        uniprot_canonical_ac = obj["uniprot_canonical_ac"]
        if field_name == "mass":
            mass = -1
            if "mass" in obj:
                mass = obj["mass"]
            grid_obj[field_name].append({"index":i, field_name:float(mass)})
        elif field_name in field_set_string:
            grid_obj[field_name].append({"index":i, field_name:obj[field_name]})
        elif field_name in field_set_int:
            grid_obj[field_name].append({"index":i, field_name:int(obj[field_name])})

    reverse_flag = True if order_type == "desc" else False
    key_list = []
    sorted_obj_list = sorted(grid_obj[field_name], key=lambda x: x[field_name], reverse=reverse_flag)
    for o in sorted_obj_list:
            key_list.append(o["index"])
    return key_list



def order_obj(jsonObj):

    ordrHash = {"uniprot_canonical_ac":1, "uniprot_canonical_id":2, "mass":3, 
            "recommendedname":4, "gene":5, "keywords":6, "species":7
    }
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


