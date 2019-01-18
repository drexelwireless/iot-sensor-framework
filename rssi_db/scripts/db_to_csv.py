from database import Database
from database_sqlite import SqliteDatabase
from database_mysql import MysqlDatabase
from mycrypto import MyCrypto
import sys
import getopt
import csv
import json
import os
import math
import numpy as np

############################################## UTIL HELPERS
cspeed = 2.99792458e8

# http://www.ptsmobile.com/impinj/impinj-speedway-user-guide.pdf
def freqbychannel(ch):
    if ch < 1 or ch > 50:
        return -1
    else:
        return 1e6 * (902.75 + 0.5 * (ch-1)) # 902-928 MHz, 50 channels of 500 kHz each
							
def doppler_by_channel(doppler, ch):
    return doppler * freqbychannel(ch)

def phase_to_rads(phase):
    return phase * 2.0 * math.pi / 4096
    
def augment(data, timescale=1e6):
    rows = []
    
    for batch in data:
        if isinstance(batch, dict):
            rows.append(batch)
        elif isinstance(batch, list):
            for row in batch:
                rows.append(row)
     
    rssis = dict()
    prevrow = None
    prevreads = dict()           
    for row in rows:
        # doppler in Hz
        raw_doppler = int(row['doppler'])
        if raw_doppler > 32767:
            raw_doppler = raw_doppler - 65536
        else:
            raw_doppler = raw_doppler
        raw_doppler = raw_doppler * 1.0 / 16
        row['doppler_hz'] = raw_doppler
        
        # velocity from doppler shift
        velocity_by_doppler = float(row['doppler_hz']) * 3e8 * 1.0 / freqbychannel(int(row['channelindex']))
        row['velocity_by_doppler'] = velocity_by_doppler
        
        # doppler times channel
        doppler_channel = doppler_by_channel(float(row['doppler_hz']), int(row['channelindex']))
        row['doppler_channel'] = doppler_channel
        
        # phase in radians
        phase_rads = phase_to_rads(float(row['phase']))
        row['phase_rads'] = phase_rads
        row['phase_cos_rads'] = math.cos(phase_rads)
            
        # velocity from phase difference, assuming the channel, antenna, and epc96 are the same from the previous row; can also use to compute doppler frequency from phase
        if not (prevrow is None) and prevrow['channelindex'] == row['channelindex'] and prevrow['antenna'] == row['antenna'] and prevrow['epc96'] == row['epc96']:
            if not ((4 * (1.0 / timescale) * (float(row['relative_timestamp']) - float(prevrow['relative_timestamp'])) * math.pi) == 0):
                deltaphase = (float(row['phase_rads']) - float(prevrow['phase_rads']))
                if deltaphase >= 2 * math.pi:
                    deltaphase = deltaphase - 2 * math.pi
                if deltaphase < -1 * math.pi:
                    deltaphase = deltaphase + 2 * math.pi
                velocity_by_phase = (3e8 * 1.0 / freqbychannel(int(row['channelindex']))) * deltaphase * 1.0 / (4 * (1.0 / timescale) * (float(row['relative_timestamp']) - float(prevrow['relative_timestamp'])) * math.pi)
                doppler_by_phase = velocity_by_phase * freqbychannel(int(row['channelindex'])) * 1.0 / 3e8
            else:
                velocity_by_phase = np.nan
                doppler_by_phase = np.nan
        elif str(row['channelindex'] + '|' + row['antenna'] + '|' + row['epc96']) in prevreads:
            if not ((4 * (1/timescale) * (float(row['relative_timestamp']) - float(prevreads[row['channelindex'] + '|' + row['antenna'] + '|' +  row['epc96']]['relative_timestamp'])) * math.pi) == 0):
                deltaphase = (float(row['phase_rads']) - float(prevreads[row['channelindex'] + '|' + row['antenna'] + '|' + row['epc96']]['phase_rads']))
                if deltaphase >= 2 * math.pi:
                    deltaphase = deltaphase - 2 * math.pi
                if deltaphase < -1 * math.pi:
                    deltaphase = deltaphase + 2 * math.pi
                velocity_by_phase = (cspeed * 1.0 / freqbychannel(int(row['channelindex']))) * deltaphase * 1.0 / (4 * (1/timescale) * (float(row['relative_timestamp']) - float(prevreads[row['channelindex'] + '|' + row['antenna'] + '|' + row['epc96']]['relative_timestamp'])) * math.pi)
                doppler_by_phase = velocity_by_phase * freqbychannel(int(row['channelindex'])) * 1.0 / 3e8
        else:
            velocity_by_phase = np.nan
            doppler_by_phase = np.nan
        row['doppler_by_phase'] = doppler_by_phase
        row['velocity_by_phase'] = velocity_by_phase
        
        # rssi normalized by channel - first separate the RSSI values by channel
        if not (str(row['channelindex']) + '|' + (row['antenna']) + '|' + (row['epc96'])) in rssis:
            rssis[(str(row['channelindex']) + '|' + (row['antenna']) + '|' + (row['epc96']))] = []
        rssis[(str(row['channelindex']) + '|' + (row['antenna']) + '|' + (row['epc96']))].append(float(row['rssi']))
        
        # Solve for moving_parts == gtag**2 * R (the return loss) / r**4 (the radius)
        prxLinear = 10**(float(row['rssi']) * 0.1) * 1000 # convert to Watts from dbm
        ptx = 1 # 1W = 30 dbm power from transmitter
        gr = 9 #reader gain (constant) - gain is 4 pi Aperature / lambda**2, so this really assumes a constant aperature; the lambda**2 component cancels out with gtag on the other side, since the frequency used is the same
        wavelength = (cspeed * 1.0 / freqbychannel(int(row['channelindex']))) # lambda
        #prx_moving_parts = ((1.0/prxLinear) * (4 * math.pi)**4) * 1.0 / (ptx * gr**2 * wavelength**4)
        prx_moving_parts = (ptx * gr**2) * 1.0 / (prxLinear * (wavelength**4)) # using aperature instead of gain for gt and gr terms, with the aperature formula integrated into prx_moving_parts
        row['prx_moving_parts'] = 10 * np.log10(prx_moving_parts * 1.0 / 1000)
        
        xi = 0.00961892564782412 # was 0.009405417 for gain only and not aperature
        prxval = float(row['prx_moving_parts']) + (xi * (50-int(row['channelindex'])))
        row['prx_moving_parts_deoscillated'] = prxval
        
        prevrow = row
        prevreads[str(row['channelindex'] + '|' + row['antenna'] + '|' + row['epc96'])] = row
        
    for row in rows:
        rssi_from_mean = float(row['rssi']) - np.mean(rssis[(str(row['channelindex']) + '|' + (row['antenna']) + '|' + (row['epc96']))])
        rssi_from_min = float(row['rssi']) - min(rssis[(str(row['channelindex']) + '|' + (row['antenna']) + '|' + (row['epc96']))])
        row['rssi_from_mean'] = rssi_from_mean
        row['rssi_from_min'] = rssi_from_min
        
    return rows
    
