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
import collections

import errorlib
import util


def search_init(config_obj):
    
    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    collection = "c_searchinit"
    doc =  dbh[collection].find_one({})
    cache_dict = {}
    if doc != None:
        if "supersearch_init" in doc:
            cache_dict = doc["supersearch_init"]
    
    typeahead_dict = json.loads(open("./conf/typeahead.json", "r").read())

    enum_dict = {}
    load_enum(dbh,enum_dict, "glycan_classification")
    for f in ["glycosylation_flag", "snv_flag", "phosphorylation_flag", "mutagenesis_flag"]:
        enum_dict[f] = ["true", "false"] 
    for f in ["fully_determined"]:
        enum_dict[f] = ["yes", "no"]

    path_dict = {}
    for doc in dbh["c_path"].find({}):
        record_type = doc["record_type"]
        if record_type not in path_dict:
            path_dict[record_type] = []
        path_dict[record_type].append(doc)



    init_dict = {}
    for record_type in config_obj["record_type_info"]:
        label = config_obj["record_type_info"][record_type]["concept_label"]
        init_dict[record_type] = {"id":record_type, "label":label,"description":"","fields":[]}
    
    for record_type in init_dict:
        label = config_obj["record_type_info"][record_type]["concept_label"]
        init_dict[record_type]["description"] = "GlyGen %s Concept" % (label)
        init_dict[record_type]["record_count"] = 0
        init_dict[record_type]["list_id"] = ""
        if record_type in cache_dict:
            init_dict[record_type]["record_count"] = cache_dict[record_type]["result_count"]
            init_dict[record_type]["list_id"] = cache_dict[record_type]["list_id"]
            init_dict[record_type]["bylinkage"] = cache_dict[record_type]["bylinkage"]

    seen_field = {}
    for record_type in path_dict:
        field_list = []
        field_len_dict = {}
        order_dict = {}
        label_dict = {}
        for path_obj in path_dict[record_type]:
            f_name = path_obj["path"]
            field_len_dict[f_name] = path_obj["maxlen"]
            order_dict[f_name] = path_obj["order"]
            label_dict[f_name] = path_obj["label"]
        for path_obj in path_dict[record_type]:
            f_name = path_obj["path"]
            f_type = path_obj["type"]
            f_name_mapped = ""
            array_map_flag = False
            if record_type in config_obj["path_map"]:
                if config_obj["path_map"][record_type] != {}:
                    if "list_fields" in config_obj["path_map"][record_type]:
                        if f_name in config_obj["path_map"][record_type]["list_fields"]:
                            array_map_flag = True
                    for new_f_name in config_obj["path_map"][record_type]:
                        if new_f_name == "list_fields":
                            continue
                        if f_name in config_obj["path_map"][record_type][new_f_name]["targetlist"]:
                            f_name_mapped = new_f_name
                            break
            if f_type == "list" and array_map_flag == False:
                continue
            f_type = "unicode" if array_map_flag == True else f_type
            #if f_name_mapped != "" and f_name_mapped != f_name:
            #    continue

            f_name = f_name  if f_name_mapped == "" else f_name_mapped
            label = label_dict[f_name] if f_name in label_dict else path_obj["label"]
            ordr = order_dict[f_name] if f_name in  order_dict else path_obj["order"]
            combo_id = "%s|%s|%s|%s" % (f_name, f_type, label, ordr)
            if combo_id not in field_list:
                field_list.append(combo_id)


        for combo_id in field_list:
            f_name, f_type, f_label,f_order = combo_id.split("|")
            max_len = field_len_dict[f_name] if f_name in field_len_dict else 2500

            ignore_flag = False
            if record_type in config_obj["ignored_path_list"]:
                if f_name in config_obj["ignored_path_list"][record_type]:
                    ignore_flag = True
            if f_name.split(".")[-1] == "url":
                continue
            if ignore_flag == True:
                continue

            f_label = f_label.replace("Species", "Organism")
            if f_label == "xxx":
                w_list = []
                for w in f_name.split("."):
                    w_list.append(w[0].upper() + w[1:])
                f_label = " ".join(w_list)
            

            f_type = "string" if f_type == "unicode" else "number"
            op_list = ["$eq","$regex", "$ne"]
            if f_type == "number":
                op_list = ["$eq","$ne", "$gt","$lt","$gte","$lte"]
            enum = enum_dict[f_name] if f_name in enum_dict else []
            url = config_obj["urltemplate"]["glygenwiki"] % (f_name)
            typeahead = ""
            if record_type in typeahead_dict:
                if f_name in typeahead_dict[record_type]:
                    typeahead = typeahead_dict[record_type][f_name]
            f_obj = {
                "id":f_name, 
                "label":f_label, 
                "type":f_type,
                "maxlength":max_len,
                "url":url,
                "oplist":op_list,
                "typeahead":typeahead, 
                "enum":enum,
                "order":int(f_order)
            }

            if record_type not in seen_field:
                seen_field[record_type] = {}
            if f_name not in seen_field[record_type]:
                init_dict[record_type]["fields"].append(f_obj)
                seen_field[record_type][f_name] = True


    out_json = []
    for record_type in init_dict:
        out_json.append(init_dict[record_type])
   

    #record_type = "gene"
    #out_json.append(init_dict[record_type])

    simple_json = {}
    for obj in out_json:
        simple_json[obj["label"]] = []
        for o in obj["fields"]:
            simple_json[obj["label"]].append(o["id"] +"|"+o["type"])
    
    
    #return simple_json
    return out_json




