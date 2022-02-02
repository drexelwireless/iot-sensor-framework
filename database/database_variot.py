import base64
import os
import numpy
import sys
import traceback
from database import Database
import queue
import threading
import os
from time import sleep
import pycurl
import json
import io
import requests

# Set up MAC address on server when ready, and use mac address as device ID; possibly token in the future
class VarIOTDatabase(Database):
    def __init__(self, crypto, db_path='https://variot.ece.drexel.edu', token=None, device='0000000000', dispatchsleep=0, username='', password=''):
        Database.__init__(self, crypto, db_path=db_path)
        self.username = username
        self.password = password
        if not (token is None):
            self.token = token
        else:
            self.token = self.getToken()
        self.insertion_queue = queue.Queue()
        self.dispatcher_thread = threading.Thread(
            target=self.dispatcher, args=())
        self.dispatcher_thread.start()
        self.dispatchsleep = dispatchsleep
        self.dev = device

    # https://thingsboard.io/docs/pe/user-guide/attributes/
    def postDeviceAttribute(self, attrname, attrvalue):
        payload = {attrname: attrvalue}
        headers = {"Authorization": "Bearer " + self.token}
        URL = self.db_path + '/api/plugins/telemetry/DEVICE/' + self.dev + '/SERVER_SCOPE'
        r = requests.post(url = URL, json = payload, headers = headers, verify=False)    
        resp = r.text
        # print(resp)
        return resp     
        
    def getToken(self):
        payload = {'username': self.username, 'password': self.password}
        URL = self.db_path + '/api/auth/login'
        r = requests.post(url = URL, json = payload, verify=False)    
        resp = r.text
        # print(resp)
        respjson = json.loads(resp)
        return respjson['token']
    
    def variot_dispatch(self, recordsdictlist):
        # Remove password since there is no application level encryption to VarIOT
        for record in recordsdictlist:
            del record['db_pw']
            
        data = json.dumps(recordsdictlist)

        # TODO POST TO VARIOT HERE
        # data is a json array of json records
        # token constructor parameter will be the API key when VarIOT is ready for that
        # self.dev is the device ID on VarIOT
        # Viewable at http://10.248.101.200:5000/messages/5e4af7041c9d440000f0cd38
        # Post to https?
        # Which side encrypts?  Right now, eliminating this side encryption for VarIOT (hence removal of password from the body and use of crypto from this module
        # Documentation of REST API: https://thingsboard.io/docs/reference/rest-api/
        # payload = {'ts': record['interrogatortime'], 'values': json.dumps(data)}
        #headers = {"Authorization": "Bearer " + self.token}
        ##URL = self.db_path + '/api/v2/hubs/message/xarray?address=' + self.dev
        #URL = self.db_path + '/api/v1/' + self.token + '/telemetry'
        #r = requests.post(url = URL, json = payload, headers = headers, verify=False)
        #print(r.status_code)
        #print(r.text)        
        
        self.postDeviceAttribute('data', json.dumps(data))

    # dispatch insertions from the queue so that the webserver can continue receiving requests
    # log each request to the Audit
    def dispatcher(self):
        while 1:
            queuelist = []

            input_dict = self.insertion_queue.get(block=True)
            queuelist.append(input_dict)

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_dict = self.insertion_queue.get_nowait()
                    queuelist.append(input_dict)
                except queue.Empty:
                    break

            self.variot_dispatch(queuelist)

            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

    # just insert into a queue for the dispatcher to insert in the background
    def insert_row(self, relativetime, interrogatortime, freeform, db_pw=''):
        input_dict = dict()  # read by the consumer dispatcher
        input_dict['relativetime'] = relativetime
        input_dict['interrogatortime'] = interrogatortime
        input_dict['freeform'] = freeform
        input_dict['db_pw'] = db_pw

        self.insertion_queue.put(input_dict)
