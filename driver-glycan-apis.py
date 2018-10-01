import sys,os
import json
import string
import csv
import traceback
from optparse import OptionParser

import glycan_apilib as apilib

def trim_object(obj):
        
    for key in obj:
        if type(obj[key]) is unicode:
            obj[key] = obj[key].strip()



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


    try:
        if svc_type == "search_init":
            res_obj = apilib.glycan_search_init(config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "search":
            trim_object(query_obj)
            res_obj = apilib.glycan_search(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "list":
            trim_object(query_obj)
            res_obj = apilib.glycan_list(query_obj, config_obj)
	    print json.dumps(res_obj, indent=4)
        elif svc_type == "detail":
            trim_object(query_obj)
            res_obj = apilib.glycan_detail(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "image":
            trim_object(query_obj)
            img_file = apilib.glycan_image(query_obj, path_obj)
            print img_file
            sys.exit()
    except Exception, e:
        res_obj = apilib.get_error_obj("glycansearch", traceback.format_exc(), path_obj)
        print traceback.format_exc()



if __name__ == '__main__':
    main()