def supersearch_search(query_obj, config_obj, reason_flag, empty_search_flag):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    if query_obj == {}:
        query_obj["concept_query_list"] = []
    if empty_search_flag == False:
        error_list = errorlib.get_errors_in_superquery(query_obj["concept_query_list"],config_obj)
        if error_list != []:
            return {"error_list":error_list}


    results_summary_default = {}
    collection = "c_searchinit"
    doc =  dbh[collection].find_one({})
    if doc != None:
        if "supersearch_init" in doc:
            results_summary_default = doc["supersearch_init"]
    


    if empty_search_flag == False and query_obj["concept_query_list"] == []:
        return {"query":[], "results_summary":results_summary_default}

    seen_path = {}
    for doc in dbh["c_path"].find({}):
        
        record_type = doc["record_type"]
        if record_type not in seen_path:
            seen_path[record_type] = {}
        path = doc["path"].split(" ")[0]
        seen_path[record_type][path] = True
        path_parts = path.split(".")
        if len(path_parts) > 1:
            for i in xrange(1, len(path_parts)):
                p = ".".join(path_parts[:i])
                seen_path[record_type][p] = True


    mongo_query = [] 
    error_list = []
    edge_rules = []
    ignore_dict = {}
    if empty_search_flag == False:
        if "ignored_edges" in query_obj:
            edge_rules = query_obj["ignored_edges"]
        else:
            for i in xrange(0, len(query_obj["concept_query_list"])):
                concept = query_obj["concept_query_list"][i]["concept"]
                edge_rules += config_obj["ignored_edges"][concept]

        for o in edge_rules:
            if "source" not in o or "target" not in o or "direction" not in o:
                return {"error_list":[{"error_code":"invalid-ignore-edge-object"}]}
            if o["source"] not in ignore_dict:
                ignore_dict[o["source"]] = {}
            ignore_dict[o["source"]][o["target"]] = True
            if o["direction"] == "both":
                if o["target"] not in ignore_dict:
                    ignore_dict[o["target"]] = {}
                ignore_dict[o["target"]][o["source"]] = True



    for i in xrange(0, len(query_obj["concept_query_list"])):
        q_obj = query_obj["concept_query_list"][i]["query"]
        concept = query_obj["concept_query_list"][i]["concept"]
                
        path_map = {}
        if concept in config_obj["path_map"]:
            path_map = config_obj["path_map"][concept]
        t_query,e_list = transform_query(q_obj, concept, seen_path, path_map)
        mongo_query.append({"query": t_query,"concept":concept})
        error_list += e_list
    
    if error_list != []:
        return {"error_list":error_list}

    DEBUG_FLAG = False

    dump_debug_timer("flag-1 running concept queries", DEBUG_FLAG)

    initial_hit_count = 0
    reason_dict = {}
    initial_hit_dict = {}
    for q_obj in mongo_query:
        record_type = q_obj["concept"]
        coll = "c_" + record_type
        if record_type == "gene":
            coll = "c_protein"
            q_obj["query"] = {"$and":[q_obj["query"], {"gene": {'$gt':[]}}]}
        if record_type == "enzyme":
            coll = "c_protein"
            q_obj["query"] = {"$and":[q_obj["query"], {"keywords":"enzyme"}]}
        if record_type not in initial_hit_dict:
            initial_hit_dict[record_type] = {}
        if coll not in config_obj["projectedfields"]:
            continue
        record_id_field = config_obj["record_type_info"][record_type]["field"]
        prj_obj = {record_id_field:1}
        doc_list = list(dbh[coll].find(q_obj["query"],prj_obj))
        #agg_query = [{"$project":{record_id_field:1, "result":{ "$not": [ q_obj["query"] ] }}}]
        #doc_list = list(dbh[coll].aggregate(agg_query))
        #print  record_type, len(doc_list)
        #print q_obj["query"]

        initial_hit_count += len(doc_list)
        for doc in doc_list:
            if record_id_field not in doc:
                continue
            record_id = doc[record_id_field]
            if record_type in ["enzyme", "gene"]:
                record_id = "%s.%s" % (record_type, record_id)
            initial_hit_dict[record_type][record_id] = True
            reason = "hit-in-initial-%s-query" % (record_type)
            add_reason(reason_dict, record_type, record_id, "self", record_id)  


    dump_debug_timer("flag-2 loading network", DEBUG_FLAG)

    record_type_list = config_obj["record_type_info"].keys()


    #Load network
    doc_list = list(dbh["c_network"].find({}))

    final_hit_dict,final_hit_dict_split, conn_dict = {}, {}, {}
    if initial_hit_count > 0:
        final_hit_dict,final_hit_dict_split, conn_dict = load_network_type_III(doc_list, 
                initial_hit_dict, empty_search_flag, ignore_dict, reason_dict)
    else:
        conn_dict = load_conn_dict(doc_list)


    #After imposing edge constraints, some hits cannot be traced
    #these untraceable hits should be removed from final_hit_dict
    impose_edge_constraints_type_I(initial_hit_dict, final_hit_dict, final_hit_dict_split, reason_dict, ignore_dict)

    if reason_flag == True:
        return reason_dict


    #Now, set concept_query_list to be empty list
    if empty_search_flag == True:
        query_obj["concept_query_list"] = []

    res_obj = {"query":query_obj, "results_summary":{}}
    ts_format = "%Y-%m-%d %H:%M:%S %Z%z"
    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime(ts_format)
    cache_coll = "c_cache"
    cachable_list = ["protein","glycan","site"]
    for dst_record_type in record_type_list:
        n = len(final_hit_dict[dst_record_type].keys()) if dst_record_type in final_hit_dict else 0
        list_id = ""
        if dst_record_type in final_hit_dict and dst_record_type in cachable_list:
            record_list = final_hit_dict[dst_record_type].keys()
            if len(record_list) != 0:
                hash_obj = hashlib.md5(dst_record_type + "_" + json.dumps(query_obj))
                list_id = hash_obj.hexdigest()
                cache_info = {
                    "query":query_obj,
                    "ts":ts,
                    "record_type":dst_record_type,
                    "search_type":"supersearch"
                }
                util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
        res_obj["results_summary"][dst_record_type] = {"list_id":list_id, "result_count":n}
        stat_obj = {}
        bylinkage_obj = {}
        if dst_record_type in final_hit_dict_split:
            stat_obj = get_network_stat(final_hit_dict_split[dst_record_type])
        
        #for src_record_type not in stat_obj
        if dst_record_type in conn_dict:
            for src_record_type in conn_dict[dst_record_type]:
                if src_record_type not in stat_obj:
                    if src_record_type in ignore_dict:
                        if dst_record_type in ignore_dict[src_record_type]:
                            continue
                    bylinkage_obj[src_record_type] = {"list_id":"", "result_count":0}
            
        #for src_record_type in stat_obj
        for src_record_type in stat_obj:
            if src_record_type in ignore_dict:
                if dst_record_type in ignore_dict[src_record_type]:
                    continue
            list_id = ""
            if stat_obj[src_record_type] > 0 and dst_record_type in cachable_list:
                record_list = final_hit_dict_split[dst_record_type][src_record_type].keys()
                hash_obj = hashlib.md5(dst_record_type + "_" + src_record_type + "_"+json.dumps(query_obj))
                list_id = hash_obj.hexdigest()
                cache_info = {
                    "query":query_obj,
                    "ts":ts,
                    "record_type":dst_record_type,
                    "linked_to":src_record_type,
                    "search_type":"supersearch"
                }
                util.cache_record_list(dbh,list_id,record_list,cache_info,cache_coll,config_obj)
            n_from_src = stat_obj[src_record_type]
            bylinkage_obj[src_record_type] = {"list_id":list_id, "result_count":n_from_src}
        res_obj["results_summary"][dst_record_type]["bylinkage"] = bylinkage_obj

   
    id_list = []
    for dst_record_type in res_obj["results_summary"]:
        list_id = res_obj["results_summary"][dst_record_type]["list_id"]
        if list_id != "":
            id_list.append(list_id)
        if "bylinkage" in res_obj["results_summary"][dst_record_type]:
            bylinkage_obj = res_obj["results_summary"][dst_record_type]["bylinkage"]
            for src_record_type in bylinkage_obj:
                list_id = bylinkage_obj[src_record_type]["list_id"]
                if list_id != "":
                    id_list.append(list_id)


    for list_id in id_list:
        q_obj = {"list_id":list_id}
        update_obj = {"cache_info.result_summary":res_obj["results_summary"]}
        res = dbh["c_cache"].update_one(q_obj, {'$set':update_obj}, upsert=True)

    return res_obj



