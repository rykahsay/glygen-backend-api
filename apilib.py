import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict



def glycan_search_init(glycandb_obj, error_obj):
                        
    res_obj = {"glycan_mass":{}, "number_monosaccharides":{}, 
                "organism":[], "glycan_type":[]}
    min_mass = 10000000.0
    max_mass = -min_mass
    min_monosaccharides = 100000
    max_monosaccharides = -min_monosaccharides

    seen = {"glycan_type":{}, "organism":{}}
    for glycan_id in glycandb_obj:
        obj = glycandb_obj[glycan_id]
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


def glycan_typehead(glycandb_obj, query_obj, path_obj, error_obj):

    if "field" not in query_obj:
        return error_obj["LIBTYPHEAD01"]
    if "value" not in query_obj:
        return error_obj["LIBTYPHEAD02"]


    res_obj = []
    for glycan_id in glycandb_obj:
        obj = glycandb_obj[glycan_id]
        if query_obj["field"] == "enzyme":
            if "enzyme" in obj:
                for o in obj["enzyme"]:
                    if o["protein_id"].lower().find(query_obj["value"].lower()) != -1:
                        res_obj.append(o["protein_id"])
        elif query_obj["field"] == "motif":
            if "motifs" in obj:
                for o in obj["motifs"]:
                    if o["name"].lower().find(query_obj["value"].lower()) != -1:
                        res_obj.append(o["name"])
        elif query_obj["field"] == "protein":
            if "glycoprotein" in obj:
                for o in obj["glycoprotein"]:
                    if o["protein_id"].lower().find(query_obj["value"].lower()) != -1:
                        res_obj.append(o["protein_id"])

    return sorted(set(res_obj))



def glycan_search(glycandb_obj, query_obj, path_obj, error_obj):

    results = []
    for glycan_id in glycandb_obj:
	obj = glycandb_obj[glycan_id]
        match_flags = check_search_conditions(obj, query_obj, error_obj)
        if sorted(set(match_flags)) != [True]:
	    continue
	    
        fobj = {}
	for key in obj:
            if type(obj[key]) is list and len(obj[key]) > 0:
                fobj[key] = obj[key]
            elif isinstance(obj[key], basestring) and obj[key].strip() != "":
                fobj[key] = obj[key]
        #results[glycan_id] = fobj
        seen = {"protein":{}, "enzyme":{}}
        if "glycoprotein" in obj:
            for xobj in obj["glycoprotein"]:
                seen["protein"][xobj["protein_id"].lower()] = True
        
        if "enzyme" in obj:
            for xobj in obj["enzyme"]:
                seen["enzyme"][xobj["gene"].lower()] = True

        mass = obj["mass"] if "mass" in obj else -1
        number_monosaccharides = obj["number_monosaccharides"] if "number_monosaccharides" in obj else -1
        iupac = obj["iupac"] if "iupac" in obj else ""
        glycoct = obj["glycoct"] if "glycoct" in obj else ""

        results.append({
            "id":glycan_id
            ,"mass": mass 
            ,"number_monosaccharides": number_monosaccharides
            ,"number_proteins": len(seen["protein"].keys()) 
            ,"number_enzymes": len(seen["enzyme"].keys()) 
            ,"iupac": iupac
            ,"glycoct": glycoct
        })

    res_obj = {}
    if len(results) == 0:
        res_obj = {"message":"No results found!"}
    else:
        hash_obj = hashlib.md5(json.dumps(query_obj))
        search_results_id = hash_obj.hexdigest()

        search_results_obj = {}
        search_results_obj["search_results_id"] = search_results_id
        search_results_obj["query"] = query_obj

        gmt_time = time.gmtime()
        gmt_time_to_dt = datetime.datetime.fromtimestamp(time.mktime(gmt_time), tz=pytz.timezone('GMT'))
        gmt_plus = gmt_time_to_dt + datetime.timedelta(minutes = 120)

        search_results_obj["query"]["execution_time"] = str(gmt_plus)
        search_results_obj["results"] = results
        cache_file = path_obj["apicachepath"] + "/" + search_results_id + ".json"
        with open(cache_file, "w") as FW:
            FW.write("%s\n" % (json.dumps(search_results_obj)))
        res_obj["search_results_id"] = search_results_id
        
        cmd = "chmod 777 " + cache_file
        x = commands.getoutput(cmd)


    return res_obj


