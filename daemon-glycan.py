import csv
import urllib,urllib2
import collections
from optparse import OptionParser
import os,sys
import json
import traceback

import datetime
import requests

import smtplib
from email.mime.text import MIMEText


__version__="1.0"
__status__ = "Dev"


###############################
def send_email(sender, receivers, msg_text, server):

    msg = MIMEText(msg_text)
    msg['Subject'] = "URGENT - GlyGen GLYCAN API not working on %s!" % (server)
    msg['From'] = sender
    msg['To'] = receivers[0]
   
    s = smtplib.SMTP('localhost')
    s.sendmail(sender, receivers, msg.as_string())
    s.quit()
    
    return





#################################
def get_webpage(url):

    url = url.replace(" ", "")
    try:
        #request = urllib2.Request(url)
        #contact = "" # Please set your email address here to help us debug in case of problems.
        #request.add_header('User-Agent', 'Python %s' % contact)
        #response = urllib2.urlopen(request)
        #res_obj = json.loads(response.read())
        
        res = requests.get(url, verify=False)
        res_obj = json.loads(res.content.strip())
        return {"status":1, "res":res_obj}
    except Exception, e:
        lines =  traceback.format_exc().split("\n")
        return {"status":0, "error":"; ".join(lines)}


###############################
def main():

    global config_obj
    global path_obj
    
    script_path = os.path.dirname(os.path.realpath(__file__))
    config_file = script_path + "/conf/config.json"
    config_obj = json.loads(open(config_file, "r").read())
    
    path_obj  =  config_obj[config_obj["server"]]["pathinfo"]
    root_obj  =  config_obj[config_obj["server"]]["rootinfo"]
    db_obj = config_obj[config_obj["server"]]["dbinfo"]

    api_domain = "https://api.glygen.org"
    log_file = path_obj["apierrorlogpath"] + "/api_test.log"
    if config_obj["server"] in ["dev", "tst"]:
        api_domain = "https://api.%s.glygen.org" % (config_obj["server"])
    elif config_obj["server"] in ["beta"]:
        api_domain = "https://%s-api.glygen.org" % (config_obj["server"])


    #Test glycan docs
    glycan_count = 10

    query_obj = {"mass_type":"native"}
    query_str = json.dumps(query_obj)
    api_url = "%s/glycan/search?query=%s" % (api_domain, query_str)
    out_obj_one = get_webpage(api_url)
    
    out_obj_final = {"status":1}
    if out_obj_one["status"] == 0:
        out_obj_final = out_obj_one
    else:
        query_obj = {"id":out_obj_one["res"]["list_id"], "limit": glycan_count}
        query_str = json.dumps(query_obj)
        api_url = "%s/glycan/list?query=%s" % (api_domain, query_str)
        out_obj_two = get_webpage(api_url)
        if out_obj_two["status"] == 0:
            out_obj_final = out_obj_two
        else:
            if len(out_obj_two["res"]["results"]) != glycan_count:
                out_obj_final = {"status":0, "error":"Count mismatch"}
            else:
                for obj in out_obj_two["res"]["results"]:
                    ac = obj["glytoucan_ac"]
                    api_url = "%s/glycan/detail/%s" %(api_domain,ac)
                    out_obj_three = get_webpage(api_url)
                    
                    #Test level-1 keys
                    for k in ["glytoucan", "classification"]:
                        if k not in out_obj_three["res"]:
                            out_obj_final = {"status":0, "error":"Missing level-1 property!"}
                            break

                    #Test some level-1 lists
                    for k in ["classification"]:
                        if len(out_obj_three["res"][k]) < 1:
                            out_obj_final = {"status":0, "error":"Empty level-1 list!"}
                            break
                    
                    if "glytoucan_ac" not in out_obj_three["res"]["glytoucan"]:
                        out_obj_final = {"status":0, "error":"Missing level-2 property!"}
                    elif out_obj_three["res"]["glytoucan"]["glytoucan_ac"].strip() == "":
                        out_obj_final = {"status":0, "error":"Empty glytoucan AC!"}


    ts = datetime.datetime.now()

    FA = open(log_file, "a")
    if out_obj_final["status"] != 1:
        sender = config_obj[config_obj["server"]]["contactemailreceivers"][0]
        receivers = config_obj[config_obj["server"]]["contactemailreceivers"]
        send_email(sender, receivers, out_obj_final["error"], config_obj["server"])
        FA.write("%s\t%s\t%s\n" % (ts, "GLYCAN API FAILURE",out_obj_final["error"]))
    else:
        FA.write("%s\t%s\t%s\n" % (ts, "GLYCAN API SUCCESS", ""))
    FA.close()



if __name__ == '__main__':
        main()