def impose_edge_constraints_type_I(initial_hit_dict, final_hit_dict, final_hit_dict_split, reason_dict, ignore_dict):
    traceble_dict = {}
    for dst_record_type in final_hit_dict_split:
        for src_record_type in final_hit_dict_split[dst_record_type]:
            if src_record_type in ignore_dict:
                if dst_record_type in ignore_dict[src_record_type]:
                    continue
            for dst_record_id in final_hit_dict_split[dst_record_type][src_record_type]:
                if dst_record_type not in traceble_dict:
                    traceble_dict[dst_record_type] = {}
                traceble_dict[dst_record_type][dst_record_id] = True


    emptied_concepts = []
    dst_record_type_list = final_hit_dict.keys()
    for dst_record_type in dst_record_type_list:
        if dst_record_type in initial_hit_dict:
            continue
        dst_record_id_list = final_hit_dict[dst_record_type].keys()
        for dst_record_id in dst_record_id_list:
            if dst_record_type not in traceble_dict:
                final_hit_dict[dst_record_type].pop(dst_record_id)
            elif dst_record_id not in traceble_dict[dst_record_type]:
                final_hit_dict[dst_record_type].pop(dst_record_id)
        if final_hit_dict[dst_record_type] == {}:
            final_hit_dict.pop(dst_record_type)
            emptied_concepts.append(dst_record_type)

        
    #clean reason_dict by considering ignored edges
    for dst_record_type in reason_dict:
        dst_record_id_list = reason_dict[dst_record_type].keys()
        for dst_record_id in dst_record_id_list:
            src_record_type_list = reason_dict[dst_record_type][dst_record_id].keys()
            for src_record_type in src_record_type_list:
                if src_record_type in ignore_dict:
                    if dst_record_type in ignore_dict[src_record_type]:
                        reason_dict[dst_record_type][dst_record_id].pop(src_record_type)
            if reason_dict[dst_record_type][dst_record_id] == {}:
                reason_dict[dst_record_type].pop(dst_record_id)
            else:
                #Remove dst_record_id if comes from emptied_concept only
                src_type_list = sorted(reason_dict[dst_record_type][dst_record_id].keys())
                if src_type_list == sorted(emptied_concepts):
                    final_hit_dict[dst_record_type].pop(dst_record_id)
                    for emptied_concept in emptied_concepts:
                        if emptied_concept in final_hit_dict_split[dst_record_type]:
                            final_hit_dict_split[dst_record_type].pop(emptied_concept)
                    #print "flag", final_hit_dict_split["gene"]["protein"].keys()

    return


