#! /usr/bin/env python

# AXIS VAPIX API
# Get door controller access log 
# Author: Robert A Swirsky / Thrill Science
# Date:   June 1, 2020 (Initial Commit)

# Date:   December 10, 2021 (Support fort HTTPS method)
# Contributor: Thibault Lansiaux / Wiconnect www.wiconnect.fr

import requests
import json
import argparse
import time
import os
from datetime import date

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from requests.auth import HTTPDigestAuth

def keyvalues_to_dictionary(kv):
   return { k['Key']: k['Value'] for k in kv }

def check_key(d, key):
   if key in d:
      return d[key]
   else:
      return "?key?"

def get_door_list(params):
   (addr, username, password) = params
   data = {"axtdc:GetDoorList":{}}
   if (args.httpmethod == 'HTTPS' or args.httpmethod == None):
      r=requests.post(str.format("https://{0}/vapix/doorcontrol", addr),
       json.dumps(data),
       auth=HTTPDigestAuth(username, password), verify = False)
   else:
      r=requests.post(str.format("http://{0}/vapix/doorcontrol", addr),
       json.dumps(data),
       auth=HTTPDigestAuth(username, password))
   if r.status_code == 200:
      e = json.loads(r.text)
      return { k['token']: k['Name'] for k in e['Door']}
   else:
      return {}

def make_http_request(data, addr, username, password):
   if (args.httpmethod == 'HTTPS' or args.httpmethod == None):
      r=requests.post(str.format("https://{0}/vapix/pacs", addr),
       json.dumps(data),
       auth=HTTPDigestAuth(username, password), verify = False)
   else:
      r=requests.post(str.format("http://{0}/vapix/pacs", addr),
       json.dumps(data),
       auth=HTTPDigestAuth(username, password))
   return r

def get_user_list(params):
   r = make_http_request({"axudb:GetUserList":{}}, *params)
   if r.status_code == 200:
      e = json.loads(r.text)
      return { k['token']: k['Name'] for k in e['User']}
   else:
      return {}

def get_access_point_list(params):
   r = make_http_request({"pacsaxis:GetAccessPointList":{}}, *params)
   if r.status_code == 200:
      e = json.loads(r.text)
      return { k['token']: k['Entity'] for k in e['AccessPoint']}
   else:
      return {}

# Get the configuration lists that don't change on every new event
def get_configuration_lists(args):
   params = (args.ipAddress, args.user, args.password)
   userList = get_user_list(params)
   doorList = get_door_list(params)
   accessPointList = get_access_point_list(params)
   return (userList, doorList, accessPointList)


# Get all Granted and Denied events
def get_events(userList, doorList, accessPointList, args):
   data = {"axlog:FetchEvents3":
               {"FilterSets":[
                 {"Start": args.fromDate,
                  "Filters":[
                      { "Key": "topic1", "Value": "AccessGranted" }
                  ]} ,
                  {"Start": args.fromDate,
                   "Filters":[
                      { "Key": "topic1", "Value": "Denied" }
                 ]}
               ],
               "Descending":True,
               "IncludeHumanReadableTime":True,
               "ConvertFilterTimeFromLocal":True
               }
         }
   if (args.httpmethod == 'HTTPS' or args.httpmethod == None):
      r=requests.post(str.format("https://{0}/vapix/eventlogger",args.ipAddress),
            json.dumps(data),
            auth=HTTPDigestAuth(args.user, args.password), verify = False)
   else:
      r=requests.post(str.format("http://{0}/vapix/eventlogger",args.ipAddress),
            json.dumps(data),
            auth=HTTPDigestAuth(args.user, args.password))
   if r.status_code == 200:
      e = json.loads(r.text)
      for event in e['Event']:
         edict = keyvalues_to_dictionary(event['KeyValues'])
         accessPointToken = check_key(edict, 'AccessPointToken')
         doorEntity = check_key(accessPointList, accessPointToken)
         doorName = check_key(doorList, doorEntity)
         if 'topic2' in edict and (edict['topic2'] == 'CredentialNotFound'):
            s = str.format("{0:8}, {1:16}, {2:32}, {3:16}, {4:14}, {5:19}", 
               event['rowid'],
               event['HumanReadableTime'],
               doorName,
               check_key(edict, 'Card'),
               edict['topic1'], 
               edict['topic2'])
            print(s)
         else:
            nameKey = check_key(edict, 'CredentialHolderName'),
            s = str.format( "{0:8}, {1:16}, {2:32}, '{3:32}', {4:24}, {5:14}, {6:19}",
               event['rowid'],
               event['HumanReadableTime'],
               doorName,
               check_key(userList, nameKey[0]),
               check_key(edict, 'CredentialType'),
               edict['topic1'],
               edict['topic2'])
            print(s)
   else:
      return "Error"


if __name__ == "__main__":
    defaultDate = date.today().isoformat()+"T00:00:00"
    parser = argparse.ArgumentParser()

    # get address,  username,  and password from environment variables
    axisAddress = os.environ.get('AxisAddress')
    axisUser = os.environ.get('AxisUser')
    axisPassword = os.environ.get('AxisPassword')
    axisHttpMethod = os.environ.get('axisHttpMethod')

    parser.add_argument("--fromDate",default=defaultDate, help="event date in YYYY-MM-DDTHH:MM:SS format")
    parser.add_argument("--ipAddress",default=axisAddress, help="ip address or DNS name of controller")
    parser.add_argument("--user",default=axisUser, help="username")
    parser.add_argument("--password",default=axisPassword, help="password")
    parser.add_argument("--httpmethod",default=axisHttpMethod, help="httpmethod")
    args = parser.parse_args()

    if args.ipAddress == None or args.user == None or args.password == None:
       print("Error: Set AxisAddress, AxisUser, and AxisPassword as environment variables or use command line options.")
       exit(-1)
    else:
      (userList, doorList, accessPointList) = get_configuration_lists(args)
      get_events(userList, doorList, accessPointList, args)
