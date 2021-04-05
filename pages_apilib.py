import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
import pymongo
from collections import OrderedDict



import smtplib
from email.mime.text import MIMEText

import errorlib
import util
import libgly



def home_init(config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("pages_home_init",{}, config_obj)
    if error_list != []:
        return {"error_list":error_list}

    ts = datetime.datetime.now(pytz.timezone('US/Eastern')).strftime('%Y-%m-%d %H:%M:%S %Z%z')
  
    res_obj = {"version":[], "statistics":[]}
    for doc in dbh["c_version"].find({}):
        doc.pop("_id")
        res_obj["version"].append(doc)

    path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
    species_obj = {}
    in_file = path_obj["datareleasespath"]
    in_file += "data/v-%s/misc/species_info.csv" % (config_obj["datarelease"])
    libgly.load_species_info(species_obj, in_file)
    tax_id_list = []
    for k in species_obj:
        obj = species_obj[k]
        if obj["is_reference"] == "yes":
            tax_id_list.append(str(obj["tax_id"]))

    for doc in dbh["c_stat"].find({}):
        for tax_id in sorted(doc["oldstat"]):
            if tax_id not in tax_id_list:
                tax_id_list.append(tax_id)

    for doc in dbh["c_stat"].find({}):
        doc.pop("_id")
        for tax_id in list(set(tax_id_list)):
            res_obj["statistics"].append(doc["oldstat"][tax_id])

        #uncomment this when the frontend is ready to consume new stat format
        #res_obj["statistics"] = doc["newstat"]

    res_obj["events"] = []
    doc_list = dbh["c_event"].find({"visibility":"visible"}).sort('createdts', pymongo.DESCENDING)
    for doc in doc_list:
        doc["id"] = str(doc["_id"])
        doc.pop("_id")
        for k in ["createdts", "updatedts"]:
            if k not in doc:
                continue
            doc[k] = doc[k].strftime('%Y-%m-%d %H:%M:%S %Z%z')
        res_obj["events"].append(doc)

    return res_obj 



def convert_stat_json(backend_obj, frontend_obj):
    
    frontend_key_sets = [
        ["venn_protein_homo", "venn_protein_mus", "venn_protein_rat"],
        ["venn_glycan_species"],
        ["bar_mass_ranges","bar_sugar_ranges"],
        ["sunb_canon_isof_prot"],
        ["sunb_glycan_organism_type"],
        ["sunb_glycan_type_subtype"],
        ["sunb_bio_molecules"],
        ["sunb_glycoprot_rep_pred_glyc"],
        ["pie_glycohydrolases_prot", "pie_glycosyltransferases_prot"],
        ["donut_motif"]
    ]

    for k_one in frontend_obj.keys():
        if k_one in frontend_key_sets[0]:
            for o in frontend_obj[k_one]:
                tax_id = o["organism"]["id"]
                s = [str(idx) for idx in o["sets"]]
                backend_key = "%s_%s" % (tax_id, "|".join(s))
                if backend_key in backend_obj["protein"]["byproteintype"]:
                    o["size"] = backend_obj["protein"]["byproteintype"][backend_key]
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[1]:
            for o in frontend_obj[k_one]:
                s = [str(idx) for idx in o["sets"]]
                backend_key = "%s" % ("|".join(s))
                if backend_key in backend_obj["glycan"]:
                    o["size"] = backend_obj["glycan"][backend_key]
                #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[2]:
            frontend_obj[k_one]["data"] = backend_obj["glycan"][k_one]
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[3]:
            for o_one in frontend_obj[k_one]["children"]:
                tax_id = o_one["organism"]["id"]
                for o_two in o_one["children"]:
                    seq_type = "canonical"
                    if o_two["name"].find("Isoform") != -1:
                        seq_type = "isoform"
                    backend_key = "%s_%s" % (tax_id, seq_type)
                    if backend_key in backend_obj["protein"]["bysequencetype"]:
                        n = backend_obj["protein"]["bysequencetype"][backend_key]
                        o_two["size"] = n
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[4]:
            for o_one in frontend_obj[k_one]["children"]:
                tax_id = o_one["organism"]["organism_list"][0]["id"]
                for o_two in o_one["children"]:
                    g_type = o_two["glycan_type"].lower()
                    backend_key = "%s_%s" % (tax_id, g_type)
                    if backend_key in backend_obj["glycan"]["byglycantype"]:
                        n = backend_obj["glycan"]["byglycantype"][backend_key]
                        o_two["size"] = n
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[5]:
            for o_one in frontend_obj[k_one]["children"]:
                g_type = o_one["name"].lower()
                for o_two in o_one["children"]:
                    g_subtype = o_two["name"].lower()
                    backend_key = "%s_%s" % (g_type, g_subtype)
                    if backend_key in backend_obj["glycan"]["byglycantype"]:
                        n = backend_obj["glycan"]["byglycantype"][backend_key]
                        o_two["size"] = n
                    #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[6]:
            for o_one in frontend_obj[k_one]["children"]:
                if o_one["name"].find("Protein") != -1:
                    tax_id = o_one["organism"]["id"]
                    backend_key = "%s" % (tax_id)
                    if backend_key in backend_obj["protein"]["total"]:
                        n = backend_obj["protein"]["total"][backend_key]
                        o_one["size"] = n
                else:
                    tax_id = o_one["organism"]["organism_list"][0]["id"]
                    for o_two in o_one["children"]:
                        g_type = o_two["glycan_type"].lower()
                        backend_key = "%s_%s" % (tax_id, g_type)
                        if backend_key in backend_obj["glycan"]["byglycantype"]:
                            n = backend_obj["glycan"]["byglycantype"][backend_key]
                            o_two["size"] = n
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[7]:
            for o_one in frontend_obj[k_one]["children"]:
                for o_two in o_one["children"]:
                    tax_id = o_two["organism"]["id"]
                    site_type = o_two["name"].split(" ")[1].lower()
                    backend_key = "%s_%s" % (tax_id, site_type)
                    if backend_key in backend_obj["protein"]["bysitetype"]:
                        n = backend_obj["protein"]["bysitetype"][backend_key]
                        o_two["size"] = n
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[8]:
            for o_one in frontend_obj[k_one]:
                tax_id = o_one["organism"]["id"]
                backend_key = "%s" % (tax_id)
                enzyme_type = k_one.split("_")[1]
                if backend_key in backend_obj["protein"][enzyme_type]:
                    n = backend_obj["protein"][enzyme_type][backend_key]
                    o_one["size"] = n
            #print json.dumps(frontend_obj[k_one], indent=4)
        elif k_one in frontend_key_sets[9]:
            for o_one in frontend_obj[k_one]:
                backend_key = "%s" % (o_one["name"].lower())
                if backend_key in backend_obj["glycan"]["bymotiftype"]:
                    n = backend_obj["glycan"]["bymotiftype"][backend_key]
                    o_one["size"] = n

    return


def get_data_statistics(config_obj):

    db_obj =  config_obj[config_obj["server"]]["dbinfo"]
   
    backend_obj = {
        "protein":{
            "total":{},
            "byproteintype":{},
            "bysequencetype":{},
            "bysitetype":{},
            "glycohydrolases":{},
            "glycosyltransferases":{}
        },
        "glycan":{
            "total":{},
            "byglycantype":{},
            "bymotiftype":{},
            "bar_mass_ranges":[1000000,1000000,1000000],
            "bar_sugar_ranges":[1000000,1000000,1000000]
        }
    }
    glycan_type_list = []
    glycan_subtype_list = []
    motif_list = []
    taxid_list = ["9606", "10090", "10116"]
    protein_type_list = ["protein","enzymes", "glycoproteins"]
    sequence_type_list = ["canonical","isoform"]
    site_type_list = ["rwgs", "rwogs", "predicted"]
    t_set_list = [["0"], ["1"], ["2"],["0","1"],["0","2"],["1","2"],["0","1","2"]]
    m_set_list = [["0"], ["1"], ["2"],["0","1"],["0","2"],["1","2"],["0","1","2"]]
    

    backend_obj["protein"]["byproteintype"]["typelist"] = protein_type_list
    backend_obj["protein"]["bysequencetype"]["typelist"] = sequence_type_list
    backend_obj["protein"]["bysitetype"]["typelist"] = site_type_list




    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    for doc in dbh["c_glycan"].find({}):
        for o in doc["classification"]:
            g_type = o["type"]["name"].lower()
            g_subtype = o["subtype"]["name"].lower()
            if g_type not in glycan_type_list:
                glycan_type_list.append(g_type)
            if g_subtype not in glycan_subtype_list: 
                glycan_subtype_list.append(g_subtype)
        for o in doc["motifs"]:
            motif_name = o["name"].lower()
            if motif_name != "" and motif_name not in motif_list:
                motif_list.append(motif_name)


    for idx_set in t_set_list:
        backend_key = "%s" % ("|".join(idx_set))
        backend_obj["glycan"][backend_key] = 10000000
    
    for tax_id in taxid_list:
        backend_obj["protein"]["total"][tax_id] = 1000000
        backend_obj["protein"]["glycohydrolases"][tax_id] = 1000000
        backend_obj["protein"]["glycosyltransferases"][tax_id] = 1000000
        for idx_set in m_set_list:
            backend_key = "%s_%s" % (tax_id, "|".join(idx_set))
            backend_obj["protein"]["byproteintype"][backend_key] = 10000000
        for seq_type in sequence_type_list:
            backend_key = "%s_%s" % (tax_id, seq_type)
            backend_obj["protein"]["bysequencetype"][backend_key] = 10000000
        for site_type in site_type_list:
            backend_key = "%s_%s" % (tax_id, site_type)
            backend_obj["protein"]["bysitetype"][backend_key] = 10000000
        for g_type in glycan_type_list:
            backend_key = "%s_%s" % (tax_id, g_type)
            backend_obj["glycan"]["byglycantype"][backend_key] = 10000000
            
    for g_type in glycan_type_list:
        for g_subtype in glycan_subtype_list:
            backend_key = "%s_%s" % (g_type, g_subtype)
            backend_obj["glycan"]["byglycantype"][backend_key] = 10000000
    
    for motif_type in motif_list:
        backend_key = "%s" % (motif_type)
        backend_obj["glycan"]["bymotiftype"][backend_key] = 10000000


    return backend_obj



