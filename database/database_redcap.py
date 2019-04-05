import base64
import os
import numpy
import sys
import traceback
from database import Database
import Queue
import threading
import os
from time import sleep
import pycurl
import json
import cStringIO


class REDCapDatabase(Database):
    def __init__(self, crypto, db_path='https://localhost', token='', dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path, flush=False)
        self.token = token
        self.insertion_queue = Queue.Queue()
        self.dispatcher_thread = threading.Thread(
            target=self.dispatcher, args=())
        self.dispatcher_thread.start()
        self.dispatchsleep = dispatchsleep

    def db_encrypt(self, s, counter):
        # counter = int(counter) % 10^16 # counter must be at most 16 digits
        counter = int(str(counter)[-16:])  # counter must be at most 16 digits

        if type(s) is int:
            val = str(s)
        elif type(s) is float:
            val = str(s)
        else:
            val = s

        aes = self.crypto.get_db_aes(self.db_password, counter)
        padded = self.crypto.pad(val)
        enc = aes.encrypt(padded)
        b64enc = base64.b64encode(enc)
        return b64enc

    def redcap_dispatch(self, recordsdictlist):
        # encrypt on dispatch and add an ID which redcap requires
        for record in recordsdictlist:
            db_pw = record['db_pw']
            del record['db_pw']
            self.db_password = db_pw
            record['rssi'] = self.db_encrypt(
                record['rssi'], record['interrogatortime'])
            record['doppler'] = self.db_encrypt(
                record['doppler'], record['interrogatortime'])
            record['phase'] = self.db_encrypt(
                record['phase'], record['interrogatortime'])
            record['epc96'] = self.db_encrypt(
                record['epc96'], record['interrogatortime'])
            record['record_id'] = str(record['interrogatortime'])

        data = json.dumps(recordsdictlist)

        fields = {
            'token': self.token,
            'content': 'record',
            'format': 'json',
            'type': 'flat',
            'data': data,
        }

        buf = cStringIO.StringIO()
        ch = pycurl.Curl()
        ch.setopt(ch.URL, self.db_path)
        ch.setopt(ch.HTTPPOST, fields.items())
        ch.setopt(ch.WRITEFUNCTION, buf.write)
        ch.setopt(pycurl.SSL_VERIFYPEER, 1)
        ch.setopt(pycurl.SSL_VERIFYHOST, 2)
        ch.perform()
        ch.close()

        #result = buf.getvalue()
        #print '***'
        #print '***'
        #print data
        #print result
        #print '***'
        #print '***'

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
                except Queue.Empty:
                    break

            self.redcap_dispatch(queuelist)

            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

    # just insert into a queue for the dispatcher to insert in the background
    def insert_row(self, relativetime, interrogatortime, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_pw=''):
        input_dict = dict()  # read by the consumer dispatcher
        input_dict['relativetime'] = relativetime
        input_dict['interrogatortime'] = interrogatortime
        input_dict['rssi'] = rssi
        input_dict['epc96'] = epc96
        input_dict['doppler'] = doppler
        input_dict['phase'] = phase
        input_dict['antenna'] = antenna
        input_dict['rospecid'] = rospecid
        input_dict['channelindex'] = channelindex
        input_dict['tagseencount'] = tagseencount
        input_dict['accessspecid'] = accessspecid
        input_dict['inventoryparameterspecid'] = inventoryparameterspecid
        input_dict['lastseentimestamp'] = lastseentimestamp
        input_dict['db_pw'] = db_pw

        self.insertion_queue.put(input_dict)
