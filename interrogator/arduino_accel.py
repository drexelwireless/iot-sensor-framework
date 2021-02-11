from interrogator import *
import threading
import json
import sys
from httplib2 import Http
from sllurp import llrp
from twisted.internet import reactor
import os
import queue
from time import sleep
import time
import collections
import serial # pip install pyserial

class ArduinoAccel(Interrogator):
    def __init__(self, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0, _port="/dev/cu.SLAB_USBtoUART", _baud=9600, _parity=serial.PARITY_NONE, _rtscts=0, _xonxoff=0, _bytesize=serial.EIGHTBITS, _stopbits=serial.STOPBITS_ONE):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)
            
        self.port = _port
        self.baud = _baud
        self.parity = _parity
        self.rtscts = _rtscts
        self.xonxoff = _xonxoff
        self.bytesize = _bytesize
        self.stopbits = _stopbits

        self.out('Initializing accelerometer interrogator client')

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.out('Starting accelerometer interrogator client')
        
        self.start_timestamp = 0

        self.ser = serial.Serial(port=self.port, baudrate=self.baud, parity=self.parity, rtscts=self.rtscts, xonxoff=self.xonxoff, timeout=1, bytesize=self.bytesize, stopbits=self.stopbits)
        self.buf = []
        
        while not self.exiting:
            try:
                x = ser.read()
                #print(x)
            except:
                #print("Failed to read")
                pass
            self.buf.extend(bytearray(x))

            if x == b'\n':
                #print("Received")
                bufs = bytes(self.buf)
                line = bufs.decode('utf-8')
                timestamp = round(time.time() * 1000)
                
                # print(line) # processing code here      
                self.handle_event((timestamp, line))
                
                self.buf = []              
       
    def communication_consumer(self):
        url = self.db_host + '/api/rssi'

        while not self.exiting:
            input_dicts = []

            input_dict = self.tag_dicts_queue.get(block=True)
            input_dicts.append(input_dict)

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_dict = self.tag_dicts_queue.get_nowait()
                    input_dicts.append(input_dict)
                except queue.Empty:
                    break

            resp, content = self.http_obj.request(uri=url, method='PUT', headers={
                                                  'Content-Type': 'application/json; charset=UTF-8'}, body=json.dumps(input_dicts))

            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

    def start(self):
        self.out('R420: start')

        self.handler_dequeue = collections.deque()
        self.handler_thread = threading.Thread(
            target=self.handler_thread, args=())
        self.handler_thread.start()

        self.tag_dicts_queue = queue.Queue()
        self.communication_thread = threading.Thread(
            target=self.communication_consumer, args=())
        self.communication_thread.start()

        self.start_server()

    def handle_event(self, msg):
        self.handler_dequeue.append(msg)

    def handler_thread(self):
        while not self.exiting:
            if len(self.handler_dequeue) == 0:
                if self.dispatchsleep > 0:
                    sleep(self.dispatchsleep)
                continue

            input_msgs = []

            input_msg = self.handler_dequeue.popleft()
            input_msgs.append(input_msg)

            #### TODO
            for (line, timestamp) in input_msgs:
                tokens = line.split()
                #print(tokens)
                
                xval = tokens[1]
                yval = tokens[3]    
                zval = tokens[5]   
                
                freeform = {}
                freeform['xval'] = xval
                freeform['yval'] = yval
                freeform['zval'] = zval
            
                # if this is the "first" firstseentimestamp, note that so the other times will be relative to that
                if self.start_timestamp == 0:
                    self.start_timestamp = timestamp

                self.latest_timestamp = timestamp
                
                freeformjson = json.dumps(freeform)

                # call self.insert_tag to insert into database
                self.insert_tag(timestamp, freeformjson, self.start_timestamp)

    def close_server(self):
        self.exiting = True
        self.fac.politeShutdown()
        reactor.stop()
        if not (self.fac is None):
            if not (self.fac.proto is None):
                self.fac.proto.exiting = True

    def __del__(self):
        self.close_server()

    def insert_tag(self, first_seen_timestamp, freeformjson, start_timestamp):
        freeform = json.loads(freeformjson)

        input_dict = dict()
        input_dict['data'] = dict()
        input_dict['data']['db_password'] = self.db_password
        input_dict['data']['freeform'] = freeform
        input_dict['data']['relative_time'] = first_seen_timestamp - \
            start_timestamp
        input_dict['data']['interrogator_time'] = first_seen_timestamp

        self.tag_dicts_queue.put(input_dict)  # read by the consumer


# Requires:
# easy_install httplib2 (not pip)
