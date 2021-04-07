from interrogator import *
import threading
import json
import sys
from httplib2 import Http
import os
import queue
from time import sleep, time
import collections
import random
import socket
import math
import numpy as np

class input_cell:
    def __init__( self, _time, _rssi, _antenna_num, _antenna_port ):
        self.time = _time
        self.antenna_num = _antenna_num
        self.antenna_port = _antenna_port
        self.rssi = _rssi

class output_cell:
    def __init__( self, _location1, _location2, _fusedlocation ):
        self.location1 = _location1
        self.location2 = _location2
        self.fusedlocation = _fusedlocation
        
class NoopDriver(Interrogator):
    #TODO: create data structures for storing data
    #add a queue for readings
    
    #queue for noah's values\
    #queue for kevin adn ian values
    
    input_readings = {}
    output_locations = {}
    
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)
        
        self.out('Initializing noop interrogator client')

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.out('Starting Impinj noop interrogator client')
        
        while not self.exiting:
            tsutc = int(time() * 1e6)
            
            rssirnd = random.randint(-10, 10)
            rssi = 186 + rssirnd
            
            msg = {}
            msg['RO_ACCESS_REPORT'] = {}
            msg['RO_ACCESS_REPORT']['TagReportData'] = []
            
            tag = {}
            tag['FirstSeenTimestampUTC'] = tsutc
            tag['AntennaID'] = 1
            tag['PeakRSSI'] = rssi
            tag['EPC-96'] = '000011112222333344445555'
            tag['RFDopplerFrequency'] = 0
            tag['ImpinjPhase'] = 0
            tag['ROSpecID'] = 0
            tag['ChannelIndex'] = 0
            tag['TagSeenCount'] = 1
            tag['LastSeenTimestampUTC'] = tsutc
            tag['AccessSpecID'] = 0
            tag['InventoryParameterSpecID'] = 0
            
            msg['RO_ACCESS_REPORT']['TagReportData'].append(tag)
            
            self.handle_event(msg)
            
            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)            

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
        self.out('noop: start')

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
        self.tag_count++
        if self.tag_count%100==0:
            
        
    #TODO: copy paste in localization algorithm
    def noah_localize( epc, inputArray ):
        #store data for processing
        readings=inputArray        
        #define the mapping from quadrant to position using unit vectors:
        pos = {
               0:[math.sqrt(2)/2, math.sqrt(2)/2],
               1:[-math.sqrt(2)/2,math.sqrt(2)/2],
               2:[-math.sqrt(2)/2,-math.sqrt(2)/2],
               3:[math.sqrt(2)/2,-math.sqrt(2)/2]
               }
        
        #Get the frequency of each quadrant for this epc
        #def countQuads( epc, readings ):
        quad_freq = []
        total_reads = 0
        for i in readings:
            i_epc = i[ 'epc96' ]
            i_quad = i[ 'antennastate' ]
            if i_epc == epc:
                quad_freq[ i_quad ] += 1
                total_reads += 1
            
        #Remove multipath here
        #start by getting the quadrant with the most reads
        for i in range(len( quad_freq )):
            if quad_freq[i]==max( quad_freq ):
                strongest_quad = i
        
        #get the reflected quadrant from the strongest and remove reads                    
        reflected_quad = (strongest_quad+(2)) % (2)
        total_reads-= quad_freq[ reflected_quad ]
        quad_freq[ reflected_quad ] = 0
        
        #normalize quadrant frequency
        for j in range(len(quad_freq)):
            quad_freq[j]/=total_reads
        
        #Calculate the weighted location
        x_est = 0
        y_est = 0

        for i in range(len(quad_freq)):
            x_est += quad_freq[i]*pos[i][0]
            y_est += quad_freq[i]*pos[i][1]

        rv = [ x_est, y_est ]
        #return dict of locations per epc ????
        return rv
    
    def KevinandIanLocalize(self,epc):
        xyCoor = {}
        # Check out extended and unscented Kalman filter
        # this will go into a queue where each element is an array of all the vectors for one tag reading
        for key in epc: # for each epc...
            xyCoor[key] = []
            for i in range( len( epc[key] ) ): # for each antenna reading of the epc
                tempCoor = [0, 0]
                temp = epc[key][i]
                
                rssi = temp['rssi']
                phase = temp['phase']
                port = temp['port']
                antennastate = temp['antennastate']
                tempCoor[0] = abs( rssi ) * np.cos(
                    phase + (np.pi / 2 * port) + (np.pi / 4 * antennastate) )  # X coordinate
                tempCoor[1] = abs( rssi ) * np.sin(
                    phase + (np.pi / 2 * port) + (np.pi / 4 * antennastate) )  # Y coordinate
                xyCoor[key].append( tempCoor )

        # if queue.full():
        #     queue.get()
        #     queue.put(xyCoor)
        # else:
        #     queue.put(xyCoor)
        return xyCoor #dict of locations per epc
    
    #TODO: copy paste in (when we call it, put it in sweep mode)
    def MattAlgo():
        return 
    
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

                tags = msg['RO_ACCESS_REPORT']['TagReportData']

                self.out(tags)
                
                #TODO: add antenna_state to list of things to get
                for tag in tags:
                    if 'FirstSeenTimestampUTC' in tag and 'EPC-96' in tag and 'AntennaID' in tag and 'PeakRSSI' in tag:
                        first_seen_timestamp = tag['FirstSeenTimestampUTC']
                        epc96 = tag['EPC-96']
                        antenna = tag['AntennaID']
                        rssi = tag['PeakRSSI']
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
                        rospecid = tag['ROSpecID']
                    else:
                        rospecid = "-1"

                    if 'ChannelIndex' in tag:
                        channelindex = tag['ChannelIndex']
                    else:
                        channelindex = "-1"

                    if 'TagSeenCount' in tag:
                        tagseencount = tag['TagSeenCount']
                    else:
                        tagseencount = "-1"

                    if 'LastSeenTimestampUTC' in tag:
                        lastseentimestamp = tag['LastSeenTimestampUTC']
                    else:
                        lastseentimestamp = "-1"

                    if 'AccessSpecID' in tag:
                        accessspecid = tag['AccessSpecID']
                    else:
                        accessspecid = "-1"

                    if 'InventoryParameterSpecID' in tag:
                        inventoryparameterspecid = tag['InventoryParameterSpecID']
                    else:
                        inventoryparameterspecid = "-1"

                    self.count = self.count + 1

                    # if this is the "first" firstseentimestamp, note that so the other times will be relative to that
                    if self.start_timestamp == 0:
                        self.start_timestamp = first_seen_timestamp

                    self.latest_timestamp = first_seen_timestamp
                    
                    #Add relevant info to data structure to store previous reads
                    data = input_cell( first_seen_timestamp, rssi, antenna, antenna_state)
                    input_readings[epc96].append(data)
                    #TODO: update locations and data structures
                    noahloc = noah_localize(epc96, input_readings[epc96] )
                    kevinandianloc = getLocation(epc)
                    
                    locations = output_cell( noahloc, kevinandianloc, (0,0) )
                    output_locations[epc96].append(locations)
                    
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
                    freeform['antennastate'] = -1
                    freeform['noahloc'] = noahloc
                    freeform['kevinandianloc'] = kevinandianloc
                    #freeform['filteredloc'] = filtered
                    
                    
                    freeformjson = json.dumps(freeform)

                    # call self.insert_tag to insert into database
                    self.insert_tag(first_seen_timestamp, freeformjson, self.start_timestamp)

    def close_server(self):
        self.exiting = True

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
        self.out("Adding tag %s with RSSI %s and timestamp %s and ID %s on antenna %s with Phase %s and Doppler %s and Channel %s" % (
            str(self.count), str(peak_rssi), str(first_seen_timestamp), str(epc), str(antenna), str(doppler), str(phase), str(channelindex)))

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