def load_network_type_I(doc_list, initial_hit_dict, network_dict, edge_dict, linked_record_type_dict):

    for doc in doc_list:
        for obj in doc["recordlist"]:
            src_record_type, src_record_id = obj["record_type"], obj["record_id"]
            if obj["linkeage"] == {}:
                continue
            if src_record_type not in network_dict:
                network_dict[src_record_type] = {}
            network_dict[src_record_type][src_record_id] = obj["linkeage"]
            if src_record_type not in linked_record_type_dict:
                linked_record_type_dict[src_record_type] = {}
            for dst_record_type in network_dict[src_record_type][src_record_id]:
                #Remove these edges for now
                if [src_record_type, dst_record_type] == ["site", "species"]:
                    continue
                if [src_record_type, dst_record_type] == ["species", "site"]:
                    continue
                linked_record_type_dict[src_record_type][dst_record_type] = True
                for dst_record_id in network_dict[src_record_type][src_record_id][dst_record_type]:
                    src_node = "%s %s" % (src_record_type,src_record_id)
                    dst_node = "%s %s" % (dst_record_type,dst_record_id)
                    if src_node not in edge_dict:
                        edge_dict[src_node] = {}
                    edge_dict[src_node][dst_node] = True
    return


def load_network_type_II(doc_list, initial_hit_dict, empty_search_flag, config_obj, reason_dict):



    edge_dict = {}
    orphan_dict = {}
    for doc in doc_list:
        for obj in doc["recordlist"]:
            src_record_type, src_record_id = obj["record_type"], obj["record_id"]
            src_node = "%s %s" % (src_record_type, src_record_id)
            if obj["linkeage"] == {}:
                if src_record_type not in orphan_dict:
                    orphan_dict[src_record_type] = {}
                orphan_dict[src_record_type][src_record_id] = True
            else:
                for dst_record_type in obj["linkeage"]:
                    for dst_record_id in obj["linkeage"][dst_record_type]:
                        dst_node = "%s %s" % (dst_record_type, dst_record_id)
                        if src_record_type not in edge_dict:
                            edge_dict[src_record_type] = {}
                        if src_record_id not in edge_dict[src_record_type]:
                            edge_dict[src_record_type][src_record_id] = {}
                        if dst_record_type not in edge_dict[src_record_type][src_record_id]:
                            edge_dict[src_record_type][src_record_id][dst_record_type] = {}
                        edge_dict[src_record_type][src_record_id][dst_record_type][dst_record_id] = True


    record_type_list = initial_hit_dict.keys()
    for record_type in edge_dict:
        if record_type not in record_type_list:
            record_type_list.append(record_type)

    node_hit_dict = {}
    edge_hit_dict = {}
    for src_record_type in record_type_list:
        for src_record_id in edge_dict[src_record_type]:
            # if empty query search, add all src nodes including unlinked ones
            if empty_search_flag == True and src_record_type in orphan_dict:
                if src_record_type not in node_hit_dict:
                    node_hit_dict[src_record_type] = {}
                node_hit_dict[src_record_type][src_record_id] = True
            
            if empty_search_flag == False:
                if filtered_out_flag_type_I(initial_hit_dict,src_record_type,src_record_id):
                    continue

            for dst_record_type in edge_dict[src_record_type][src_record_id]:
                for dst_record_id in edge_dict[src_record_type][src_record_id][dst_record_type]:
                    if empty_search_flag == False:
                        
                        if filtered_out_flag_type_I(initial_hit_dict,dst_record_type,dst_record_id):
                            #node (dst_record_type,dst_record_id) is filtered out
                            continue
                    init_flag = False
                    if dst_record_type in initial_hit_dict:
                        if dst_record_id in initial_hit_dict[dst_record_type]:
                            init_flag = True
                    if init_flag == False:
                        add_reason(reason_dict, dst_record_type, dst_record_id, src_record_type, src_record_id)


                    # at this point both src node (src_record_type, src_record_id) and 
                    # dst node (dst_record_type,dst_record_id) are not filtered out
                    
                    # adding src node (src_record_type,src_record_id) to node_hit_dict
                    if src_record_type not in node_hit_dict:
                        node_hit_dict[src_record_type] = {}
                    node_hit_dict[src_record_type][src_record_id] = True
                    
                    # adding dst node (dst_record_type,dst_record_id) to node_hit_dict
                    if dst_record_type not in node_hit_dict:
                        node_hit_dict[dst_record_type] = {}
                    node_hit_dict[dst_record_type][dst_record_id] = True
                    e_lbl = "[%s:%s <-> %s:%s]"
                    e_lbl = e_lbl % (src_record_type,src_record_id,dst_record_type,dst_record_id)
                    #if "site" in [src_record_type]:
                    #    print "considering edge ", e_lbl

                    if dst_record_type not in edge_hit_dict:
                        edge_hit_dict[dst_record_type] = {}
                    if src_record_type not in edge_hit_dict[dst_record_type]:
                        edge_hit_dict[dst_record_type][src_record_type] = {}
                    edge_hit_dict[dst_record_type][src_record_type][dst_record_id] = True


    return node_hit_dict, edge_hit_dict



