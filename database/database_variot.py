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


class VarIOTDatabase(Database):
    def __init__(self, crypto, db_path='http://10.248.101.200:5000', token='', device='0000000000', dispatchsleep=0):
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
            del record['db_pw']
            
        data = json.dumps(recordsdictlist)

        # TODO POST TO VARIOT HERE
        # data is a json array of json records
        # token constructor parameter will be the API key when VarIOT is ready for that
        # self.dev is the device ID on VarIOT
        # Viewable at http://10.248.101.200:5000/messages/5e4af7041c9d440000f0cd38
        # Post to https?
        # Which side encrypts?  Right now, eliminating this side encryption for VarIOT (hence removal of password from the body and use of crypto from this module
        payload = {'data': json.dumps(data)}
        URL = self.db_path + '/api/v1/hub/message/rfid?address=' + self.dev
        r = requests.post(url = URL, json = payload)

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
