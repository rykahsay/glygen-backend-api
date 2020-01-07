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

    img_file = path_obj["glycanimagespath"] +  "G0000000.png"

    data_buffer = ""
    if query_obj["type"] in ["glycan_list", "protein_list"]:
        collection = config_obj["downloadtypes"][query_obj["type"]]["cache"]
        mongo_query = {"list_id":query_obj["id"]}
        list_obj = dbh[collection].find_one(mongo_query)
        if list_obj == None:
            return {"error_list":{"error_code":"non-existent-search-results"}}
        if query_obj["format"].lower() in ["json"]:
            list_obj.pop("_id")
            data_buffer = json.dumps(list_obj["results"], indent=4)
        elif query_obj["format"].lower() in ["csv", "tsv"]:
            if len(list_obj["results"]) > 0:
                ordr_dict = config_obj["objectorder"]["proteinlist"] if query_obj["type"] == "protein_list" else config_obj["objectorder"]["glycanlist"]
                key_list = util.order_list(list_obj["results"][0].keys(), ordr_dict)
            
                if query_obj["format"].lower() == "csv":
                    data_buffer = ",".join(key_list) + "\n"
                else:
                    data_buffer = "\t".join(key_list) + "\n" 
                for obj in list_obj["results"]:
                    row = []
                    for k in key_list:
                        row.append(str(obj[k]))
                    if query_obj["format"].lower() == "csv":
                        data_buffer += "\"" +  "\",\"".join(row) + "\"\n"
                    else:
                        data_buffer += "\"" +  "\"\t\"".join(row) + "\"\n"
        elif query_obj["format"].lower() in ["fasta"]:
            for obj in list_obj["results"]:
                protein_obj = dbh["c_protein"].find_one({"uniprot_canonical_ac":obj["uniprot_canonical_ac"]})
                if "sequence" not in protein_obj:
                    continue
                if "sequence" not in protein_obj["sequence"]:
                    continue
                desc = ""
                if "recommendedname" in protein_obj:
                    if "full" in protein_obj["recommendedname"]:
                        desc = protein_obj["recommendedname"]["full"]
                seq_obj = SeqRecord(
                    Seq(protein_obj["sequence"]["sequence"], IUPAC.protein),
                    id=obj["uniprot_canonical_ac"], 
                    description=desc
                )
                data_buffer += seq_obj.format("fasta") + "\n\n"
    elif query_obj["type"] in ["glycan_image"]:
        data_buffer = "xxxx"
        img_file = path_obj["glycanimagespath"] +   query_obj["id"].upper() +".png"
        if os.path.isfile(img_file) == False:
            img_file = path_obj["glycanimagespath"] +  "G0000000.png"
        data_buffer = open(img_file, "rb").read()
    elif query_obj["type"] in ["glycan_detail", "motif_detail", "protein_detail"]:
        collection = config_obj["downloadtypes"][query_obj["type"]]["cache"]
        main_id = "uniprot_canonical_ac" if query_obj["type"] == "protein_detail" else "glytoucan_ac"
        mongo_query = {main_id:query_obj["id"]}
        record_obj = dbh[collection].find_one(mongo_query)
        if record_obj == None:
            return {"error_list":{"error_code":"non-existent-record"}}

        if query_obj["format"].lower() in ["json"]:
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
        elif query_obj["format"].lower() in ["csv"] and query_obj["type"] in ["motif_detail"]:
            m_query = {"motifs.id": {'$eq': query_obj["id"]}}
            row = ["glytoucan_ac"]
            data_buffer += "\"" +  "\",\"".join(row) + "\"\n"
            for o in dbh["c_glycan"].find(m_query):
                row = [o["glytoucan_ac"]]
                data_buffer += "\"" +  "\",\"".join(row) + "\"\n"
        elif query_obj["format"].lower() in ["fasta"]:
            if "sequence" in record_obj:
                if "sequence" in record_obj["sequence"]:
                    desc = ""
                    if "recommendedname" in record_obj:
                        if "full" in record_obj["recommendedname"]:
                            desc = record_obj["recommendedname"]["full"]
                    seq_obj = SeqRecord(
                        Seq(record_obj["sequence"]["sequence"], IUPAC.protein),
                        id=record_obj["uniprot_canonical_ac"],
                        description=desc
                    )
                    data_buffer += seq_obj.format("fasta") + "\n\n"



     
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





