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
import collections
import random
import socket
import math
import numpy as np
from datetime import datetime

#added
import requests
import signal
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

#import localization noah class
from localize_noah import localizer


''' 
-------------------------------------------------------------------------------------------------------    
    DESCRPITION
       - executuion begins in start()
            - multiple threads started: start_server(), communication_consumer(), and handler_thread()
        - start_server() is what we really have to focus on
            - This is where we connect to the tag reader and write code to get
              the tag reports back
        - handler_thread() works to process the tag reports we give in
            - puts the information into a standardized data structure that we can send
              to the database for storage
        - communication_consumer() sends those standardized structures to the database
            - we don't have to worry about changing this
-------------------------------------------------------------------------------------------------------    
    START_SERVER (what we focus on)
        - connect to r700 in start_server
        - get tag reports from reader
        - add new tags to self.handler_dequeue using handler_event()
    HANDLER_THREAD (a couple modifications related to field-names)
        - process tags in handler_event into the freeform
            - i.e, make sure relevant data present, set up freeform, etc.
        - This is proccessed into a json that can be easily passed to insert_tag()
        - insert_tag() does some final processing before putting it into self.tag_dicts_queue
    COMMUNICATIONS_CONSUMER
        - communications consumer will take tag dicts from the queue and send them to the db
-------------------------------------------------------------------------------------------------------    
    MODIFICATIONS
    - Added dependencies: requests, signal, urljoin
    - Added connection method using python requests package
    - Append returned events to the handler_dequeue using handler_event method
    - Convert the recieved event to a .json() in handler_thread()
    - Changed the names of relevant and present parameters in handler_thread()
'''

