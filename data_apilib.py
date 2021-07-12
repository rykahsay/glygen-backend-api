import os
import string
import random
import hashlib
import json
import commands
import datetime,time
import pytz
from collections import OrderedDict

from flask import Flask, request, jsonify, Response, stream_with_context

import zlib
import gzip
import struct           


import smtplib
from email.mime.text import MIMEText
import errorlib
import util

from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.Alphabet import IUPAC

import motif_apilib 




def data_download(query_obj, config_obj):

    db_obj = config_obj[config_obj["server"]]["dbinfo"]
    path_obj = config_obj[config_obj["server"]]["pathinfo"]

    dbh, error_obj = util.connect_to_mongodb(db_obj) #connect to mongodb
    if error_obj != {}:
        return error_obj

    #Collect errors 
    error_list = errorlib.get_errors_in_query("data_download",query_obj, config_obj)
    if error_list != []:
        if error_list[0]["field"] != "id" and query_obj["type"] != "motif_list":
            return {"error_list":error_list}

    if query_obj["type"] not in config_obj["downloadtypes"].keys():
        error_list.append({"error_code":"download-type-not-supported"})
        return {"error_list":error_list}
    
    if query_obj["format"].lower() not in config_obj["downloadtypes"][query_obj["type"]]["formatlist"]:
        error_list.append({"error_code":"download-type-format-combination-not-supported"})
        return {"error_list":error_list}

    if query_obj["format"].lower() not in config_obj["mimetypes"]:
        error_list.append({"error_code":"non-existent-mime-type-for-submitted-format"})
        return {"error_list":error_list}

    img_path = path_obj["glycanimagespath"] % (config_obj["datarelease"])
    img_file = img_path +  "G0000000.png"
    
    format_lc = query_obj["format"].lower()

    data_buffer = ""
    if query_obj["type"] in ["glycan_list", "site_list", "motif_list","protein_list", 
            "genelocus_list", "ortholog_list","idmapping_list_mapped",
            "idmapping_list_unmapped", "idmapping_list_all", "idmapping_list_all_collapsed"]:
        collection = config_obj["downloadtypes"][query_obj["type"]]["cache"]
        mongo_query = {"list_id":query_obj["id"]}
        if query_obj["type"] == "motif_list":
           mongo_query = {}
        list_obj = {}
        if query_obj["type"] == "motif_list":
            list_query = {"sort":"glycan_count","order":"desc", "limit":10000000}
            list_obj = util.get_cached_motif_records_direct(list_query, config_obj)
        else:
            list_query = {"id":query_obj["id"], "limit":10000000}
            if query_obj["type"] in ["idmapping_list_all", "idmapping_list_all_collapsed",
                    "idmapping_list_mapped","idmapping_list_unmapped", 
                    "genelocus_list", "ortholog_list"]:
                list_obj = util.get_cached_records_direct(list_query, config_obj)
            else:
                list_obj = util.get_cached_records_indirect(list_query, config_obj)

            if "error_list" in list_obj:
                return list_obj
        if format_lc in ["json"]:
            if "_id" in list_obj:
                list_obj.pop("_id")
            data_buffer = json.dumps(list_obj["results"], indent=4)
        elif format_lc in ["csv", "tsv"]:
            ordr_dict = {}
            if query_obj["type"] in config_obj["objectorder"]:
                ordr_dict = config_obj["objectorder"][query_obj["type"]]
                                                                    
            if query_obj["type"] in ["idmapping_list_mapped", "idmapping_list_unmapped",
                    "idmapping_list_all", "idmapping_list_all_collapsed"]:
                new_list_obj = []
                mapped_legends = list_obj["cache_info"]["mapped_legends"]
                unmapped_legends = list_obj["cache_info"]["unmapped_legends"]
                legend_dict = mapped_legends
                if query_obj["type"] == "idmapping_list_unmapped":
                    legend_dict = unmapped_legends
               

                #print json.dumps(list_obj["results"], indent=4)
                for j in xrange(0, len(list_obj["results"])):
                    obj = list_obj["results"][j]
                    if query_obj["type"] == "idmapping_list_mapped":
                        if obj["category"] == "unmapped":
                            continue
                    if query_obj["type"] == "idmapping_list_unmapped":
                        if obj["category"] == "mapped":
                            continue
                    
                    if query_obj["type"] in ["idmapping_list_all", "idmapping_list_all_collapsed"]:
                        legend_dict["input_id"] = legend_dict["from"]
                        legend_dict["reason"] = legend_dict["to"]

                    new_obj = {}
                    for k in obj:
                        if k in ["category", "hit_score"]:
                            continue
                        new_obj[legend_dict[k]] = obj[k]
                        if k in ordr_dict:
                            ordr_dict[legend_dict[k]] = ordr_dict[k]
                    new_list_obj.append(new_obj)
                                
                if query_obj["type"] == "idmapping_list_all_collapsed":
                    collapse_dict = {}
                    list_obj["results"] = []
                    for obj in new_list_obj:
                        in_id = obj[legend_dict["from"]]
                        anchor = obj[legend_dict["anchor"]] if legend_dict["anchor"] in obj else ""
                        out_id = obj[legend_dict["to"]]                      
                        if in_id not in collapse_dict:
                            collapse_dict[in_id] = {"to":[], "anchor":[]}
                        if anchor not in collapse_dict[in_id]["anchor"]:
                            collapse_dict[in_id]["anchor"].append(anchor)
                        if out_id not in collapse_dict[in_id]["to"]:
                            collapse_dict[in_id]["to"].append(out_id)

                    for in_id in collapse_dict:
                        out_id = ",".join(collapse_dict[in_id]["to"])
                        anchor = ",".join(collapse_dict[in_id]["anchor"])
                        obj = {legend_dict["from"]:in_id, legend_dict["to"]:out_id, 
                                legend_dict["anchor"]:anchor}
                        list_obj["results"].append(obj)
                else:
                    list_obj["results"] = new_list_obj

            if len(list_obj["results"]) > 0:
                key_list = util.order_list(list_obj["results"][0].keys(), ordr_dict)
                if format_lc == "csv":
                    data_buffer = ",".join(key_list) + "\n"
                else:
                    data_buffer = "\t".join(key_list) + "\n" 
                line_list = []
                for j in xrange(0, len(list_obj["results"])):
                    obj = list_obj["results"][j]
                    row = []
                    for k in key_list:
                        val_k = str(obj[k]) if k in obj else ""
                        if query_obj["type"] == "ortholog_list" and k == "sequence":
                            val_k = obj[k]["sequence"]
                        if query_obj["type"] == "ortholog_list" and k == "evidence":
                            val_k = obj[k][0]["url"]
                        #if query_obj["type"] == "site_list" and k in ["glycosylation", "mutagenesis", "snv","site_annotation"]:
                        #val_k = "yes" if len(obj[k]) > 0 else "no"
                        row.append(val_k)
                    line = "\"" +  "\"\t\"".join(row) + "\"\n"
                    if format_lc == "csv":
                        line = "\"" +  "\",\"".join(row) + "\"\n"
                    line_list.append(line)
                data_buffer += "".join(line_list)
                #print data_buffer
        elif format_lc in ["iupac", "wurcs","glycam","smiles_isomeric","inchi","glycoct", "byonic"]:
            for j in xrange(0, len(list_obj["results"])):
                obj = list_obj["results"][j]
                data_buffer += "%s,%s\n" % (obj["glytoucan_ac"], obj[format_lc])
        elif format_lc in ["fasta"]:
            seq_list = []
            ac_list = []
            for obj in list_obj["results"]:
                ac_list.append(obj["uniprot_canonical_ac"])
            k = 0
            for protein_obj in dbh["c_protein"].find({"uniprot_canonical_ac":{"$in":ac_list}}):
                k += 1
                if "sequence" not in protein_obj:
                    continue
                if "sequence" not in protein_obj["sequence"]:
                    continue
                desc = util.extract_name(protein_obj["protein_names"],"recommended","UniProtKB")
                seq_obj = SeqRecord(
                    Seq(protein_obj["sequence"]["sequence"], IUPAC.protein),
                    id=obj["uniprot_canonical_ac"], 
                    description=desc
                )
                seq_list.append(seq_obj.format("fasta") + "\n\n")
            data_buffer += "".join(seq_list)
    elif query_obj["type"] in ["glycan_image"]:
        data_buffer = "xxxx"
        img_path = path_obj["glycanimagespath"] % (config_obj["datarelease"])
        img_file = img_path + query_obj["id"].upper() + ".png"
        if os.path.isfile(img_file) == False:
            img_file = img_path +  "G0000000.png"
        data_buffer = open(img_file, "rb").read()
    elif query_obj["type"] in ["glycan_detail", "motif_detail", "protein_detail","protein_detail_isoformset","protein_detail_homologset", "site_detail", "publication_detail"]:
        collection = config_obj["downloadtypes"][query_obj["type"]]["cache"]
        main_id = "uniprot_canonical_ac" 
        main_id = "glytoucan_ac" if query_obj["type"] == "glycan_detail" else main_id
        main_id = "motif_ac" if query_obj["type"] == "motif_detail" else main_id 
        main_id = "id" if query_obj["type"] == "site_detail" else main_id
        main_id = "record_id" if query_obj["type"] == "publication_detail" else main_id
    
        mongo_query = {main_id:{"$regex":query_obj["id"], "$options":"i"}}
        record_obj = dbh[collection].find_one(mongo_query)
        if record_obj == None:
            return {"error_list":{"error_code":"non-existent-record"}}

        if format_lc in ["json"]:
            record_obj.pop("_id")
            if query_obj["type"] == "protein_detail":
                url = config_obj["urltemplate"]["uniprot"] % (record_obj["uniprot_canonical_ac"])
                record_obj["uniprot"] = {
                    "uniprot_canonical_ac":record_obj["uniprot_canonical_ac"],
                    "uniprot_id":record_obj["uniprot_id"],
                    "url":url
                }
                record_obj.pop("uniprot_canonical_ac")
                record_obj.pop("uniprot_id")
                data_buffer = json.dumps(record_obj,  indent=4)
            elif query_obj["type"] in ["site_detail", "publication_detail"]:
                data_buffer = json.dumps(record_obj,  indent=4)
            elif query_obj["type"] in ["glycan_detail", "motif_detail"]:
                url = config_obj["urltemplate"]["glytoucan"] % (record_obj["glytoucan_ac"])
                record_obj["glytoucan"] = {
                    "glytoucan_ac":record_obj["glytoucan_ac"], 
                    "glytoucan_url":url
                }
                m_query = {"motifs.id": {'$eq': record_obj["glytoucan_ac"]}}
                doc_list = dbh["c_glycan"].find(m_query)
                record_obj["results"] = motif_apilib.get_parent_glycans(record_obj["glytoucan_ac"], doc_list, record_obj)
                record_obj.pop("glytoucan_ac")
                data_buffer = json.dumps(record_obj,  indent=4)
        elif format_lc in ["csv"] and query_obj["type"] in ["motif_detail"]:
            m_query = {"motifs.id": {'$eq': query_obj["id"]}}
            row = ["glytoucan_ac"]
            data_buffer += "\"" +  "\",\"".join(row) + "\"\n"
            for o in dbh["c_glycan"].find(m_query):
                row = [o["glytoucan_ac"]]
                data_buffer += "\"" +  "\",\"".join(row) + "\"\n"
        elif format_lc in ["iupac", "wurcs","glycam","smiles_isomeric","inchi","glycoct", "byonic"] and query_obj["type"] in ["glycan_detail"]:
            data_buffer += record_obj[format_lc]
        elif query_obj["format"].lower() in ["fasta"]:
            if query_obj["type"] in ["protein_detail"]:
                if "sequence" in record_obj:
                    if "sequence" in record_obj["sequence"]:
                        id_lbl, desc = "", ""
                        if "header" in record_obj["sequence"]:
                            parts = record_obj["sequence"]["header"].split(" ")
                            id_lbl = parts[0]
                            desc = " ".join(parts[1:])
                        seq_obj = SeqRecord(
                            Seq(record_obj["sequence"]["sequence"], IUPAC.protein),
                            id=id_lbl,
                            description=desc
                        )
                        data_buffer += seq_obj.format("fasta") + "\n\n"
            elif query_obj["type"] in ["protein_detail_isoformset"]:
                seq_id = record_obj["uniprot_canonical_ac"]
                for o in record_obj["isoforms"]:
                    isoform_ac = o["isoform_ac"]
                    data_buffer += get_fasta_sequence(dbh, seq_id, isoform_ac, "isoform")
            elif query_obj["type"] in ["protein_detail_homologset"]:
                seq_id = record_obj["uniprot_canonical_ac"]
                data_buffer += get_fasta_sequence(dbh, seq_id, seq_id, "canonical")
                for o in record_obj["orthologs"]:
                    seq_id = o["uniprot_canonical_ac"]
                    data_buffer += get_fasta_sequence(dbh, seq_id, seq_id, "canonical")
        elif query_obj["format"].lower() in ["png"] and query_obj["type"] in ["motif_detail"]:
            data_buffer = "xxxx"
            img_path = path_obj["glycanimagespath"] % (config_obj["datarelease"])
            glytoucan_ac = record_obj["glytoucan_ac"]
            img_file = img_path + glytoucan_ac.upper() + ".png"
            if os.path.isfile(img_file) == False:
                img_file = img_path +  "G0000000.png"
            data_buffer = open(img_file, "rb").read()
 

    #Now that we have data_buffer, let's worry about compression
    if query_obj["compressed"] == True:
        fname = "%s.%s" % (query_obj["id"], query_obj["format"])
        out_file = "/tmp/glygen-download-%s" % (fname)
        with open(out_file, "w") as FW:
            FW.write(data_buffer)
        cmd = path_obj["gzip"] + " -c %s " % (out_file)
        c_data_buffer = commands.getoutput(cmd)
        res_stream = Response(c_data_buffer, mimetype='application/gzip')
        res_stream.headers['Content-Disposition'] = 'attachment; filename=%s.gz' % (fname)
        cmd = " rm -f  %s " % (out_file)
        x = commands.getoutput(cmd)
    else:
        res_stream = Response(data_buffer, mimetype=config_obj["mimetypes"][query_obj["format"]])

    #print data_buffer

    return res_stream



