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

# TODO - integrate into main driver with self.reconfigurableantennastate=-1 in start as default for no antenna swapping, check in when appropriate
class ImpinjR420Reconfigurable(Interrogator):
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0, _antennas=[], _tagpop=4, _antennaclientip="localhost", _antennaclientport=8080, _reconfigurableantennas=4, _antennastatesleep=5, _reconfigurableantennatagmonitor=None):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address
        
        # antenna ports on the interrogator itself, not the reconfigurable ones
        if len(_antennas) > 0:
            self.antennas = _antennas
        else:
            self.antennas = [1, 2, 3, 4]
        self.tagpop = _tagpop
        
        self.fac = None

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)
         
        # *** Begin Reconfigurable Antenna configuration
        self.k = _reconfigurableantennas # k is the number of reconfigurable antennas to select
        
        # This is required
        if self.k == 0:
            self.reconfigurableantennastate = -1 # do not use reconfigurable antenna thread
        else:
            self.reconfigurableantennastate = 0 # default reconfigurable antenna state, which goes 1 through k
            
        self.running_max_relative_time = 0
        self.antennastatesleep = _antennastatesleep # how long to wait to allow the history queue to fill up to pick the next antenna state
        self.reconfigurableantennatagmonitor = _reconfigurableantennatagmonitor # this is the EPC tag to check for RSSI history; or set to None for all tags
        self.antennaclientip = _antennaclientip
        self.antennaclientport = _antennaclientport
        # *** End Reconfigurable Antenna configuration
        
        self.out('Initializing R420 interrogator client')

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.out('Starting Impinj R420 interrogator client')

        # Create Clients and set them to connect
        self.fac = llrp.LLRPClientFactory(report_every_n_tags=1,  
                                     antennas=self.antennas,
                                     tx_power=81,  # was 0, 81 is 30 dbm, 91 is max 32.5 dbm
                                     session=2,  
                                     start_inventory=True,
                                     mode_identifier=0, # sllurp inventory --mode-identifier N interrogator.ip.local
                                     tag_population=self.tagpop,  # The interrogator can only handle 90 reads per second over ethernet; if the read rate is greater than this, only 90 per second will be processed, up to 5000 per minute.  If 5000 tags is reached before one minute's time, lag will be introduced as a shorter amount of time will be obtained.  Setting to tag population of 16 enables 2 tags; tag population of 4 is best for 1 tag.  Best to parameterize this
                                     tag_content_selector={
                                         'EnableROSpecID': True,
                                         'EnableSpecIndex': True,
                                         'EnableInventoryParameterSpecID': True,
                                         'EnableAntennaID': True,
                                         'EnableChannelIndex': True,
                                         'EnablePeakRSSI': True,  
                                         'EnableFirstSeenTimestamp': True,
                                         'EnableLastSeenTimestamp': True,
                                         'EnableTagSeenCount': True,
                                         'EnableAccessSpecID': True
                                     },
                                     impinj_tag_content_selector={
                                         'EnablePeakRSSI': True,
                                         'EnableRFPhaseAngle': True,
                                         'EnableRFDopplerFrequency': True
                                     })

        self.fac.addTagReportCallback(self.handle_event)

        self.out('Starting Reactor TCP client')

        reactor.connectTCP(self.ip_address, 5084, self.fac, timeout=5)
        reactor.run()

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
        
        if self.reconfigurableantennastate != -1:
            # If using reconfigurable antenna, start the reconfigurable antenna thread that monitors the RSSI and picks the next antenna state
            self.antennathreadhistory = queue.Queue()
            self.R = [0] * self.k # R is the recent RSSI history for each selected antenna in the k'th position
            self.antennaclientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.antennaclientsocket.connect((self.antennaclientip, self.antennaclientport))
            self.antennathread = threading.Thread(target=self.select_antenna, args=())
            self.antennathread.start()        

        self.start_server()
   
    # ***** Antenna State Selection with Adaptive Pursuit
    def avg(self, arr):
        if len(arr) == 0:
            return 0
            
        sum = 0
        
        for i in range(len(arr)):
            sum = sum + arr[i]
            
        return sum / len(arr)
    
    # we're assuming the antenna state update is immediate, so we may think the antenna state is one thing when it is really another, and record values from that.  This should converge thanks to the leaky integrator.
    def send_antenna_state(self, state):
        antenna = str(state + 1) # controller uses state numbers starting at 1
        state = str(state)
        self.out("Sending value %s to antenna" % (str(state)))
        self.reconfigurableantennastate = state
        self.antennaclientsocket.send(antenna.encode())

    def find_Max(self, p):
        maxx = p[0]
        
        for i in range(len(p)):
            if p[i] > maxx:
                maxx = p[i]
        
        return maxx
                
    def random_Distribution(self, arr):
        return np.random.choice(range(len(arr)), 1, p=arr/np.sum(arr))
        
    ##### # TODO: could change this to be the average of the last 5 seconds for each antenna
    ##### # TODO: if no tags are seen for a period, sweep, and do that sweep in the beginning
    def get_recent_antenna_RSSI(self, max_age = 5e6, go_back_n=100):
        # Given self.k antennas, loop backwards over self.antennathreadhistory, which are tag_dict, to get the most recent RSSI for each antenna,
        # which we set in self.R.  Clear self.R before we begin so that we don't select based on old readings if an antenna goes out of range.
        newR = [0] * self.k
        
        # no data? return no score
        if self.antennathreadhistory.qsize() == 0:
            self.R = newR
            self.antenna_sweep()
            return self.R
            
        antenna_history_items = []

        antenna_history_item = self.antennathreadhistory.get(block=True)
        antenna_history_items.append(antenna_history_item)

        # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
        # while we're here, try to pick up any more items that were inserted into the queue
        ##### # TODO: perhaps add a release clause so we don't infinitely read from the interrogator this round (i.e., stop after N seconds of reading or N records)
        tag_reads = 0
        while tag_reads < go_back_n:
            try:                
                antenna_history_item = self.antennathreadhistory.get_nowait()
                antenna_history_items.append(antenna_history_item)
                
                tag_reads = tag_reads + 1
            except queue.Empty:
                break 

        #print(antenna_history_items)
                
        # keep track of the max relative time that we've seen so we can track the age of these tags
        # so that we only consider recent history
        for antenna_history_item in antenna_history_items:
            if float(antenna_history_item['data']['relative_time']) > self.running_max_relative_time: 
                self.running_max_relative_time = float(antenna_history_item['data']['relative_time'])
        
        # if a monitor tag epc is provided, filter out non-matching epc96 tags
        matching_items = []
        for item in antenna_history_items:
            if (self.reconfigurableantennatagmonitor is None) or item['data']['epc96'] == self.reconfigurableantennatagmonitor:
                matching_items.append(item)
                
        #print(matching_items)
        
        ##### # TODO: if len(matching_items) == 0 (or perhaps < N but let's say 0 for now) then call antenna sweep (which you'll write) and just return self.R without modification (assume its state this round has remained the same)
        if len(matching_items) == 0:
            self.antenna_sweep()
        else:
            rssidict = {}
            
            # for each antenna, gather their recent rssi's
            for i, item in reversed(list(enumerate(matching_items))):
                rssi = float(item['data']['freeform']['rssi'])
                antennastate = int(item['data']['freeform']['antennastate'])
                relative_time = float(item['data']['relative_time'])
                epc96 = item['data']['freeform']['epc96']
                age = relative_time - self.running_max_relative_time # in microseconds
                
                # Filter the tags for the monitoring tag (or use all tags if the monitor is None
                if (self.reconfigurableantennatagmonitor is None) or self.reconfigurableantennatagmonitor == epc96:            
                    # add 129 to the rssi so that it becomes positive for scoring, so our default 0 is always the smallest
                    rssi = 129 + rssi
                    
                if not (antennastate in rssidict):
                    rssidict[antennastate] = []
                    
                rssidict[antennastate].append(rssi)
            
            # compute the recent average RSSI for each antenna (or 0 if no reads found for that antenna)
            for i in range(self.k):
                if not (i in rssidict):
                    newR[i] = 0
                else:
                    newR[i] = self.avg(rssidict[i])

            self.R = newR
            
        #print(self.R)
        
        return self.R

    ######  # TODO: antenna sweep function shoud loop for i in range(self.k), and call self.send_atenna_state(i), then sleep for self.antennastatesleep time
    def antenna_sweep(self):
        for i in range(self.k):
            self.send_antenna_state(i)
            sleep(self.antennastatesleep)
     
    # make an intelligent antenna selection that is non-random
    # using the adaptive pursuit algorithm
    # look in the self.antennathreadhistory array for history data
    ##### # TODO: occasionally, sweep all the antennas and update their scores
    def select_antenna(self, alpha = 0.8, beta = 0.8, Pmax = 0.8, Pmin=0.2):
        p = [1/self.k] * self.k # p is the probability of selecting an antenna in the k'th index
        q = [0] * self.k # q is the recent RSSI leaky integrator weighted average score for a given antenna in the k'th index
        
        while not self.exiting:   
            #######     # TODO: generate a random number between 1 and 20 and if it's 20 call sweep function, ELSE do what's below
            if random.randint(1,20) == 20:
                self.out("Performing sweep...")
                self.antenna_sweep()
            else:
                self.R = self.get_recent_antenna_RSSI()
                
                self.out("R: %s" % (str(self.R)))
                
                for i in range(len(q)):
                    q[i] = (1 - alpha)*q[i] + alpha * self.R[i]
                
                Rmax = self.find_Max(self.R)
                
                for i in range(len(p)):
                    if self.R[i]==Rmax:
                        p[i] += beta * (Pmax - p[i])
                    else:
                        p[i] += beta * (Pmin - p[i])
                
                state = self.random_Distribution(p) 
                
                self.send_antenna_state(state)
                
                # sleep for a moment no matter what so that more data can arrive into self.antennathreadhistory
                if self.antennastatesleep:
                    sleep(self.antennastatesleep) 

    # ***** End: Antenna State Selection with Adaptive Pursuit
    
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

                tags = msg.msgdict['RO_ACCESS_REPORT']['TagReportData']

                self.out(tags)

                for tag in tags:
                    if 'FirstSeenTimestampUTC' in tag and 'EPC-96' in tag and 'AntennaID' in tag and 'PeakRSSI' in tag:
                        first_seen_timestamp = tag['FirstSeenTimestampUTC'][0]
                        epc96 = tag['EPC-96'].decode("utf-8")
                        antenna = tag['AntennaID'][0]
                        rssi = tag['PeakRSSI'][0]
                    else:
                        self.out(
                            "Message did not contain all elements\n" + str(tag))
                        continue

                    # Optional parameters from sllurp library for Impinj
                    if 'RFDopplerFrequency' in tag:
                        doppler = tag['RFDopplerFrequency']
                    else:
                        doppler = "-65536"

                    if 'ImpinjPhase' in tag:
                        phase = tag['ImpinjPhase']
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

                    if 'LastSeenTimestampUTC' in tag:
                        lastseentimestamp = tag['LastSeenTimestampUTC'][0]
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

    def close_server(self):
        self.exiting = True
        
        try:
            reactor.stop()
            
            if not (self.fac is None):
                self.fac.politeShutdown()
                if not (self.fac.proto is None):
                    self.fac.proto.exiting = True
        except:
            self.out('R420: error shutting down the interrogator')

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
        self.out("Adding tag %s with RSSI %s and timestamp %s and ID %s on antenna %s with Phase %s and Doppler %s and Channel %s and Antenna State %s" % (
            str(self.count), str(peak_rssi), str(first_seen_timestamp), str(epc), str(antenna), str(phase), str(doppler), str(channelindex), str(antennastate)))

        input_dict = dict()
        input_dict['data'] = dict()
        input_dict['data']['db_password'] = self.db_password
        input_dict['data']['freeform'] = freeform
        input_dict['data']['relative_time'] = first_seen_timestamp - \
            start_timestamp
        input_dict['data']['interrogator_time'] = first_seen_timestamp

        self.tag_dicts_queue.put(input_dict)  # read by the consumer

        # add input_dict to our own local array called self.antennathreadhistory
        self.antennathreadhistory.put(input_dict)
        
# Requires:
# easy_install httplib2 (not pip)