def load_conn_dict(doc_list):

    conn_dict = {}
    for doc in doc_list:
        for obj in doc["recordlist"]:
            src_record_type, src_record_id = obj["record_type"], obj["record_id"]
            src_node = "%s %s" % (src_record_type, src_record_id)
            for dst_record_type in obj["linkeage"]:
                if src_record_type not in conn_dict:
                    conn_dict[src_record_type] = {}
                if dst_record_type not in conn_dict[src_record_type]:
                    conn_dict[src_record_type][dst_record_type] = True

    return conn_dict




def load_network_type_III(doc_list, initial_hit_dict, empty_search_flag, ignore_dict,reason_dict):


    conn_dict = {}
    edge_dict = {}
    orphan_dict = {}
    for doc in doc_list:
        for obj in doc["recordlist"]:
            src_record_type, src_record_id = obj["record_type"], obj["record_id"]
            src_node = "%s %s" % (src_record_type, src_record_id)
            if obj["linkeage"] == {}:
                if src_record_type not in orphan_dict:
                    orphan_dict[src_record_type] = {}
                orphan_dict[src_record_type][src_record_id] = True
            else:
                for dst_record_type in obj["linkeage"]:
                    if src_record_type not in conn_dict:
                        conn_dict[src_record_type] = {}
                    if dst_record_type not in conn_dict[src_record_type]:
                        conn_dict[src_record_type][dst_record_type] = True
                    
                    #If edge is ignored, continue
                    if src_record_type in ignore_dict:
                        if dst_record_type in ignore_dict[src_record_type]:
                            continue

                    for dst_record_id in obj["linkeage"][dst_record_type]:
                        dst_node = "%s %s" % (dst_record_type, dst_record_id)
                        if src_record_type not in edge_dict:
                            edge_dict[src_record_type] = {}
                        if src_record_id not in edge_dict[src_record_type]:
                            edge_dict[src_record_type][src_record_id] = {}
                        if dst_record_type not in edge_dict[src_record_type][src_record_id]:
                            edge_dict[src_record_type][src_record_id][dst_record_type] = {}
                        edge_dict[src_record_type][src_record_id][dst_record_type][dst_record_id] = True


    record_type_list = initial_hit_dict.keys()
    for record_type in edge_dict:
        if record_type not in record_type_list:
            record_type_list.append(record_type)


    #node_hit_dict = initial_hit_dict
    node_hit_dict = {}
    edge_hit_dict = {}
 
    #add nodes in initial_hit_dict to node_hit_dict
    for src_record_type in initial_hit_dict:
        for src_record_id in initial_hit_dict[src_record_type]:
            if src_record_type not in node_hit_dict:
                node_hit_dict[src_record_type] = {}
            node_hit_dict[src_record_type][src_record_id] = True



    for src_record_type in record_type_list:
        for src_record_id in edge_dict[src_record_type]:

            # if empty query search, add all src nodes including unlinked ones
            if empty_search_flag == True and src_record_type in orphan_dict:
                if src_record_type not in node_hit_dict:
                    node_hit_dict[src_record_type] = {}
                node_hit_dict[src_record_type][src_record_id] = True

            if empty_search_flag == False:
                # any outgoing link/edge passes this step if src node has not been filtered out
                # or the src node has already made it to the node_hit_dict
                if filtered_out_flag_type_I(initial_hit_dict,src_record_type,src_record_id):
                    continue
                elif src_record_type in node_hit_dict:
                    if src_record_id not in node_hit_dict[src_record_type]:
                        continue


            for dst_record_type in edge_dict[src_record_type][src_record_id]:
                # ignore edges in the ignore dict
                if empty_search_flag == False:
                    if src_record_type in ignore_dict:
                        if dst_record_type in ignore_dict[src_record_type]:
                            continue
                    
                for dst_record_id in edge_dict[src_record_type][src_record_id][dst_record_type]:
                    if empty_search_flag == False:
                        # link/edge passes this step only if dst node has not been filtered out
                        # or the src node has already made it to the node_hit_dict
                        if filtered_out_flag_type_I(initial_hit_dict,dst_record_type,dst_record_id):
                            continue
                        elif src_record_type in node_hit_dict:
                            if src_record_id not in node_hit_dict[src_record_type]:
                                continue

                    init_flag = False
                    if dst_record_type in initial_hit_dict:
                        if dst_record_id in initial_hit_dict[dst_record_type]:
                            init_flag = True

                    #skip if src-to-dst edge is ignored
                    if src_record_type in ignore_dict:
                        if dst_record_type in ignore_dict[src_record_type]:
                            continue

                    # at this point both src node (src_record_type, src_record_id) and 
                    # dst node (dst_record_type,dst_record_id) are not filtered out
                    
                    src_node = "%s:%s" % (src_record_type,src_record_id)
                    dst_node = "%s:%s" % (dst_record_type,dst_record_id)
                    quad_id = "%s -> %s" % (src_node, dst_node)
                    
                    # adding src_node to node_hit_dict
                    if src_record_type not in node_hit_dict:
                        node_hit_dict[src_record_type] = {}
                    node_hit_dict[src_record_type][src_record_id] = True

                    # adding src_node to edge_hit_dict
                    if src_record_type not in edge_hit_dict:
                        edge_hit_dict[src_record_type] = {}
                    if dst_record_type not in edge_hit_dict[src_record_type]:
                        edge_hit_dict[src_record_type][dst_record_type] = {}
                    edge_hit_dict[src_record_type][dst_record_type][src_record_id] = True
                    # adding src_node to reason_dict
                    if init_flag == False:
                        add_reason(reason_dict, src_record_type, src_record_id, dst_record_type, dst_record_id)
                        #print "flag", quad_id, reason                                                                                        
                    # adding dst_node to node_hit_dict
                    if dst_record_type not in node_hit_dict:
                        node_hit_dict[dst_record_type] = {}
                    node_hit_dict[dst_record_type][dst_record_id] = True
                    # adding dst_node to edge_hit_dict
                    if dst_record_type not in edge_hit_dict:
                        edge_hit_dict[dst_record_type] = {}
                    if src_record_type not in edge_hit_dict[dst_record_type]:
                        edge_hit_dict[dst_record_type][src_record_type] = {}
                    edge_hit_dict[dst_record_type][src_record_type][dst_record_id] = True
                    # adding dst_node to reason_dict
                    if init_flag == False:
                        add_reason(reason_dict, dst_record_type, dst_record_id, src_record_type, src_record_id)



    return node_hit_dict, edge_hit_dict, conn_dict