############################################## OPTIONS
def usage(flask_host, db_path, key_path_prefix, password):   
    print '%s [<options>]' % sys.argv[0]
    print 'where <options> are:\n' \
            '\t-h - show this help message\n' \
            '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
            '\t-b <path> - path to the database: default %s\n' \
            '\t-k <path> - path to tke ssl key: default %s\n' \
            '\t-m - Enable mysql instead of sqlite (also add -s xxx and -w xxx)\n' \
            '\t-p <password> - database password: default %s\n' % (flask_host, db_path, key_path_prefix, password)
    sys.exit(1)
    
def getopts():
    # Defaults
    flask_host = '0.0.0.0'
    db_path = 'database.db'
    key_path_prefix = 'key'
    password = ''
    mysql = False
    db_user = 'rssi'
    db_password = ''
    
    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hmp:f:b:k:s:w:')
    for opt in optlist:
        if opt[0] == '-h':
            usage(flask_host, db_path, key_path_prefix, password)
        if opt[0] == '-p':
            password = opt[1]
        if opt[0] == '-f':
            flask_host = opt[1]
        if opt[0] == '-b':
            db_path = opt[1]
        if opt[0] == '-k':
            key_path_prefix = opt[1]
        if opt[0] == '-m':
            mysql = True
        if opt[0] == '-s':
            db_user = opt[1]
        if opt[0] == '-w':
            db_password = opt[1]
                
    return flask_host, db_path, key_path_prefix, password, mysql, db_user, db_password
    
############################################## MAIN
    
def main():
    # Get options
    flask_host, db_path, key_path_prefix, password, mysql, db_user, db_password = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    if mysql == True:
        database = MysqlDatabase(crypto=crypto, db_path=db_path, db_password=db_password, db_user=db_user)
    else:
        database = SqliteDatabase(crypto=crypto, db_path=db_path)
    
    data = database.fetch_all(password)

    #print data

    myjson = data # assumed to be a json array
    
    keys = dict()

    #print myjson
    
    myjson = augment(myjson)

    if isinstance(myjson[0], dict):
        for k in myjson[0].keys():
            keys[k] = 1
    elif isinstance(myjson[0], list):
        for k in myjson[0][0].keys():
            keys[k] = 1        
        
    #print 'keys', keys
            
    csvfile = open('out.csv', 'wb')
    mycsv = csv.DictWriter(csvfile, fieldnames=keys.keys(), quoting=csv.QUOTE_MINIMAL)

    mycsv.writeheader()
    
    for batch in myjson:
        #print 'got:', batch
        if isinstance(batch, dict):
            #print 'dict:', batch
            mycsv.writerow(batch)  
        elif isinstance(batch, list):
            for row in batch:
                #print 'list:', row
                mycsv.writerow(row)
        else:
            print 'Error on data (not inserting):', batch  

    csvfile.close()
    database.close_db_connection()
    os._exit(0)
    
if __name__ == "__main__":
    main()        
    
# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