def glycan_list(cached_obj, query_obj, path_obj, error_obj):

    res_obj = {}
    sorted_id_list = sort_objects(cached_obj["results"], query_obj["sort"], query_obj["order"], error_obj)
    res_obj = {"query":cached_obj["query"]}

    if len(cached_obj["results"]) == 0:
        return {}
    if int(query_obj["offset"]) < 1 or int(query_obj["offset"]) > len(cached_obj["results"]):
	return error_obj["LIBGLIST01"]

    start_index = int(query_obj["offset"]) - 1
    stop_index = start_index + int(query_obj["limit"])
    res_obj["results"] = []

    for obj_id in sorted_id_list[start_index:stop_index]:
        obj = cached_obj["results"][obj_id]
        res_obj["results"].append(order_obj(obj, error_obj))

    res_obj["pagination"] = {"offset":query_obj["offset"], "limit":query_obj["limit"],
        "total_length":len(cached_obj["results"]), "sort":query_obj["sort"], "order":query_obj["order"]}
    return res_obj


def glycan_detail(glycandb_obj, query_obj, error_obj):

    res_obj = {}
    glycan_id = query_obj["id"]
    if glycan_id not in glycandb_obj:
        return error_obj["LIBGDETAIL01"]

    obj = glycandb_obj[glycan_id]
    if "number_monosaccharides" in obj:
        obj.pop("number_monosaccharides")

    return obj


def glycan_image(query_obj, path_obj, error_obj):

        img_file = path_obj["glycanimagespath"] +   query_obj["id"].upper() +".png"
        if os.path.isfile(img_file) == False:
            img_file = path_obj["glycanimagespath"] +  "G0000000.png"
        
        return img_file

        #data_uri = open(img_file, 'rb').read().encode('base64').replace('\n', '')
        #img_tag = '<img src="data:image/png;base64,{0}">'.format(data_uri)
        #return img_tag


def auth_userid(path_obj, error_obj):

    useriddb_file = path_obj["useriddbpath"]
    useriddb_obj = json.loads(open(useriddb_file, "r").read())
                            
    gmt_time = time.gmtime()
    gmt_time_to_dt = datetime.datetime.fromtimestamp(time.mktime(gmt_time), tz=pytz.timezone('GMT'))
    gmt_plus = str(gmt_time_to_dt + datetime.timedelta(minutes = 120))

    res_obj = {}
    i = 0
    while True:
        rstr = get_random_string(32).lower()
        if rstr not in useriddb_obj:
            res_obj = {"user":rstr}
            useriddb_obj[rstr] = {"created_ts":gmt_plus}
            with open(useriddb_file, "w") as FW:
                FW.write("%s\n" % (json.dumps(useriddb_obj, indent=4) ))
            return res_obj
        if i > 100000:
            return error_obj["LIBAUTHUSERID01"]        
        i += 1


def auth_logging(query_obj, path_obj, error_obj):

	res_json = {"status":"success"}
        
	logdb_file = path_obj["logdbpath"]
    	logdb_obj = json.loads(open(logdb_file, "r").read())
	logdb_obj.append(query_obj)
	with open(logdb_file, "w") as FW:
		FW.write("%s\n" % (json.dumps(logdb_obj, indent=4)))

	return res_json


def dump_debug_log(out_string, error_obj):

    debug_log_file = path_obj["debuglogfile"]
    with open(debug_log_file, "a") as FA:
        FA.write("\n\n%s\n" % (out_string))
    return


