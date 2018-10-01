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

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure


def glycan_search_init(db_obj):
    

    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_searchinit"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}

    res_obj =  dbh[collection].find_one({})

    return res_obj["glycan"]






def glycan_search(query_obj, db_obj):




    client = MongoClient('mongodb://localhost:27017')    
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"    
    cache_collection = "c_glycancache"

    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}
    if cache_collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}



    field_grp1 = ["query_type", "operation", "glytoucan_ac", "glycan_motif", 
                    "uniprot_canonical_ac","glycan_type", "glycan_subtype"]
    field_grp2 = ["mass", "number_monosaccharides"]
    field_grp3 = ["enzyme"]
    field_grp4 = ["tax_id"]
    #check if submitted fields are allowed and contain valid values
    field_list = field_grp1 + field_grp2 + field_grp3 + field_grp4
    max_query_value_len = 1000
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    flag_list = []
    for field in query_obj:
        if field in ["query_type", "operation"]:
            continue
        if field in field_grp1:
            flag_list.append(query_obj[field] != "")
        elif field in field_grp2 + field_grp3:
            flag_list.append(query_obj[field] != {})
        elif field in field_grp4:
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
                if field2 not in ["type", "id"]:
                    return {"error_code":"unexpected-field-in-query"}
                if len(str(query_obj[field1][field2])) > max_query_value_len:
                    return {"error_code":"invalid-parameter-value-length"}

    for field1 in field_grp1:
        if field1 not in query_obj:
		continue
	if field1 in ["query_type", "operation"]:
            query_obj.pop(field1)
        elif str(query_obj[field1]).strip() == "":
            query_obj.pop(field1)

    for field1 in field_grp2 + field_grp3:
        if field1 not in query_obj:
                continue
	if query_obj[field1] == {}:
            query_obj.pop(field1)

    mongo_query = get_mongo_query(query_obj)


    results = []
    for obj in dbh[collection].find(mongo_query):
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


        number_monosaccharides = obj["number_monosaccharides"] if "number_monosaccharides" in obj else -1
        iupac = obj["iupac"] if "iupac" in obj else ""
        glycoct = obj["glycoct"] if "glycoct" in obj else ""

        results.append({
            "glytoucan_ac":glytoucan_ac
            ,"mass": mass 
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
        search_results_obj = {}
        search_results_obj["list_id"] = list_id
        search_results_obj["query"] = query_obj
        search_results_obj["query"]["execution_time"] = ts
        search_results_obj["results"] = results
        result = dbh[cache_collection].delete_many({"list_id":list_id})
        result = dbh[cache_collection].insert_one(search_results_obj)
        res_obj["list_id"] = list_id

    return res_obj


def glycan_list(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    cache_collection = "c_glycancache"
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


    default_hash = {"offset":1, "limit":20, "sort":"glytoucan_ac", "order":"asc"}
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


def glycan_detail(query_obj, db_obj):


    client = MongoClient('mongodb://localhost:27017')
    dbh = client[db_obj["dbname"]]
    collection = "c_glycan"
    if collection not in dbh.collection_names():
        return {"error_code": "open-connection-failed"}


    #check if submitted fields are allowed and contain valid values
    field_list = ["glytoucan_ac"]
    max_query_value_len = 1000
    for field in query_obj:
        if field not in field_list:
            return {"error_code":"unexpected-field-in-query"}
        if len(str(query_obj[field])) > max_query_value_len:
            return {"error_code":"invalid-parameter-value-length"}

    mongo_query = {"glytoucan_ac":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}}
    obj = dbh[collection].find_one(mongo_query)
    if obj == None:
        return {"error_code":"non-existent-record"}

    keys_to_remove = ["_id", "number_monosaccharides"]
    for key in keys_to_remove:
        if key in obj:
            obj.pop(key)

    return order_obj(obj) 


def glycan_image(query_obj, path_obj):

        img_file = path_obj["glycanimagespath"] +   query_obj["glytoucan_ac"].upper() +".png"
        if os.path.isfile(img_file) == False:
            img_file = path_obj["glycanimagespath"] +  "G0000000.png"
        return img_file

        #data_uri = open(img_file, 'rb').read().encode('base64').replace('\n', '')
        #img_tag = '<img src="data:image/png;base64,{0}">'.format(data_uri)
        #return img_tag



def get_mongo_query(query_obj):

    cond_objs = []
    #glytoucan_ac
    if "glytoucan_ac" in query_obj:
        cond_objs.append({"glytoucan_ac":{'$regex': query_obj["glytoucan_ac"], '$options': 'i'}})

    #mass
    if "mass" in query_obj:
        if "min" in query_obj["mass"]:
            cond_objs.append({"mass":{'$gte': query_obj["mass"]["min"]}})
        if "max" in query_obj["mass"]:
            cond_objs.append({"mass":{'$lte': query_obj["mass"]["max"]}})
    
    #number_monosaccharides
    if "number_monosaccharides" in query_obj:
        if "min" in query_obj["number_monosaccharides"]:
            cond_objs.append({"number_monosaccharides":{'$gte': query_obj["number_monosaccharides"]["min"]}})
        if "max" in query_obj["number_monosaccharides"]:
            cond_objs.append({"number_monosaccharides":{'$lte': query_obj["number_monosaccharides"]["max"]}})

    #organism
    if "tax_id" in query_obj:
        if query_obj["tax_id"] > 0:
            cond_objs.append({"species.taxid": {'$eq': query_obj["tax_id"]}})

    #uniprot_canonical_ac
    if "uniprot_canonical_ac" in query_obj:
        cond_objs.append({"glycoprotein.uniprot_canonical_ac": {'$regex': query_obj["uniprot_canonical_ac"], '$options': 'i'}})

    #glycan_motif
    if "glycan_motif" in query_obj:
        cond_objs.append({"motifs.name": {'$regex': query_obj["glycan_motif"], '$options': 'i'}}) 

    #glycan_type 
    if "glycan_type" in query_obj:
        cond_objs.append({"classification.type.name": {'$regex': query_obj["glycan_type"], '$options': 'i'}})

    #glycan_subtype
    if "glycan_subtype" in query_obj:
        cond_objs.append({"classification.subtype.name": {'$regex': query_obj["glycan_subtype"], 
                                                            '$options': 'i'}})
    #enzyme
    if "enzyme" in query_obj:
        if "id" in query_obj["enzyme"]:
            cond_objs.append({"enzyme.gene": {'$regex': query_obj["enzyme"]["id"], '$options': 'i'}})


    mongo_query = {} if cond_objs == [] else { "$and": cond_objs }
    return mongo_query



def dump_debug_log(out_string):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return


def sort_objects(obj_list, field_name, order_type):

    seen = {"glytoucan_ac":{}, "mass":{}, "number_proteins":{}, "number_monosaccharides":{}, 
            "number_enzymes":{}, "iupac":{}, "glycoct":{}, "wurcs":{}}
    grid_obj = {"glytoucan_ac":[], "mass":[], "number_proteins":[], "number_monosaccharides":[], 
            "number_enzymes":[], "iupac":[], "glycoct":[], "wurcs":[]}
  

    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        glytoucan_ac = obj["glytoucan_ac"]
        if field_name in ["mass"] and field_name in obj:
            grid_obj[field_name].append({"index":i, field_name:float(obj[field_name])})
        elif field_name in ["glytoucan_ac"]:
            grid_obj[field_name].append({"index":i, field_name:obj["glytoucan_ac"]})
        elif field_name in ["iupac", "glycoct", "wurcs"]:
            grid_obj[field_name].append({"glytoucan_ac":i, field_name:obj[field_name]})
        elif field_name in ["number_proteins", "number_monosaccharides", "number_enzymes"] and field_name in obj:
            grid_obj[field_name].append({"index":i, field_name:int(obj[field_name])})

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
