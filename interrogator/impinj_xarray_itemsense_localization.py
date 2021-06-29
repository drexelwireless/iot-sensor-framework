from interrogator import *
import requests
import base64
import threading
import json
import sys
from httplib2 import Http
import os
import queue
from time import sleep
import collections
import dateutil.parser

class ImpinjXArray(Interrogator):
    #CalcLocations Function
    def calcLocations(freeform):

        numAntennas = 52

        # Large dictionarry of array locations
        # Key is EPC string (name) for a tag, one entry per tag
        # Values are tuples of quadrant, location
        antennas = {
            "1": (1, [-0.25, 0.25]),
            "12": (1, [-0.44, 0.44]),
            "20": (1, [-0.62, 0.62]),
            "28": (1, [-0.80, 0.80]),
            "36": (1, [-0.97, 0.97]),
            "44": (1, [-1.15, 1.15]),
            "52": (1, [-1.33, 1.33]),
            "5": (2, [0, 0.625]),
            "13": (2, [0, 0.875]),
            "21": (2, [0, 1.125]),
            "29": (2, [0, 1.375]),
            "37": (2, [0, 1.625]),
            "45": (2, [0, 1.875]),
            "2": (3, [0.25, 0.25]),
            "6": (3, [0.44, 0.44]),
            "14": (3, [0.62, 0.62]),
            "22": (3, [0.80, 0.80]),
            "30": (3, [0.97, 0.97]),
            "38": (3, [1.15, 1.15]),
            "46": (3, [1.33, 1.33]),
            "7": (4, [0.625, 0]),
            "15": (4, [0.875, 0]),
            "23": (4, [1.125, 0]),
            "31": (4, [1.375, 0]),
            "39": (4, [1.625, 0]),
            "47": (4, [1.875, 0]),
            "3": (5, [0.25, -0.25]),
            "8": (5, [0.44, -0.44]),
            "16": (5, [0.62, -0.62]),
            "24": (5, [0.80, -0.80]),
            "32": (5, [0.97, -0.97]),
            "40": (5, [1.15, -1.15]),
            "48": (5, [1.33, -1.33]),
            "9": (6, [0, -0.625]),
            "17": (6, [0, -0.875]),
            "25": (6, [0, -1.125]),
            "33": (6, [0, -1.375]),
            "41": (6, [0, -1.625]),
            "49": (6, [0, -1.875]),
            "4": (7, [-0.25, -0.25]),
            "10": (7, [-0.44, -0.44]),
            "18": (7, [-0.62, -0.62]),
            "26": (7, [-0.80, -0.80]),
            "34": (7, [-0.97, -0.97]),
            "42": (7, [-1.15, -1.15]),
            "50": (7, [-1.33, -1.33]),
            "11": (8, [-0.625, 0]),
            "19": (8, [-0.875, 0]),
            "27": (8, [-1.125, 0]),
            "35": (8, [-1.375, 0]),
            "43": (8, [-1.625, 0]),
            "51": (8, [-1.875, 0])
        }

        # Method to get the location using all of the methods in calcLocation
        # @param EPCReads: an arraylist of tagPhysInfos (one list of tag reports for an EPC)
        # @return array of doubles containing the estimated x and y location unit vector
        def getLoc(EPCReads):

            removeMultipathOutliers(EPCReads)
            antennaWeights = computeAntennaWeights(EPCReads)
            loct = computeLocTranspose(antennaWeights)
            highRssiAntennas = computeHighRssiAntennaBeams(EPCReads)
            locr = averageRssiLoc(highRssiAntennas)

            return averageWithRssi(locr, loct)

        # Method to compute antenna weights for an EPC
        # @param EPCReads: an arraylist of tag report data for one EPC (one element from the tagMap)
        # @return A hashmap of antenna numbers with their corresponding weight
        def computeAntennaWeights(EPCReads):

            seenAntennas = {}

            # Create a dictionary of antennas and the frequency of each antenna
            for epcRead in EPCReads:
                antennaNumber = epcRead.getAntennaPortNumber()  # NOTE: getAntennaPortNumber() is a placeholder for when the coode is merged
                if antennaNumber in seenAntennas:
                    count = seenAntennas.get(antennaNumber)
                    seenAntennas[antennaNumber] = count + 1
                else:
                    seenAntennas[antennaNumber] = 1

            totalReads = len(EPCReads)
            antennaWeights = {}

            # Create a dictionary of weights for each of the antennas for this EPC where an antenna's weight is:
            # w_i = n_i / sum 1 to M n_i
            for antennaName, entry in seenAntennas.items():
                w_i = entry / totalReads
                antennaWeights[antennaName] = w_i

            return antennaWeights

        # Method to compute [xt,yt] using the list of antenna weights and the antenna x_p and y_p
        # @param antennaWeights: a list hashmap of antenna weights (output of computeAntennaWeights)
        # @return a vector [xt,yt] containing the location of the tag
        def computeLocTranspose(antennaWeights):
            xt, yt = 0, 0
            # Iterate over the antenna weights to multiply the weight by the antenna's x_p, y_p
            for name, entry in antennaWeights.items():
                # Get the x_p,y_p vals for this antenna
                xi = antennas[name][1][0]  # anetnnas[name][1] == array of x and y coordinates
                yi = antennas[name][1][1]
                # Add to weighted x and y
                xt += entry * xi
                yt += entry * yi

            return [xt, yt]

        # Method to get the beam with the highest peak RSSI value
        # @param tagReads: tag report data for one EPC as an arraylist (one element from tag map)
        # @return The antenna number(s) with the highest peak RSSI as an arrayList of shorts
        def computeHighRssiAntennaBeams(tagReads):
            maxRssi = 0

            for tagRead in tagReads:
                if tagReads[i].getPeakRssi() > maxRssi:  # NOTE: getPeakRssi() is a placeholder
                    maxRssi = tagRead.getPeakRssi()  # NOTE: getPeakRssi() is a placeholder
            # Make an arraylist of the reports with maxRssi
            maxRssiAntennas = []
            for tagRead in tagReads:
                if tagRead.getPeakRssi() == maxRssi:  # NOTE: getPeakRssi() is a placeholder
                    maxRssiAntennas.append(
                        tagRead.getAntennaPortNumber())  # NOTE: getAntennaPortNumber() is a placeholder

            return maxRssiAntennas

        # Methods to calculate the location of the antenna with the max RSSI beam by averaging them
        # @param maxRssiAntennas: arraylist of shorts that contains the antenna numbers of the max rssi antennas
        # @return array of doubles giving the averaged location
        def averageRssiLoc(maxRssiAntennas):
            xr, yr = 0, 0

            if maxRssiAntennas == null or len(maxRssiAntennas) == 0:
                return [xr, yr]

            for maxRssiAntenna in maxRssiAntennas:
                currAntenna = int(maxRssiAntenna)
            xr += antennas[currAntenna][1][0]  # antennas[currAntenna] == array of x and y coordinates
            yr += antennas[currAntenna][1][1]

            xr /= len(maxRssiAntennas)
            yr /= len(maxRssiAntennas)

            return [xr, yr]

        # Method to average the location of the max rssi antennas and the weighted antennas
        # @param locr: Array of doubles giving the x and y location of the averaged rssi antennas
        # @param loct: Array of doubles giving the x and y location of the weighted antennas
        # @return Array of doubles giving the final x and y location
        def averageWithRssi(locr, loct):
            xout = (locr[0] + loct[0]) / 2
            yout = (locr[1] + loct[1]) / 2

            return [xout, yout]

        # Method to remove outliers due to reflected antenna beams in place
        # @param tagReads: arraylist of tag reports for one EPC
        def removeMultipathOutliers(tagReads):
            quadrantNumber, antennaNumber = 0, 0
            quadrantFrequencies = {}

            for tagRead in tagReads:
                antennaNumber = tagRead.getAntennaPortNumber()  # NOTE: getAntennaPortNumber() is a placeholder
                quadrantNumber = antennas[antennaNumber][0]

                if quadrantNumber in quadrantFrequencies:
                    count = quadrantFrequencies[quadrantNumber]
                    quadrantFrequencies[quadrantNumber] = count + 1
                else:
                    quadrantFrequencies[quadrantNumber] = 1

            maxQuadCount = 0
            storedQuad = 0
            lowerQuad = 0
            upperQuad = 0
            storedLowerQuad = 0
            storedUpperQuad = 0

            ##add two more variables?
            for key, entry in quadrantFrequencies.items():
                thisQuad = key
                lowerQuad = thisQuad - 1

                if lowerQuad == 0:
                    lowerQuad = 8
                upperQuad = thisQuad + 1
                if upperQuad == 9:
                    upperQuad = 1

                thisQuadFreq = entry
                lowerQuadFreq = quadrantFrequencies[lowerQuad]
                if lowerQuadFreq == null:
                    lowerQuadFreq = 0
                upperQuadFreq = quadrantFrequencies[upperQuad]
                if upperQuadFreq == null:
                    upperQuadFreq = 0

                print("-----TEST-----")
                print("This Quad Frequency: %d\nLower Quad Frequency: %d\nUpper Quad Frequency: %d\n" % (
                thisQuadFreq, lowerQuadFreq, upperQuadFreq))

                adjQuadCount = thisQuadFreq + lowerQuadFreq + upperQuadFreq
                print("total quad count: " + adjQuadCount)

                if adjQuadCount > maxQuadCount:
                    maxQuadCount = adjQuadCount
                    storedQuad = thisQuad
                    storedLowerQuad = lowerQuad
                    storedUpperQuad = upperQuad

                print("max Quadrant: " + storedQuad)

                # Get reflected quadrants
                if storedUpperQuad > 4:
                    upperReflectedQuad = storedUpperQuad - 4
                else:
                    upperReflectedQuad = storedUpperQuad + 4
                ###################################################
                if storedLowerQuad > 4:
                    lowerReflectedQuad = storedLowerQuad - 4
                else:
                    lowerReflectedQuad = storedLowerQuad + 4
                ###################################################
                if storedQuad > 4:
                    reflectedQuad = storedQuad - 4
                else:
                    reflectedQuad = storedQuad + 4

                print("reflected: %d\nreflected lower: %d\n reflected upper: %d" % (
                reflectedQuad, lowerReflectedQuad, upperReflectedQuad))
                print("-----END TEST-----")

                ##Remove tag reports that are in reflected quadrants
                for i in range(len(tagReads)):
                    antennaNumber = tagReads[i].getAntennaPortNumber();  # NOTE: getAntennaPortNumber() is a placeholder
                    quadrantNumber = antennas[antennaNumber][0]  # returns the first item in the tuple - the quadrant

                    if (quadrantNumber == upperReflectedQuad) or (quadrantNumber == lowerReflectedQuad) or (
                            quadrantNumber == reflectedQuad):
                        tagReads.pop(i)
                        i = i - 1

    def __init__(self, _ip_address, _db_host, _db_password, _cert_path, _debug, _apiusername, _apipassword, _dispatchsleep=0, _recipe='IMPINJ_Deep_Scan_Inventory', _facility='MESS'):
        Interrogator.__init__(self, _db_host, _db_password,
                              _cert_path, _debug, _dispatchsleep)
        self.exiting = False
        self.ip_address = _ip_address
        self.baseurl = "http://%s/itemsense" % self.ip_address
        
        self.apiusername = _apiusername
        self.apipassword = _apipassword

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)
            
        self.start_timestamp = -1
        
        self.recipe = _recipe
        self.facility = _facility

        self.out('Initializing XArray Interrogator client')

    def out(self, x):
        if self.debug:
            sys.stdout.write(str(x) + '\n')

    def start_server(self):
        self.out('Starting Impinj XArray Interrogator client')
        
        self.tag_dicts_queue = queue.Queue()
        self.handler_thread = threading.Thread(
            target=self.handler_thread, args=())
        self.handler_thread.start()

        # Create Clients and set them to connect
        authstr = "%s:%s" % (self.apiusername, self.apipassword)
        basicenc = base64.b64encode(authstr.encode())
        self.basicauth = 'Basic ' + basicenc.decode()
        facility = self.facility #'MESS'
        recipe = self.recipe #'IMPINJ_Fast_Location'

        # Get a Token
        url = self.baseurl + '/authentication/v1/token/' + self.apiusername
        Headers = {}
        Headers['Authorization'] = self.basicauth
        response = requests.put(url, headers=Headers)
        self.token = response.json()['token']
        self.tokenauth = 'Token {"token":\"' + self.token + '\"}'

        # Start a Job
        url = self.baseurl + '/control/v1/jobs/start'
        Data = {}
        Data['startDelay'] = 'PT1S'  # 1 second job start delay
        Data['facility'] = facility
        Data['recipeName'] = recipe
        Headers = {}
        Headers['Authorization'] = self.tokenauth
        Headers['Content-Type'] = 'application/json'
        response = requests.post(url, data=json.dumps(Data), headers=Headers)
        
        # Job start will fail if there is already a running job; cycle through our jobs and end those RUNNING jobs with a facility and recipe name that match ours; note that if there is another RUNNING job from another facility or recipe, this will continue to fail, but it seems better not to stop someone else's job
        if not ('id' in response.json()): # if id is not in response, need to stop existing running jobs
            # Stop Running Jobs, then Re-Start the Job
            url = self.baseurl + '/control/v1/jobs/show'
            Headers = {}
            Headers['Authorization'] = self.tokenauth
            Headers['Content-Type'] = 'application/json'
            response = requests.get(url, headers=Headers)
            
            for j in response.json():
                if j['job']['facility'].lower() == facility.lower() and j['job']['recipeName'].lower() == recipe.lower():
                    if j['status'].lower() == 'running':
                        url = self.baseurl + '/control/v1/jobs/stop/' + j['id']
                        Headers = {}
                        Headers['Content-Type'] = 'application/json'
                        Headers['Authorization'] = self.tokenauth
                        response = requests.post(url, headers=Headers)                    
            # Re-Start the Job
            url = self.baseurl + '/control/v1/jobs/start'
            Data = {}
            Data['startDelay'] = 'PT1S'  # 1 second job start delay
            Data['facility'] = facility
            Data['recipeName'] = recipe
            Headers = {}
            Headers['Authorization'] = self.tokenauth
            Headers['Content-Type'] = 'application/json'
            response = requests.post(url, data=json.dumps(Data), headers=Headers)            
        jobId = response.json()['id'] # This will fail if the job did not start successfully, could handle more gracefully...
        self.out("Job ID: %s" % jobId)

        self.jobId = jobId
        self.count = 0

        while not self.exiting:            
            done = False
            while (not done):
                sleep(5)
                url = self.baseurl + '/data/v1/items/show/'
                urlh = self.baseurl + '/data/v1/items/show/history'
                Data = {}
                Data['facility'] = facility
                Data['jobId'] = jobId
                Headers = {}
                Headers['Content-Type'] = 'application/json'
                Headers['Authorization'] = self.tokenauth
                response = requests.get(
                    url, data=json.dumps(Data), headers=Headers)
                # responseh = requests.get(
                #     urlh, data=json.dumps(Data), headers=Headers)
                responsejson = response.json()
		
		
                print("Responsejson:")
                print(responsejson)
                #XYLoc = calcLocations(responsejson['freeform'])#NOTE: This is the localization function call; returns [x,y]

                if not "nextPageMarker" in responsejson:
                    done = True
                elif responsejson['nextPageMarker'] is None:
                    done = True
                else:
                    Data['pageMarker'] = responsejson['nextPageMarker']
                
                self.tag_dicts_queue.put(responsejson)
                
            self.count = self.count + 1

    def handler_thread(self):
        while not self.exiting:
            responsearray = []
            
            responsejson = self.tag_dicts_queue.get(block=True)
            responsearray.append(responsejson)
            
            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    responsejson = self.tag_dicts_queue.get_nowait()
                    responsearray.append(responsejson)
                except queue.Empty:
                    break
                    
            self.insert_tag(responsearray)            

    def start(self):
        self.out('XArray: start')
        self.start_server()

    def close_server(self):
        self.exiting = True
        # Stop the Job
        url = self.baseurl + '/control/v1/jobs/stop/' + self.jobId
        Headers = {}
        Headers['Content-Type'] = 'application/json'
        Headers['Authorization'] = self.tokenauth
        response = requests.post(url, headers=Headers)
        self.out(response)

        # Revoke the Token
        url = self.baseurl + '/authentication/v1/revokeToken'
        Headers = {}
        Headers['Content-Type'] = 'application/json'
        Headers['Authorization'] = self.basicauth
        Data = {}
        Data['token'] = self.token
        response = requests.put(url, headers=Headers, data=json.dumps(Data))
        print(response)

    def __del__(self):
        self.close_server()

    def insert_tag(self, tagarray):
        input_dicts = []
        
        if self.start_timestamp == -1:
          min_timestamp = -1
          for entry in tagarray:
            items = entry['items']

            for freeform in items:
              # convert the timestamp from a string to numeric
              timestamp = freeform['lastModifiedTime']
              timestampdt = dateutil.parser.parse(timestamp)
              timestampmicro = timestampdt.timestamp() * 1000
              
              if int(timestampmicro) < min_timestamp or min_timestamp == -1:
                min_timestamp = timestampmicro
                
          self.start_timestamp = int(min_timestamp)
        
        for entry in tagarray:
          items = entry['items']

          for freeform in items:            
            timestamp = freeform['lastModifiedTime']
            epc = freeform['epc']
            xPos = freeform["xLocation"]
            yPos = freeform["yLocation"]
            zPos = freeform["zLocation"]
            
            # convert the timestamp from a string to numeric
            timestampdt = dateutil.parser.parse(timestamp)
            timestampmicro = timestampdt.timestamp() * 1000
            
            self.out("Adding tag / collection %s with timestamp %s and epc %s and xPosition %s and yPosition %s and zPosition %s" % (
                str(self.count), str(timestampmicro), str(epc), str(xPos), str(yPos), str(zPos)))

            input_dict = dict()
            input_dict['data'] = dict()
            input_dict['data']['db_password'] = self.db_password
            input_dict['data']['freeform'] = freeform
            input_dict['data']['relative_time'] = int(timestampmicro) - self.start_timestamp
            input_dict['data']['interrogator_time'] = timestampmicro            
            
            self.out("Input dict is: %s" % input_dict)
            
            input_dicts.append(input_dict)
            
        url = self.db_host + '/api/rssi'

        resp, content = self.http_obj.request(uri=url, method='PUT', headers={
            'Content-Type': 'application/json; charset=UTF-8'}, body=json.dumps(input_dicts))
            
        if self.dispatchsleep > 0:
            # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
            sleep(self.dispatchsleep)

# Requires:
# easy_install httplib2 (not pip)