class ImpinjR700(Interrogator):
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0, _antennas=[], _tagpop=4):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address
        self.hostname = 'http://{0}'.format(self.ip_address)
        if len(_antennas) > 0:
            self.antennas = _antennas
        else:
            self.antennas = [1, 2, 3, 4]
        self.tagpop = _tagpop

        self.txPower = 3000
        
        self.fac = None

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)
        
        self.out('Initializing R700 interrogator client')

        #temporarily use these to calculate doppler
        self.last_time={}
        self.last_phase={}

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        # Handle Ctrl+C interrupt (might not be needed)
        signal.signal(signal.SIGINT, self.signal_handler)
        
        self.out('Starting Impinj R700 interrogator client')
        
        reader=self.ip_address 
        toStart='dwsl' #choose a mode to run in (i.e., default)
        #hostname = 'http://{0}'.format(reader)
        
        #try to connect to r700
        try:
            requests.get(urljoin(self.hostname, '/api/v1/status')).raise_for_status()
        except (requests.ConnectionError, requests.exceptions.HTTPError):
            self.out('Error : Unable to connect to the Impinj Reader API on "{0}"'.format(self.hostname))
            if len(self.hostname.split(':')) == 2:
                self.out('        Have you provided the port number with your reader hostname?')
                self.out('        ex.  --reader <your-reader-hostname>:<api-port>')
            sys.exit(1)
        
        requests.post(urljoin(self.hostname, 'api/v1/profiles/stop')) # Stop the active preset
        # Do phase
        #defaultConfig = {"antennaConfigs" : [{"antennaPort": 1, "transmitPowerCdbm": 3000, "inventorySession": 2, "inventorySearchMode": "dual-target", "estimatedTagPopulation": 32, "rfMode": 1110 } ] }
        
        # For after firmware update
        defaultConfig = {"eventConfig": {"common": {"hostname": "disabled"},"tagInventory": {"tagReporting": {"reportingIntervalSeconds": 0,"antennaIdentifier": "antennaPort","tagIdentifier": "epc"},"epc": "enabled","epcHex": "enabled","tid":"enabled","tidHex": "enabled","antennaPort": "enabled","transmitPowerCdbm": "enabled","peakRssiCdbm": "enabled","frequency": "enabled","pc": "enabled","lastSeenTime": "enabled","phaseAngle": "enabled"}}, "antennaConfigs" : [{"antennaPort": 1, "transmitPowerCdbm": self.txPower, "inventorySession": 2, "inventorySearchMode": "dual-target", "estimatedTagPopulation": 32, "rfMode": 1110 } ] }

        #resp = requests.get(urljoin(self.hostname, 'api/v1/profiles/inventory/presets/{0}'.format("default")))
        #print(resp)
        #print(resp.content)

        resp = requests.put(urljoin(self.hostname, 'api/v1/profiles/inventory/presets/{0}'.format(toStart)), data=json.dumps(defaultConfig).encode('utf-8'), headers={"Content-Type": "application/json"})
        # print(json.dumps(defaultConfig).encode('utf-8'))
        #print(resp)
        #print(resp.content)

        requests.post(urljoin(self.hostname, 'api/v1/profiles/inventory/presets/{0}/start'.format(toStart))) # Start the default preset
        for event in requests.get(urljoin(self.hostname, 'api/v1/data/stream'), stream=True).iter_lines(): # Connect to the event stream
            #print for debug
            self.out(event)
            self.handle_event( event )


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
        self.out('R700: start')

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
            #added .json() to be able to parse input_msg like a dict
            input_msg = input_msg.decode("utf-8")    
            input_msg = json.loads(input_msg)  
            input_msgs.append( input_msg )

            # Subtags like <EPC> may or may not be present
            # <RO_ACCESS_REPORT>
            #    <Ver>1</Ver>
            #    <Type>61</Type>
            #    <ID>2323</ID>
            #    <TagReportData>
            #        <EPC-96>
            #            <EPC>00e200600312226a4b000000</EPC>
            #        </EPC-96>
            #        <Antenna>
            #            <Antenna>0001</Antenna>
            #        </Antenna>
            #        <RSSI>
            #            <RSSI>ba</RSSI>
            #        </RSSI>
            # .... also a Timestamp here
            #   and now, with impinj extensions and sllurp
            #    <ImpinjPhase>1744</ImpinjPhase>
            #    <RFDopplerFrequency>234</RFDopplerFrequency>
            #    </TagReportData>
            # </RO_ACCESS_REPORT>

            for msg in input_msgs:
                self.out(msg)

                #tags = msg.msgdict['RO_ACCESS_REPORT']['TagReportData']

                #self.out(tags)
                first_seen_timestamp = msg['timestamp'] 
                epc96 = msg['tagInventoryEvent']['epcHex'] 
                antenna = msg['tagInventoryEvent']['antennaPort'] 
                rssi = msg['tagInventoryEvent']['peakRssiCdbm'] / 100
                transmit_power = msg['tagInventoryEvent']['transmitPowerCdbm'] 
                channelindex = int(((msg['tagInventoryEvent']['frequency'] - 902750) / 500) + 1)
                
                # added phase and doppler reporting
                if 'phaseAngle' in msg['tagInventoryEvent']:
                    phase = msg['tagInventoryEvent']['phaseAngle'] 
                else:
                    phase = 0

                if 'doppler' in msg['tagInventoryEvent']:
                    doppler = msg['tagInventoryEvent']['doppler']
                else:
                    doppler = 0
                
                self.count = self.count + 1
                
                # converted first_seen_timestamp to milliseconds because strptime is incompatible with date format
                first_seen_timestamp = first_seen_timestamp.replace('Z', '')
                first_seen_timestamp_nanos = first_seen_timestamp[-3:]
                first_seen_timestamp_nanos = int(first_seen_timestamp_nanos)
                first_seen_timestamp = first_seen_timestamp[:-3] # remove nanoseconds for strptime
                dt_first_seen_timestamp = datetime.strptime(first_seen_timestamp.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
                first_seen_timestamp = int(dt_first_seen_timestamp.timestamp() * 1000000)
               # first_seen_timestamp = first_seen_timestamp + first_seen_timestamp_nanos

                # if this is the "first" firstseentimestamp, note that so the other times will be relative to that
                if self.start_timestamp == 0:
                    self.start_timestamp = first_seen_timestamp

                self.latest_timestamp = first_seen_timestamp
               

                lastseentimestamp = first_seen_timestamp
                
                #TODO: calculate doppler here
                if not epc96 in self.last_phase.keys():
                    doppler=0
                else:
                    if lastseentimestamp==self.last_time[epc96]:
                        doppler=0
                        self.out('doppler: no delta time')
                    else:
                        doppler=(1/(4*math.pi))*(phase-self.last_phase[epc96])/(lastseentimestamp-self.last_time[epc96])
                
                self.last_phase[epc96]=phase
                self.last_time[epc96]=lastseentimestamp

                # doppler = 0
                # phase = 0
                rospecid = 1
                tagseencount = 1
                accessspecid = 1
                inventoryparameterspecid = 1                
                
                self.out('phase was: {}'.format(phase))
                phase = phase*math.pi/180
                self.out('phase is: {}'.format(phase))

                freeform = {}
                freeform['rssi'] = rssi
                freeform['epc96'] = epc96
                freeform['doppler'] = doppler
                freeform['phase'] = phase
                freeform['antenna'] = antenna
                freeform['rospecid'] = rospecid
                freeform['channelindex'] = channelindex
                freeform['tagseencount'] = tagseencount
                freeform['accessspecid'] = accessspecid
                freeform['inventoryparameterspecid'] = inventoryparameterspecid
                freeform['lastseentimestamp'] = lastseentimestamp
            
                freeformjson = json.dumps(freeform)

                # call self.insert_tag to insert into database
                self.insert_tag(first_seen_timestamp, freeformjson, self.start_timestamp)
                                

                """for tag in tags:
                    #changes
                    '''
                    FirstSeenTimestampUTC -> timestamp
                    EPC-96 -> epc
                    AntennaID -> antennaPort
                    PeakRSSI -> peakRssiCbdm
                    '''
                    if 'timestamp' in tag and 'epc' in tag and 'antennaPort' in tag and 'peakRssiCdbm' in tag:
                        first_seen_timestamp = tag['timestamp'][0]
                        epc96 = tag['epc'].decode("utf-8")
                        antenna = tag['antennaPort'][0]
                        rssi = tag['peakRssiCdbm'][0]
                    else:
                        self.out(
                            "Message did not contain all elements\n" + str(tag))
                        continue

                    # Optional parameters from sllurp library for Impinj
                    if 'RFDopplerFrequency' in tag:
                        doppler = tag['RFDopplerFrequency']
                    else:
                        doppler = "-65536"
                    
                    #changed
                    if 'phaseAngle' in tag:
                        phase = tag['phaseAngle']
                    else:
                        phase = "-65536"

                    if 'ROSpecID' in tag:
                        rospecid = tag['ROSpecID'][0]
                    else:
                        rospecid = "-1"

                    if 'ChannelIndex' in tag:
                        channelindex = tag['ChannelIndex'][0]
                    else:
                        channelindex = "-1"

                    if 'TagSeenCount' in tag:
                        tagseencount = tag['TagSeenCount'][0]
                    else:
                        tagseencount = "-1"
                        
                    #changed
                    if 'lastSeenTime' in tag:
                        lastseentimestamp = tag['lastSeenTime'][0]
                    else:
                        lastseentimestamp = "-1"

                    if 'AccessSpecID' in tag:
                        accessspecid = tag['AccessSpecID'][0]
                    else:
                        accessspecid = "-1"

                    if 'InventoryParameterSpecID' in tag:
                        inventoryparameterspecid = tag['InventoryParameterSpecID'][0]
                    else:
                        inventoryparameterspecid = "-1"

                    self.count = self.count + 1

                    # if this is the "first" firstseentimestamp, note that so the other times will be relative to that
                    if self.start_timestamp == 0:
                        self.start_timestamp = first_seen_timestamp

                    self.latest_timestamp = first_seen_timestamp
                    
                    freeform = {}
                    freeform['rssi'] = rssi
                    freeform['epc96'] = epc96
                    freeform['doppler'] = doppler
                    freeform['phase'] = phase
                    freeform['antenna'] = antenna
                    freeform['rospecid'] = rospecid
                    freeform['channelindex'] = channelindex
                    freeform['tagseencount'] = tagseencount
                    freeform['accessspecid'] = accessspecid
                    freeform['inventoryparameterspecid'] = inventoryparameterspecid
                    freeform['lastseentimestamp'] = lastseentimestamp
                    
                    if self.reconfigurableantennastate != -1: # if we're using reconfigurable antennas, include the state
                        freeform['antennastate'] = self.reconfigurableantennastate
                    
                    freeformjson = json.dumps(freeform)

                    # call self.insert_tag to insert into database
                    self.insert_tag(first_seen_timestamp, freeformjson, self.start_timestamp)
"""
    def close_server(self):
        #if getting rid of fac clients, need to change this
        self.exiting = True
        requests.post(urljoin(self.hostname, 'api/v1/profiles/stop')) # Stop the active preset
        try:
            reactor.stop()
        except:
            pass
        if not (self.fac is None):
            self.fac.politeShutdown()
            if not (self.fac.proto is None):
                self.fac.proto.exiting = True

    def __del__(self):
        self.close_server()

    def insert_tag(self, first_seen_timestamp, freeformjson, start_timestamp):
        freeform = json.loads(freeformjson)
        
        peak_rssi = freeform['rssi']
        if peak_rssi >= 128:  # convert to signed
            peak_rssi = peak_rssi - 256
        freeform['rssi'] = peak_rssi
        
        epc = freeform['epc96']
        antenna = freeform['antenna']
        phase = freeform['phase']
        channelindex = freeform['channelindex']
        doppler = freeform['doppler']
        antennastate = '-1'
        if 'antennastate' in freeform:
            antennastate = freeform['antennastate']
        self.out("Adding tag %s with RSSI %s and timestamp %s and ID %s on antenna %s with Phase %s and Doppler %s and Channel %s and antenna state %s" % (
            str(self.count), str(peak_rssi), str(first_seen_timestamp), str(epc), str(antenna), str(phase), str(doppler), str(channelindex), str(antennastate)))

        input_dict = dict()
        input_dict['data'] = dict()
        input_dict['data']['db_password'] = self.db_password
        input_dict['data']['freeform'] = freeform
        input_dict['data']['relative_time'] = first_seen_timestamp - \
            start_timestamp
        input_dict['data']['interrogator_time'] = first_seen_timestamp

        self.tag_dicts_queue.put(input_dict)  # read by the consumer
        
        self.antennathreadhistory.put(input_dict)

    def signal_handler(self, signal, frame):
        self.close_server()
        sys.exit(0)




# Requires:
# easy_install httplib2 (not pip)
