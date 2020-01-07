import os
import string
import json
import util



def get_errors_in_query(svc_name, query_obj, config_obj):

    for key1 in query_obj:
        if type(query_obj[key1]) in [str, unicode]:
            query_obj[key1] = query_obj[key1].strip()
        elif type(query_obj[key1]) is dict:
            for key2 in query_obj[key1]:
                if type(query_obj[key1][key2]) in [str, unicode]:
                    query_obj[key1][key2] = query_obj[key1][key2].strip()




    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    field_info = config_obj[svc_name]["field_info"]
    collection_list = config_obj[svc_name]["collectionlist"]
    max_query_value_len = config_obj["max_query_value_len"]

    error_list = []
    for coll in collection_list:
        if coll not in dbh.collection_names():
            error_list.append({"error_code": "missing-collection", "collection":coll})

    for key1 in query_obj:
        if key1 not in field_info:
            error_list.append({"error_code":"unexpected-field-in-query", "field":key1})
        else:
            if type(query_obj[key1]) is dict:
                for key2 in query_obj[key1]:
                    if key2 not in field_info[key1]:
                        error_list.append({"error_code":"unexpected-field-in-query", "field":key2})
                    elif "type" in field_info[key1][key2]:
                        combo_key = "%s.%s" % (key1, key2)
                        val_type = ""
                        val_type = "string" if type(query_obj[key1][key2]) in [str, unicode] else val_type
                        val_type = "number" if type(query_obj[key1][key2]) in [int, float] else val_type
                        val_type = "boolean" if type(query_obj[key1][key2]) in [bool] else val_type
                        val_type = "list" if type(query_obj[key1][key2]) in [list] else val_type
                        if key2 not in field_info[key1]:
                            error_list.append({"error_code":"unexpected-field-in-query", "field":combo_key})
                        if val_type != field_info[key1][key2]["type"]:
                            error_list.append({"error_code":"invalid-parameter-value", "field":combo_key})
                        if "maxlen" in field_info[key1][key2]:
                            max_query_value_len = field_info[key1][key2]["maxlen"]
                        if len(str(query_obj[key1][key2])) > max_query_value_len:
                            error_list.append({"error_code":"invalid-parameter-value-length", "field":combo_key})
                    else:
                        if type(query_obj[key1][key2]) is dict:
                            for key3 in query_obj[key1][key2]:
                                if "type" in field_info[key1][key2][key3]:
                                    combo_key = "%s.%s.%s" % (key1, key2,key3)
                                    t = query_obj[key1][key2][key3]
                                    val_type = ""
                                    val_type = "string" if type(t) in [str, unicode] else val_type
                                    val_type = "number" if type(t) in [int, float] else val_type
                                    val_type = "boolean" if type(t) in [bool] else val_type
                                    if key3 not in field_info[key1][key2]:
                                        error_list.append({"error_code":"unexpected-field-in-query", 
                                            "field":combo_key})
                                    if val_type != field_info[key1][key2][key3]["type"]:
                                        error_list.append({"error_code":"invalid-parameter-value", "field":combo_key})
                                    if "maxlen" in field_info[key1][key2][key3]:
                                        max_query_value_len = field_info[key1][key2][key3]["maxlen"]
                                    if len(str(query_obj[key1][key2][key3])) > max_query_value_len:
                                        error_list.append({"error_code":"invalid-parameter-value-length", "field":combo_key})
                        elif type(query_obj[key1][key2]) is list:
                            for o in query_obj[key1][key2]:
                                for key3 in o:
                                    if "type" in field_info[key1][key2][key3]:
                                        combo_key = "%s.%s.%s" % (key1, key2,key3)
                                        t = o[key3]
                                        val_type = ""
                                        val_type = "string" if type(t) in [str, unicode] else val_type
                                        val_type = "number" if type(t) in [int, float] else val_type
                                        val_type = "boolean" if type(t) in [bool] else val_type
                                        if key3 not in field_info[key1][key2]:
                                            error_list.append({"error_code":"unexpected-field-in-query",
                                                "field":combo_key})
                                        if val_type != field_info[key1][key2][key3]["type"]:
                                            error_list.append({"error_code":"invalid-parameter-value", "field":combo_key})
                                        if "maxlen" in field_info[key1][key2][key3]:
                                            max_query_value_len = field_info[key1][key2][key3]["maxlen"]
                                        if len(str(o[key3])) > max_query_value_len:
                                            error_list.append({"error_code":"invalid-parameter-value-length", "field":combo_key})



            elif type(query_obj[key1]) is list:
                for val in query_obj[key1]:
                    if "maxlen" in field_info[key1]:
                        max_query_value_len = field_info[key1]["maxlen"]
                    if len(str(val)) > max_query_value_len:
                        error_list.append({"error_code":"invalid-parameter-value-length", "field":key1})
            else:
                val_type = "" 
                val_type = "string" if type(query_obj[key1]) in [str, unicode] else val_type
                val_type = "number" if type(query_obj[key1]) in [int, float] else val_type
                val_type = "boolean" if type(query_obj[key1]) in [bool] else val_type
                if "maxlen" in field_info[key1]:
                    max_query_value_len = field_info[key1]["maxlen"] 
                if len(str(query_obj[key1])) > max_query_value_len:
                    error_list.append({"error_code":"invalid-parameter-value-length", "field":key1})
                if val_type != field_info[key1]["type"]:
                    error_list.append({"error_code":"invalid-parameter-value", "field":key1})


    for combo_field in config_obj[svc_name]["requiredfields"]:
        field_list = combo_field.split(".")
        if len(field_list)  == 1:
            key1 = field_list[0]
            if key1 not in query_obj:
                error_list.append({"error_code":"missing-parameter", "field":key1})
            elif str(query_obj[key1]).strip() == "":
                error_list.append({"error_code":"invalid-parameter-value-length", "field":key1})
        elif len(field_list) > 1:
            key1, key2 = field_list[0], field_list[1]
            if key1 not in query_obj:
                error_list.append({"error_code":"missing-parameter", "field":key1})
            elif key2 not in query_obj[key1]:
                error_list.append({"error_code":"missing-parameter", "field":combo_field})
            elif str(query_obj[key1][key2]).strip() == "":
                error_list.append({"error_code":"invalid-parameter-value-length", "field":combo_field})

    return error_list



def get_error_obj(error_code, error_log, path_obj):

    error_id = util.get_random_string(6)
    log_file = path_obj["apierrorlogpath"] + "/" + error_code + "-" + error_id + ".log"
    with open(log_file, "w") as FW:
        FW.write("%s" % (error_log))
    return {"error_list":[{"error_code": "exception-error-" + error_id}]}







