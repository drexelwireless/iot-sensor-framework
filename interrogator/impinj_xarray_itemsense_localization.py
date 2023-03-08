from interrogator import *
import requests
import base64
import threading
import json
import sys
import os
import queue
from time import sleep
import collections
import dateutil.parser

class ImpinjXArray(Interrogator):
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _apiusername, _apipassword, _dispatchsleep=0, _recipe='IMPINJ_Fast_Location', _facility='MESS'):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address
        self.baseurl = "http://%s/itemsense" % self.ip_address
        
        self.apiusername = _apiusername
        self.apipassword = _apipassword
            
        self.start_timestamp = -1
        
        self.recipe = _recipe
        self.facility = _facility

        self.out('Initializing XArray Interrogator client')

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.out('Starting Impinj XArray Interrogator client')
        
        self.tag_dicts_queue = queue.Queue()
        self.handler_thread = threading.Thread(
            target=self.handler_thread, args=())
        self.handler_thread.start()

        # Create Clients and set them to connect
        authstr = "%s:%s" % (self.apiusername, self.apipassword)
        basicenc = base64.b64encode(authstr.encode())
        self.basicauth = 'Basic ' + basicenc.decode()
        facility = self.facility #'MESS'
        recipe = self.recipe #'IMPINJ_Fast_Location'

        # Get a Token
        url = self.baseurl + '/authentication/v1/token/' + self.apiusername
        Headers = {}
        Headers['Authorization'] = self.basicauth
        response = requests.put(url, headers=Headers)
        self.token = response.json()['token']
        self.tokenauth = 'Token {"token":\"' + self.token + '\"}'

        # Start a Job
        url = self.baseurl + '/control/v1/jobs/start'
        Data = {}
        Data['startDelay'] = 'PT1S'  # 1 second job start delay
        Data['facility'] = facility
        Data['recipeName'] = recipe
        Headers = {}
        Headers['Authorization'] = self.tokenauth
        Headers['Content-Type'] = 'application/json'
        response = requests.post(url, data=json.dumps(Data), headers=Headers)
        
        # Job start will fail if there is already a running job; cycle through our jobs and end those RUNNING jobs with a facility and recipe name that match ours; note that if there is another RUNNING job from another facility or recipe, this will continue to fail, but it seems better not to stop someone else's job
        if not ('id' in response.json()): # if id is not in response, need to stop existing running jobs
            # Stop Running Jobs, then Re-Start the Job
            url = self.baseurl + '/control/v1/jobs/show'
            Headers = {}
            Headers['Authorization'] = self.tokenauth
            Headers['Content-Type'] = 'application/json'
            response = requests.get(url, headers=Headers)
            
            for j in response.json():
                if j['job']['facility'].lower() == facility.lower() and j['job']['recipeName'].lower() == recipe.lower():
                    if j['status'].lower() == 'running':
                        url = self.baseurl + '/control/v1/jobs/stop/' + j['id']
                        Headers = {}
                        Headers['Content-Type'] = 'application/json'
                        Headers['Authorization'] = self.tokenauth
                        response = requests.post(url, headers=Headers)                    
            # Re-Start the Job
            url = self.baseurl + '/control/v1/jobs/start'
            Data = {}
            Data['startDelay'] = 'PT1S'  # 1 second job start delay
            Data['facility'] = facility
            Data['recipeName'] = recipe
            Headers = {}
            Headers['Authorization'] = self.tokenauth
            Headers['Content-Type'] = 'application/json'
            response = requests.post(url, data=json.dumps(Data), headers=Headers)            
        jobId = response.json()['id'] # This will fail if the job did not start successfully, could handle more gracefully...
        self.out("Job ID: %s" % jobId)

        self.jobId = jobId
        self.count = 0

        while not self.exiting:            
            done = False
            while (not done):
                sleep(5)
                url = self.baseurl + '/data/v1/items/show'
                urlh = self.baseurl + '/data/v1/items/show/history'
                Data = {}
                Data['facility'] = facility
                Data['jobId'] = jobId
                Headers = {}
                Headers['Content-Type'] = 'application/json'
                Headers['Authorization'] = self.tokenauth
                response = requests.get(
                    url, data=json.dumps(Data), headers=Headers)
                # responseh = requests.get(
                #     urlh, data=json.dumps(Data), headers=Headers)
                responsejson = response.json()
                # responsehjson = responseh.json()
                # self.out("==========================================================")
                # self.out("DATA")
                # self.out(response)
                # self.out(response.text)

                # self.out("==========================================================")
                # self.out("timestamp\t\tepc\txLocation\tyLocation\tzLocation")
                # t = 0
                # for i in responsejson["items"]:
                #     self.out(t)
                #     t += 1
                #     timestamp = i['lastModifiedTime']
                #     epc = i['epc']
                #     x = i["xLocation"]
                #     y = i["yLocation"]
                #     self.out("%s\t%s\t%d\t\t%d" % (timestamp, epc[-4:], x, y))

                # self.out("==========================================================")

                # self.out("timestamp\t\tepc\txLocation\tyLocation")

                # for i in responsehjson["history"]:
                #     timestamp = i['observationTime']
                #     epc = i['epc']
                #     x = i["toX"] if i["toX"] is not None else 0
                #     y = i["toY"] if i["toY"] is not None else 0
                #     self.out("%s\t%s\t%d\t\t%d" % (timestamp, epc[-4:], x, y))

                # self.out("==========================================================")

                # self.out("HISTORY")
                # self.out(responseh)
                # self.out(responseh.text)

                if not "nextPageMarker" in responsejson:
                    done = True
                elif responsejson['nextPageMarker'] is None:
                    done = True
                else:
                  Data['pageMarker'] = responsejson['nextPageMarker']
                
                self.tag_dicts_queue.put(responsejson)
                
            self.count = self.count + 1

    def handler_thread(self):
        while not self.exiting:
            responsearray = []
            
            responsejson = self.tag_dicts_queue.get(block=True)
            responsearray.append(responsejson)
            
            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    responsejson = self.tag_dicts_queue.get_nowait()
                    responsearray.append(responsejson)
                except queue.Empty:
                    break
                    
            self.insert_tag(responsearray)            

    def start(self):
        self.out('XArray: start')
        self.start_server()

    def close_server(self):
        self.exiting = True
        # Stop the Job
        url = self.baseurl + '/control/v1/jobs/stop/' + self.jobId
        Headers = {}
        Headers['Content-Type'] = 'application/json'
        Headers['Authorization'] = self.tokenauth
        response = requests.post(url, headers=Headers)
        self.out(response)

        # Revoke the Token
        url = self.baseurl + '/authentication/v1/revokeToken'
        Headers = {}
        Headers['Content-Type'] = 'application/json'
        Headers['Authorization'] = self.basicauth
        Data = {}
        Data['token'] = self.token
        response = requests.put(url, headers=Headers, data=json.dumps(Data))
        print(response)

    def __del__(self):
        self.close_server()

    def insert_tag(self, tagarray):
        input_dicts = []
        
        if self.start_timestamp == -1:
          min_timestamp = -1
          for entry in tagarray:
            items = entry['items']

            for freeform in items:
              # convert the timestamp from a string to numeric
              timestamp = freeform['lastModifiedTime']
              timestampdt = dateutil.parser.parse(timestamp)
              timestampmicro = timestampdt.timestamp() * 1000
              
              if int(timestampmicro) < min_timestamp or min_timestamp == -1:
                min_timestamp = timestampmicro
                
          self.start_timestamp = int(min_timestamp)
        
        for entry in tagarray:
          items = entry['items']

          for freeform in items:            
            timestamp = freeform['lastModifiedTime']
            epc = freeform['epc']
            xPos = freeform["xLocation"]
            yPos = freeform["yLocation"]
            zPos = freeform["zLocation"]
            
            # convert the timestamp from a string to numeric
            timestampdt = dateutil.parser.parse(timestamp)
            timestampmicro = timestampdt.timestamp() * 1000
            
            self.out("Adding tag / collection %s with timestamp %s and epc %s and xPosition %s and yPosition %s and zPosition %s" % (
                str(self.count), str(timestampmicro), str(epc), str(xPos), str(yPos), str(zPos)))

            input_dict = dict()
            input_dict['data'] = dict()
            input_dict['data']['db_password'] = self.db_password
            input_dict['data']['freeform'] = freeform
            input_dict['data']['relative_time'] = int(timestampmicro) - self.start_timestamp
            input_dict['data']['interrogator_time'] = timestampmicro            
            
            self.out("Input dict is: %s" % input_dict)
            
            input_dicts.append(input_dict)
            
        url = self.db_host + '/api/rssi'

        resp, content = Interrogator.sendhttp(url, headerdict={'Content-Type': 'application/json; charset=UTF-8'}, bodydict=input_dicts, method='PUT')
            
        if self.dispatchsleep > 0:
            # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
            sleep(self.dispatchsleep)

# Requires:
# easy_install httplib2 (not pip)
