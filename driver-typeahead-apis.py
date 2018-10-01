import sys,os
import json
import string
import csv
import traceback
from optparse import OptionParser

import typeahead_apilib as apilib



def main():

    usage = "\n%prog  [options]"
    parser = OptionParser(usage,version="%prog version___")
    parser.add_option("-s","--svctype",action="store",dest="svctype",help="SVC name")
    parser.add_option("-q","--queryfile",action="store",dest="queryfile",help="Query JSON file")
    (options,args) = parser.parse_args()
    for key in ([options.queryfile, options.svctype]):
        if not (key):
            parser.print_help()
            sys.exit(0)
                                                                                    
                                                                                    
    global config_obj
    global path_obj
    config_obj = json.loads(open("./conf/config.json", "r").read())
    path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
    db_obj = config_obj[config_obj["server"]]["dbinfo"]



    if apilib.is_valid_json(open(options.queryfile, "r").read()) == False:
        res_obj = {"error_code": "invalid-query-json"}
        print json.dumps(res_obj, indent=4)
        sys.exit()


    res_obj = {}
    query_obj = json.loads(open(options.queryfile, "r").read())
    svc_type = options.svctype

    field_list_one = ["glytoucan_ac", "motif_name", "enzyme_uniprot_canonical_ac"]
    field_list_two = ["uniprot_canonical_ac", "uniprot_id", "refseq_ac", 
                        "protein_name", "gene_name", "pathway_id", "pathway_name", "disease_name"] 
    try:
        tmp_obj_one, tmp_obj_two = [], []
        if query_obj["field"] in field_list_one:
            tmp_obj_one = apilib.glycan_typeahead(query_obj, config_obj)
        if query_obj["field"] in field_list_two:
            tmp_obj_two = apilib.protein_typeahead(query_obj, config_obj)
        if "error_code" in tmp_obj_one:
            res_obj = tmp_obj_one
        elif "error_code" in tmp_obj_two:
            res_obj = tmp_obj_two
        else:
            res_obj = tmp_obj_one + tmp_obj_two
        print json.dumps(res_obj, indent=4)
    except Exception, e:
        res_obj = apilib.get_error_obj("typeahead", traceback.format_exc(),  path_obj)
        print traceback.format_exc()


if __name__ == '__main__':
    main()