def filtered_out_flag_type_I(initial_hit_dict, record_type, record_id):


    if record_type in initial_hit_dict:
        if record_id not in initial_hit_dict[record_type]:
            return True

    return False


def filtered_out_flag_type_II(initial_hit_dict, node_hit_dict, record_type, record_id):
    
    #flag_one = filtered_out_flag_type_I(initial_hit_dict, record_type, record_id)
    flag_one = True
    if record_type in initial_hit_dict:
        if record_id in initial_hit_dict[record_type]:
            flag_one = False
    flag_two = True
    if record_type in node_hit_dict: 
        if record_id in node_hit_dict[record_type]:
            flag_two = False
    
    if flag_one == True and flag_two == True:
        return True

    return False


















def get_network_stat(network_dict):
   
    o = {}
    for record_type in network_dict:
        o[record_type] = len(network_dict[record_type].keys())
    return o


def get_hit_stat(hit_dict):

    seen = {}
    for record_type in hit_dict:
        for record_id in hit_dict[record_type]:
            if record_type not in seen:
                seen[record_type] = {}
            seen[record_type][record_id] = True
    o = {}
    for record_type in seen:
        o[record_type] = len(seen[record_type].keys())
    return o




def load_properity_lineage(in_obj, in_key, seen):

    if type(in_obj) in [dict, collections.OrderedDict]:
        for k in in_obj:
            new_key = in_key + "." + k if in_key != "" else k
            load_properity_lineage(in_obj[k], new_key, seen)
    elif type(in_obj) is list:
        for o in in_obj:
            load_properity_lineage(o, in_key, seen)
    elif type(in_obj) in [unicode, int, float]:
        value_type = str(type(in_obj)).replace("<type ", "").replace("'", "").replace(">", "")
        in_key += " %s" % (value_type)
        if in_key not in seen:
            seen[in_key] = True

    return 




