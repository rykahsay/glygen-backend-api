import sys,os
import json
import string
import csv
import traceback
from optparse import OptionParser

import usecases_apilib as apilib




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


    res_obj = {}
    query_obj = json.loads(open(options.queryfile, "r").read())
    svc_type = options.svctype


    try:

        if svc_type == "search_init":
            res_obj = apilib.protein_search_init(config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "glycan_to_biosynthesis_enzymes":
            res_obj = apilib.glycan_to_biosynthesis_enzymes(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "glycan_to_glycoproteins":
            res_obj = apilib.glycan_to_glycoproteins(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "species_to_glycosyltransferases":
            res_obj = apilib.species_to_glycosyltransferases(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "species_to_glycohydrolases":
            res_obj = apilib.species_to_glycohydrolases(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "species_to_glycoproteins":
            res_obj = apilib.species_to_glycoproteins(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "disease_to_glycosyltransferases":
            res_obj = apilib.disease_to_glycosyltransferases(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "protein_to_orthologs":
            res_obj = apilib.protein_to_orthologs(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "glycan_to_enzyme_gene_loci":
            res_obj = apilib.glycan_to_enzyme_gene_loci(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)

    except Exception, e:
        res_obj = apilib.get_error_obj("proteinsearch", traceback.format_exc(), path_obj)
        print traceback.format_exc()



if __name__ == '__main__':
    main()