def sort_objects(obj_list, field_name, order_type, error_obj):

    seen = {"id":{}, "mass":{}, "number_proteins":{}, "number_monosaccharides":{}, 
            "number_enzymes":{}, "iupac":{}, "glycoct":{}, "wurcs":{}}
    grid_obj = {"id":[], "mass":[], "number_proteins":[], "number_monosaccharides":[], 
            "number_enzymes":[], "iupac":[], "glycoct":[], "wurcs":[]}
  

    for i in xrange(0, len(obj_list)):
        obj = obj_list[i]
        glycan_id = obj["id"]
        if field_name in ["mass"] and field_name in obj:
            grid_obj[field_name].append({"index":i, field_name:float(obj[field_name])})
        elif field_name in ["id"]:
            grid_obj[field_name].append({"index":i, field_name:obj["id"]})
        elif field_name in ["iupac", "glycoct", "wurcs"]:
            grid_obj[field_name].append({"id":i, field_name:obj[field_name]})
        elif field_name in ["number_proteins", "number_monosaccharides", "number_enzymes"] and field_name in obj:
            grid_obj[field_name].append({"index":i, field_name:int(obj[field_name])})

    reverse_flag = True if order_type == "desc" else False
    key_list = []
    sorted_obj_list = sorted(grid_obj[field_name], key=lambda x: x[field_name], reverse=reverse_flag)
    for o in sorted_obj_list:
            key_list.append(o["index"])
    return key_list



def order_obj(jsonObj, error_obj):

    ordrHash = {"id":1, "mass":2, "iupac":3, "wurcs":4, "glycoct":5,
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



def check_search_conditions(obj, query_obj, error_obj): 


    matches = []
    for key in query_obj:
        if key == "glycan_id":
            matches.append(obj["id"].lower().find(query_obj[key].lower()) != -1)
	elif key == "mass":
            if "mass" in obj:
                min_mass = query_obj[key]["min"] if "min" in query_obj[key] else 0
                max_mass = query_obj[key]["max"] if "max" in query_obj[key] else 10000000
                c1 = float(obj["mass"])  >= float(min_mass)
                c2 = float(obj["mass"])  <= float(max_mass)
                matches.append( c1 and c2)
        elif key == "glycan_type":
            matchList = []
            for o in obj["classification"]:
                matchList.append(o["type"]["name"].lower().find(query_obj[key].lower()) != -1)
            matches.append(True in matchList)
        elif key == "glycan_subtype":
            matchList = []                                                  
            if "classification" in obj:
                for o in obj["classification"]:
                    matchList.append(o["subtype"]["name"].lower().find(query_obj[key].lower()) != -1)
                matches.append(True in matchList)
        elif key == "organism":
            matchList = []
            if "species" in obj:
                for o in obj["species"]: 
                    matchList.append(o["name"].lower().find(query_obj[key].lower()) != -1)
                matches.append(True in matchList)
        elif key == "protein":
            matchList = []
            if "glycoprotein" in obj:
                for o in obj["glycoprotein"]:
                    matchList.append(o["protein_id"].lower().find(query_obj[key].lower()) != -1)
                matches.append(True in matchList)
        elif key == "enzyme":
            matchList = []
            if "enzyme" in obj:
                if "id" in query_obj[key]:
                    for o in obj["enzyme"]:
                        matchList.append(o["gene"].lower().find(query_obj[key]["id"].lower()) != -1)
                    matches.append(True in matchList)
        #elif key == "glycan_motif":
        #    matches[key] = False;
    return matches


def get_random_string(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def get_error_obj(error_code, error_log, error_msg, path_obj, error_obj):
    log_file = path_obj["apierrorlogpath"] + "/" + error_code + "-" + get_random_string(6) + ".log"
    with open(log_file, "w") as FW:
        FW.write("%s" % (error_log))
    return {"code": error_code, "message": error_msg}






