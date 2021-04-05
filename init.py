#!/usr/bin/python
import os,sys
import string
import commands
import csv
import traceback

from Bio import SeqIO
from Bio.Seq import Seq


from optparse import OptionParser
import glob
from bson import json_util, ObjectId
import json
import util
import cgi


import pymongo
from pymongo import MongoClient



__version__="1.0"
__status__ = "Dev"



###############################
def main():

    global config_json
    global db_obj
    global client
    global path_obj
    
    print "Content-Type: application/json"
    print   

    out_json = {}
    try:
        config_json = json.loads(open("conf/config.json", "r").read())
        db_obj = config_json[config_json["server"]]["dbinfo"]
        path_obj = config_json[config_json["server"]]["pathinfo"]
        root_obj = config_json[config_json["server"]]["rootinfo"]

        version_one, version_two = config_json["moduleversion"],config_json["datarelease"]
        versions = "Website-%s | Data-%s" % (version_one, version_two)
        
        domain_dict = {}
        for domain in ["api", "data", "sparql"]:
            url = ""
            if config_json["server"] in ["dev", "tst"]:
                url = "https://%s.%s.glygen.org/" % (domain, config_json["server"]);
            elif config_json["server"] in ["beta"]:
                url = "https://%s-%s.glygen.org/" % (config_json["server"], domain);
            elif config_json["server"] in ["prd"]:
                url = "https://%s.glygen.org/" % (domain);
            domain_dict[domain] = url
        
        domain_dict["portal"] = "https://%s.glygen.org/" % (config_json["server"])
        if config_json["server"] in ["prd"]:
            domain_dict["portal"] = "https://glygen.org/"

        out_json = {"moduleversion":versions, "domains":domain_dict, "taskstatus":1};
    except Exception, e:
        out_json = {"taskstatus":0, "errormsg":"query failed!"}

    print json.dumps(out_json, indent=4)



if __name__ == '__main__':
	main()

