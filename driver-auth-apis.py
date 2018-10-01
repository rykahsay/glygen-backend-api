import sys,os
import json
import string
import csv
import traceback
from optparse import OptionParser

import auth_apilib as apilib




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
    db_obj =  config_obj[config_obj["server"]]["dbinfo"]


    if apilib.is_valid_json(open(options.queryfile, "r").read()) == False:
        res_obj = {"error_code": "invalid-query-json"}
        print json.dumps(res_obj, indent=4)
        sys.exit()


    res_obj = {}
    query_obj = json.loads(open(options.queryfile, "r").read())
    svc_type = options.svctype




    try:
        if svc_type == "userid":
            res_obj = apilib.auth_userid(config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "logging":
            res_obj = apilib.auth_logging(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
        elif svc_type == "contact":
            res_obj = apilib.auth_contact(query_obj, config_obj)
            print json.dumps(res_obj, indent=4)
    except Exception, e:
        res_obj = apilib.get_error_obj("glycansearch", traceback.format_exc(), path_obj)
               
        print traceback.format_exc()



if __name__ == '__main__':
    main()





