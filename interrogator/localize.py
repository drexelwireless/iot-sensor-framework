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
import filterpy
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise


class input_cell:
    def __init__( self, _time, _rssi, _phase, _antenna_num, _antenna_port ):
        self.time = _time
        self.phase = _phase
        self.antenna_num = _antenna_num
        self.antenna_port = _antenna_port
        self.rssi = _rssi

class output_cell:
    def __init__( self, _location1, _location2, _filtered ):
        self.location1 = _location1
        self.location2 = _location2
        self.filtered = _filtered

    #getters
    def getLocation1(self):
        return self.location1
    def getLocation2(self):
        return self.location2
    def getFilteredLocation(self):
        return self.filtered





class Localize():

    def __init__(self):
        #initialize data storage
        self.tag_count = 0

        self.quad_freq = [0,0,0,0] #for use in Noah's algorithm, assumes 1 port, 4 antennas

        self.array = []

        self.KF = KalmanFilter(dim_x = 2, dim_z = 2) #Kalman Filter

        #define dictionaries to store values
        #key: epc
        #value: list of input/output cells
        self.input_readings = {}
        self.output_locations = {}


    #Noah location
    def getLocation1( self, epc ):
        #define the mapping from quadrant to position using unit vectors:
        pos = {
               0:[math.sqrt(2)/2, math.sqrt(2)/2],
               1:[-math.sqrt(2)/2,math.sqrt(2)/2],
               2:[-math.sqrt(2)/2,-math.sqrt(2)/2],
               3:[math.sqrt(2)/2,-math.sqrt(2)/2]
               }
        
        #Copy the paramters so that we don't mess them up
        this_quad_freq = self.quad_freq
        total_reads = self.tag_count

        #Remove multipath here
        #start by getting the quadrant with the most reads
        #if we have no reads, just return a dummy location
        for i in range(len(this_quad_freq)):
            if this_quad_freq[i]==max( this_quad_freq ):
                strongest_quad = i
        
        #get the opposite quadrant to the strongest and remove reads                    
        reflected_quad = (strongest_quad+(2)) % (2)
        total_reads-= this_quad_freq[ reflected_quad ]
        this_quad_freq[ reflected_quad ] = 0
        
        #normalize quadrant frequency
        this_quad_freq = [ i/10 for i in this_quad_freq ]

        #Calculate the weighted location
        x_est = 0
        y_est = 0

        for i in range(len(this_quad_freq)):
            x_est += this_quad_freq[i]*pos[i][0]
            y_est += this_quad_freq[i]*pos[i][1]

        rv = [ x_est, y_est ]
        #return dict of locations per epc ????
        return rv


    #Kevin and Ian location
    def getLocation2(self, epc):
        xyCoor = [] 
        # Check out extended and unscented Kalman filter
        # this will go into a queue where each element is an array of all the vectors for one tag reading 
        for reading in self.input_readings[epc]: # for each antenna reading of the epc
            tempCoor = [0, 0]
            
            rssi = reading.rssi
            phase = reading.phase
            port = reading.antenna_port
            antennastate = reading.antenna_num

            tempCoor[0] = abs( rssi ) * np.cos(
                phase + (np.pi / 2 * port) + (np.pi / 4 * antennastate) )  # X coordinate
            tempCoor[1] = abs( rssi ) * np.sin(
                phase + (np.pi / 2 * port) + (np.pi / 4 * antennastate) )  # Y coordinate
            xyCoor.append( tempCoor )
        
        # if queue.full():
        #     queue.get()
        #     queue.put(xyCoor)
        # else:
        #     queue.put(xyCoor)
        return xyCoor #dict of locations per epc
    
    def update(self, epc96, first_seen_timestamp, rssi, phase, antenna_num, antenna_port):
        #store the data and update persistent parameters
        data = input_cell( first_seen_timestamp, rssi, phase, antenna_num, antenna_port)
        if not epc96 in self.input_readings:
            self.input_readings[epc96]=[] #TODO: Change this to a queue
        self.input_readings[epc96].append(data)
        
        self.tag_count+=1
        self.quad_freq[antenna_num]+=1
        
        #TODO:clear out the tags
        if self.tag_count%100==0:
            None
        
        #update locations and put into output data structure
        if self.tag_count > 1:
            location1 = self.getLocation1(epc96)
            location2 = self.getLocation2(epc96)
        else:
            location1 = [-1,-1]
            location2 =  [-1,-1]
        
        #TODO: get filtered location here
        filtered = [-1,-1]
        rv = output_cell( location1, location2, filtered ) #TODO: add filtered location
        return rv

    #TODO
    def KalmanFilter(self, kevinandianloc,noahloc):

        

        dt = 0.5 #seconds between each reading

        

        #initial guess for XY Location

        

        if len(self.input_readings) == 1:

            xMin, yMin = -10, 10 #Can be changed depending on the dimension of the area

            xMax, yMax = -10,10 #Can be changed depending on the dimension of the area

            initialX, initialY = random.randint(xMin, xMax), random.randint(yMin, yMax)

            self.KF.x = np.array([initialX,initialY]) #Initial Location Guess

            self.KF.P = np.diag([250,250])

            self.KF.Q = Q_discrete_white_noise(2, dt=0.5, var=1)

            self.KF.F = np.array([[1,0],[0,1]])

            self.KF.H = np.array([[1,0], [0,1]])

            

        

        error_KevinandIanLoc = 500 #Noise measurement/Standard deviation of Kevin and Ian's algo Placeholder right now

        error_NoahLoc = 500 #Noise measurement/Standard deviation of Noah's Algo Placeholder right now

        

        self.KF.R = error_KevinandIanLoc

        self.KF.predict()

        self.KF.update(kevinandianloc)

        self.KF.R = error_NoahLoc

        self.KF.update(noahloc)

        

        return self.KF.x




'''
-------------------NOTES-------------------

-- Outline of the data structures --

input_readings{
    epc_1 -> [ cell, cell, cell ... ]
    epc_2 -> [ cell, ... ]
    epc_3 -> [ ]
    ...
    epc_n -> [ cell, cell, cell, cell ... ]
}
where each 'cell' is an object called input_cell defined as such:

input_cell( _time, _rssi, _phase, _antenna_num, _antenna_port )


-- So how to use the structures? --

- When you get a reading:
    * create a new cell and input the data you have
        EX: newcell = input_cell( newtime, newrssi, newantenna_num, newantenna_port)
    * input this cell into the dictionary
        Ex: input_readings[ current_epc ].append( newcell ) 
'''

