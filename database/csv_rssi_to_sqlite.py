import sys
import getopt
import csv
import os
import base64
from mycrypto import MyCrypto
from database import Database
from database_sqlite import SqliteDatabase
import time
import json

# OPTIONS


def usage(flask_host, db_path, key_path_prefix, password, csvpath):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-b <path> - path to the database: default %s\n' \
        '\t-k <path> - path to tke ssl key: default %s\n' \
        '\t-c <path> - path to tke csv file: default %s\n' \
        '\t-p <password> - database password: default %s\n' % (
            flask_host, db_path, key_path_prefix, csvpath, password))
    sys.exit(1)


def getopts():
    # Defaults
    flask_host = '0.0.0.0'
    db_path = 'database.db'
    key_path_prefix = 'key'
    password = ''
    mysql = False
    csvpath = 'database.csv'

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hp:f:b:k:c:')
    for opt in optlist:
        if opt[0] == '-h':
            usage(flask_host, db_path, key_path_prefix, password, csvpath)
        if opt[0] == '-p':
            password = opt[1]
        if opt[0] == '-f':
            flask_host = opt[1]
        if opt[0] == '-b':
            db_path = opt[1]
        if opt[0] == '-k':
            key_path_prefix = opt[1]
        if opt[0] == '-c':
            csvpath = opt[1]

    return flask_host, db_path, key_path_prefix, password, csvpath

# MAIN


def db_decrypt(s, counter, password, crypto):
    # counter = int(counter) % 10^16 # counter must be at most 16 digits
    counter = int(str(counter)[-16:])  # counter must be at most 16 digits

    aes = crypto.get_db_aes(password, counter)
    b64dec = base64.b64decode(s)
    dec = aes.decrypt(b64dec)
    unpaddec = crypto.unpad(dec)
    return unpaddec


def getfield(row, field, default=''):
    if type(field) is list:
        for f in field:
            if f in row:
                return row[f]
        return default
    else:
        if field in row:
            return row[field]
        else:
            return default


def main():
    # Get options
    flask_host, db_path, key_path_prefix, password, csvpath = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    database = SqliteDatabase(crypto=crypto, db_path=db_path)

    csvfile = open(csvpath, 'rt')
    conn = database.open_db_connection()

    # read all records from csv
    reader = csv.DictReader(csvfile)

    for row in reader:
        interrogatortime = getfield(
            row, ['interrogatortime', 'interrogator_timestamp'])
        relativetime = getfield(row, ['relativetime', 'relative_timestamp'])
        rssi = getfield(row, 'rssi')
        epc96 = getfield(row, 'epc96')
        doppler = getfield(row, 'doppler')
        phase = getfield(row, 'phase')
        antenna = getfield(row, 'antenna')
        channelindex = getfield(row, 'channelindex')
        rospecid = getfield(row, 'rospecid')
        tagseencount = getfield(row, 'tagseencount')
        accessspecid = getfield(row, 'accessspecid')
        inventoryparameterspecid = getfield(row, 'inventoryparameterspecid')
        lastseentimestamp = getfield(row, 'lastseentimestamp')

        # decrypt each according to the password
        rssi = db_decrypt(rssi, interrogatortime, password, crypto)
        epc96 = db_decrypt(doppler, interrogatortime, password, crypto)
        doppler = db_decrypt(doppler, interrogatortime, password, crypto)
        phase = db_decrypt(phase, interrogatortime, password, crypto)

        #print '*****'
        #print row
        #print '*****'
        #print relativetime, interrogatortime, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp

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
        
        # insert each into sqlite database
        database.insert_row(relativetime, interrogatortime, freeform, db_pw=password)

    database.close_db_connection()
    time.sleep(10)  # allow the database to write
    csvfile.close()
    os._exit(0)


if __name__ == "__main__":
    main()

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