def load_enum(dbh, enum_dict, case):
    
    if case == "glycan_classification":
        field_one = "classification.type.name"
        field_two = "classification.subtype.name"
        enum_dict[field_one], enum_dict[field_two] = [], []
        for doc in dbh["c_glycan"].find({}, {"classification":1}):
            for o in doc["classification"]:
                if o["type"]["name"] not in enum_dict[field_one]:
                    enum_dict[field_one].append(o["type"]["name"])
                if o["subtype"]["name"] not in enum_dict[field_two]:
                    enum_dict[field_two].append(o["subtype"]["name"])

    return





def transform_query(in_obj, concept, seen_path, path_map):
    q_list = []
    error_list = []
    if "unaggregated_list" in in_obj:
        for obj in in_obj["unaggregated_list"]:
            if concept not in seen_path:
                error_obj = {"error_code": "unknown-concept", "concept":concept}
                error_list.append(error_obj)
            elif obj["path"] not in path_map and obj["path"] not in seen_path[concept]:
                error_obj = {"error_code": "unknown-path", 
                        "concept":concept, "path":obj["path"]}
                error_list.append(error_obj)
            else:
                if "string_value" in obj:
                    if obj["string_value"] in [True, False]:
                        obj["string_value"] = str(obj["string_value"]).lower()

                val = obj["string_value"] if "string_value" in obj else obj["numeric_value"]
                val_obj = {obj["operator"]:val}
                if obj["operator"] == "$eq" and "string_value" in obj:
                    val = "^%s$" % (val)
                    val_obj = {"$regex":val, "$options":"i"}
                elif obj["operator"] == "$ne" and "string_value" in obj:
                    val = "^%s$" % (val)
                    val_obj = {"$not": {"$regex":val, "$options":"i"}}
                elif obj["operator"] == "$regex":
                    val_obj = {"$regex":val, "$options":"i"}

                o = {obj["path"]:val_obj}
                if obj["path"] in path_map:
                    local_agg = "$and" if obj["operator"] in ["$ne"] else "$or"
                    o = {local_agg:[]}
                    for new_path in path_map[obj["path"]]["targetlist"]:
                        new_o = {new_path:val_obj}
                        o[local_agg].append(new_o)
                    if "list_fields" in path_map:
                        if new_path in path_map["list_fields"]:
                            val_obj = {"$gt":[]} if obj["string_value"] == "true" else {"$eq":[]} 
                            o = {new_path:val_obj}
                q_list.append(o)
        
    if "aggregated_list" in in_obj:
        for i in xrange(0, len(in_obj["aggregated_list"])):
            child_obj = in_obj["aggregated_list"][i]
            o = transform_query(child_obj, concept, seen_path, path_map)
            q_list.append(o)

    in_obj = {in_obj["aggregator"]:q_list} if q_list != [] else {}


    return in_obj, error_list



def add_reason(reason_dict, dst_record_type, dst_record_id, src_record_type, src_record_id):

    if dst_record_type not in reason_dict:
        reason_dict[dst_record_type] = {}
    if dst_record_id not in reason_dict[dst_record_type]:
        reason_dict[dst_record_type][dst_record_id] = {}
    if src_record_type not in reason_dict[dst_record_type][dst_record_id]:
        reason_dict[dst_record_type][dst_record_id][src_record_type] = {}
    reason_dict[dst_record_type][dst_record_id][src_record_type][src_record_id] = True

    return

def dump_debug_timer(flag,debug_flag):

    if debug_flag == True:
        print datetime.datetime.now(), flag

    return