def generate_gzip(data_buffer):
    

    # Yield a gzip file header first.
    yield (
        '\037\213\010\000' + # Gzip file, deflate, no filename
        struct.pack('<L', long(time.time())) +  # compression start time
        '\002\377'  # maximum compression, no OS specified
    )

    # bookkeeping: the compression state, running CRC and total length
    compressor = zlib.compressobj(
        9, zlib.DEFLATED, -zlib.MAX_WBITS, zlib.DEF_MEM_LEVEL, 0)
    crc = zlib.crc32("")
    length = 0

    lines = data_buffer.split("\n")
    for i in xrange(0,len(lines)):
        chunk = compressor.compress(lines[i])
        if chunk:
            yield chunk
        crc = zlib.crc32(lines[i], crc) & 0xffffffffL
        length += len(lines[i])

    # Finishing off, send remainder of the compressed data, and CRC and length
    yield compressor.flush()
    yield struct.pack("<2L", crc, length & 0xffffffffL)






def get_fasta_sequence(dbh, canon, isoform_ac, seq_type):

    mongo_query = {"uniprot_canonical_ac":canon}
    doc = dbh["c_protein"].find_one(mongo_query)

    sec_doc = doc["sequence"]
    if seq_type == "isoform":
        for o in doc["isoforms"]:
            if isoform_ac == o["isoform_ac"]:
                sec_doc = o["sequence"]
                break
    seq_str = sec_doc["sequence"]
    seq_header = sec_doc["header"]
    seq_obj = SeqRecord(Seq(seq_str,IUPAC.protein),id="x",description="xxx")
    seq_lines = seq_obj.format("fasta").split("\n")
    seq_lines = [">"+seq_header] + seq_lines[1:]
    seq = "\n".join(seq_lines) + "\n"

    return seq


