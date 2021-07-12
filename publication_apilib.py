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




def publication_detail(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj


    #Collect errors 
    error_list = errorlib.get_errors_in_query("publication_detail", query_obj, config_obj)
    if error_list != []:
        return {"error_list":error_list}
    collection = "c_publication"


    #combo_id = "%s.%s" % (query_obj["type"].lower(), query_obj["id"])
    #mongo_query = {"record_id":{"$regex":combo_id, "$options":"i"}}
    mongo_query = {
        "$and":[
            {"reference.id":{"$eq":query_obj["id"]}},
            {"reference.type":{"$regex":query_obj["type"], "$options":"i"}}
        ]
    }
    
    publication_doc = dbh[collection].find_one(mongo_query)
    
    #check for post-access error, error_list should be empty upto this line
    post_error_list = []
    if publication_doc == None:
        post_error_list.append({"error_code":"non-existent-record"})
        return {"error_list":post_error_list}

    q_obj = {"uniprot_canonical_ac":{"$in":publication_doc["referenced_proteins"]}}
    for protein_doc in dbh["c_protein"].find(q_obj):
        get_section_objects(protein_doc, publication_doc)

    util.clean_obj(publication_doc, config_obj["removelist"]["c_publication"], "c_publication")

    return publication_doc




def get_section_objects(protein_doc, pub_doc):


    site_sec_list = ["snv", "glycosylation", "phosphorylation", "glycation", "mutagenesis"] 
    for sec in site_sec_list:
        if sec in protein_doc:
            for sec_obj in protein_doc[sec]:
                for ev_obj in sec_obj["evidence"]:
                    record_id = ""
                    if ev_obj["database"] != "":
                        record_id = "%s.%s" % (ev_obj["database"].lower(), ev_obj["id"])
                    if record_id == pub_doc["record_id"]:
                        if sec not in pub_doc:
                            pub_doc[sec] = []
                        sec_obj["uniprot_canonical_ac"] = protein_doc["uniprot_canonical_ac"]
                        pub_doc[sec].append(sec_obj)

    return







