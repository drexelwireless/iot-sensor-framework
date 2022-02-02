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
import time

class VarIOTDatabase(Database):
    def __init__(self, crypto, db_path='https://variot.ece.drexel.edu', token='e2tmxfzcJG6JfPuyzTOT', device='6592aa50-579f-11ec-b72a-b3a72eee71ca', dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path)
        self.token = token
        self.insertion_queue = queue.Queue()
        self.dispatcher_thread = threading.Thread(
            target=self.dispatcher, args=())
        self.dispatcher_thread.start()
        self.dispatchsleep = dispatchsleep
        self.dev = device

    def variot_dispatch(self, recordsdictlist):
        # Remove password since there is no application level encryption to VarIOT
        for record in recordsdictlist:
            del record['values']['db_pw']
            #record['ts']=int(time.time())
            #print(int(time.time()))

        # TODO POST TO VARIOT HERE
        # data is a json array of json records
        # token constructor parameter will be the API key when VarIOT is ready for that
        # self.dev is the device ID on VarIOT
        # Viewable at http://10.248.101.200:5000/messages/5e4af7041c9d440000f0cd38
        # Post to https?
        # Which side encrypts?  Right now, eliminating this side encryption for VarIOT (hence removal of password from the body and use of crypto from this module
        for payload in recordsdictlist:
        	URL = self.db_path + f'/api/v1/{self.token}/telemetry'
        	r = requests.post(url = URL, json = payload, verify=False, headers={"Content-Type":"application/json"})
        	print('Status code: '+str(r.status_code))
        	print('Payload: '+str(payload))
	
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
        #input_dict['ts'] = int(time.time()) #changed input_dict field to ts from relativetime
        #input_dict['values']={}
        #input_dict['values']['interrogatortime'] = interrogatortime
        #input_dict['values']['relativetime'] = relativetime
        input_dict['interrogatortime'] = interrogatortime
        input_dict['relativetime'] = relativetime
        
        for key in freeform:
        	#input_dict['values'][key] = freeform[key]
            input_dict[key] = freeform[key]
            
        input_dict['values']['db_pw'] = db_pw

        self.insertion_queue.put(input_dict)
        #TODO: Add fetch_since method
        
