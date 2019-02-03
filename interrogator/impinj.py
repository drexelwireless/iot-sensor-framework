from interrogator import *
import threading
import json
import sys
import Queue
import os
from httplib2 import Http
from llrp_proto import *
from time import sleep

# llrp_proto GPLv2 statement:
# Copyright (C) 2009 Rodolfo Giometti <giometti@linux.it>
# Copyright (C) 2009 CAEN RFID <support.rfid@caen.it>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA


class Impinj(Interrogator):
    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _dispatchsleep=0):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.ip_address = _ip_address

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.rospec = None  # to facilitate early shutdown
        self.server = None
        self.client_thread = None

        # Connect with remote LLRPd
        self.out('connecting with ' + self.ip_address + '... ')
        try:
            self.server = LLRPdConnection(
                self.ip_address, event_cb=self.handle_event)
        except LLRPResponseError, ret:
            self.out('fail: %s' % ret)
            sys.exit(1)

        # Get reader capabilities
        self.out('asking for reader capabilities... ')
        try:
            self.cap = self.server.get_capabilities('LLRP Capabilities')
        except LLRPResponseError, ret:
            self.out('fail: %s' % ret)
            sys.exit(1)

        # Delete all existing ROSpecs
        self.out('deleting all existing ROSpecs... ')
        try:
            self.server.delete_all_rospec()
        except LLRPResponseError, ret:
            self.out('fail: %s' % ret)
            sys.exit(1)

        # Create a ROSpec
        self.rospec = LLRPROSpec(1, 0, 'Disabled', 9, 1)  # was 123

        # Add ROSpec
        self.out('adding ROSpec... ')
        self.rospec.add(self.server)

        # Enable ROSpec
        self.out('enabling ROSpec... ')
        try:
            self.rospec.enable(self.server)
        except LLRPResponseError, ret:
            self.out('fail: %s' % ret)
            sys.exit(1)

        # Start ROSpec
        self.out('starting ROSpec... ')
        try:
            self.rospec.start(self.server)
        except LLRPResponseError, ret:
            self.out('fail: %s' % ret)
            sys.exit(1)

    def __del__(self):
        self.close_server()

    def close_server(self):
        if self.rospec:
            # Stop ROSpec
            self.out('stopping ROSpec... ')
            try:
                self.rospec.stop(self.server)
            except LLRPResponseError, ret:
                self.out('fail: %s' % ret)
                os._exit(1)

            # Disable ROSpec
            self.out('disabling ROSpec... ')
            try:
                self.rospec.disable(self.server)
            except LLRPResponseError, ret:
                self.out('fail: %s' % ret)
                os._exit(1)

            # Delete ROSpec
            self.out('deleting ROSpec... ')
            try:
                self.rospec.delete(self.server)
            except LLRPResponseError, ret:
                self.out('fail: %s' % ret)
                os._exit(1)

        if self.server:
            # Close connection
            self.out('disconnecting from ' + self.ip_address + '... ')
            self.server.close()

        if self.client_thread:
            self.client_thread.stop()

        os._exit(0)

    def communication_consumer(self):
        url = self.db_host + '/api/rssi'

        while 1:
            input_dicts = []

            input_dict = self.tag_dicts_queue.get(block=True)
            input_dicts.append(input_dict)

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_dict = self.tag_dicts_queue.get_nowait()
                    input_dicts.append(input_dict)
                except Queue.Empty:
                    break

            resp, content = self.http_obj.request(uri=url, method='PUT', headers={
                                                  'Content-Type': 'application/json; charset=UTF-8'}, body=json.dumps(input_dicts))

            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

    def start(self):
        self.handler_queue = Queue.Queue()
        self.handler_thread = threading.Thread(
            target=self.handler_thread, args=())
        self.handler_thread.start()

        self.tag_dicts_queue = Queue.Queue()
        self.client_thread = threading.Thread(
            target=self.start_server, args=())
        self.client_thread.start()

        self.communication_thread = threading.Thread(
            target=self.communication_consumer, args=())
        self.communication_thread.start()

    def handle_event(self, connection, msg):
        self.handler_queue.put(msg)

    def handler_thread(self):
        while 1:
            input_msgs = []

            input_msg = self.handler_queue.get(block=True)
            input_msgs.append(input_msg)

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_msgs = self.handler_queue.get_nowait()
                    input_msgs.append(input_msg)
                except Queue.Empty:
                    break

            # <RO_ACCESS_REPORT>
            #	<Ver>1</Ver>
            #	<Type>61</Type>
            #	<ID>2323</ID>
            #	<TagReportData>
            #		<EPC-96>
            #			<EPC>00e200600312226a4b000000</EPC>
            #		</EPC-96>
            #		<Antenna>
            #			<Antenna>0001</Antenna>
            #		</Antenna>
            #		<RSSI>
            #			<RSSI>ba</RSSI>
            #		</RSSI>
            # .... also a Timestamp here
            #	</TagReportData>
            # </RO_ACCESS_REPORT>

            for msg in input_msgs:
                self.out(msg)

                repevents = [
                    'RO_ACCESS_REPORT',
                ]

                if msg.keys()[0] in repevents:
                    try:  # sanity check that a message was received with a TagReportData
                        innermsg = msg['RO_ACCESS_REPORT']['TagReportData'][0]
                        if 'EPC-96' in innermsg:
                            epc = innermsg['EPC-96']['EPC']
                        elif 'EPCData' in innermsg:
                            epc = innermsg['EPCData']['EPC']
                        else:
                            epc = ''
                            self.out(
                                "WARNING: No EPC tag found in this message: " + msg)
                        antenna = innermsg['Antenna']['Antenna']
                        # convert from hex byte
                        peak_rssi = int(innermsg['RSSI']['RSSI'], 16)
                        # convert from hex bytes
                        first_seen_timestamp = int(
                            innermsg['Timestamp']['Timestamp'], 16)

                        self.count = self.count + 1

                        # if this is the "first" firstseentimestamp, note that so the other times will be relative to that
                        if self.start_timestamp == 0:
                            self.start_timestamp = first_seen_timestamp

                        self.latest_timestamp = first_seen_timestamp

                        self.insert_tag(epc, antenna, peak_rssi,
                                        first_seen_timestamp, self.start_timestamp)
                    except IndexError:
                        self.out(
                            "Ignoring message that contained no TagReportData")

    def insert_tag(self, epc, antenna, peak_rssi, first_seen_timestamp, start_timestamp):
        if peak_rssi >= 128:  # convert to signed
            peak_rssi = peak_rssi - 256

        self.out("Adding tag %s with RSSI %s and timestamp %s and ID %s on antenna %s" % (
            str(self.count), str(peak_rssi), str(first_seen_timestamp), str(epc), str(antenna)))

        input_dict = dict()
        input_dict['data'] = dict()
        input_dict['data']['db_password'] = self.db_password
        input_dict['data']['rssi'] = peak_rssi
        input_dict['data']['relative_time'] = first_seen_timestamp - \
            start_timestamp
        input_dict['data']['interrogator_time'] = first_seen_timestamp
        input_dict['data']['epc96'] = epc
        input_dict['data']['antenna'] = antenna

        self.tag_dicts_queue.put(input_dict)  # read by the consumer


# Requires:
# easy_install httplib2 (not pip)
