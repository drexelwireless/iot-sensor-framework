from interrogator import *
import threading
import json
import sys
from sllurp import llrp
from twisted.internet import reactor
import os
import queue
from time import sleep
import collections

class ImpinjR420(Interrogator):
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0, _antennas=[], _tagpop=4):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address
        if len(_antennas) > 0:
            self.antennas = _antennas
        else:
            self.antennas = [1, 2, 3, 4]
        self.tagpop = _tagpop
        
        self.fac = None

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

            resp, content = Interrogator.sendhttp(url, headerdict={'Content-Type': 'application/json; charset=UTF-8'}, bodydict=input_dicts, method='PUT')

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
        self.out("Adding tag %s with RSSI %s and timestamp %s and ID %s on antenna %s with Phase %s and Doppler %s and Channel %s" % (
            str(self.count), str(peak_rssi), str(first_seen_timestamp), str(epc), str(antenna), str(phase), str(doppler), str(channelindex)))

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
