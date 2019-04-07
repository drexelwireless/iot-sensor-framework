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

# OPTIONS


def usage(flask_host, db_path, key_path_prefix, password):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-b <path> - path to the database: default %s\n' \
        '\t-k <path> - path to tke ssl key: default %s\n' \
        '\t-m - Enable mysql instead of sqlite (also add -s xxx and -w xxx)\n' \
        '\t-g <csvfile> - A CSV file containing times in seconds that gaps in data should begin, and the duration of the gap, with headers \'time\' and \'duration\'' \
        '\t-p <password> - database password: default %s\n' % (
            flask_host, db_path, key_path_prefix, password))
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
    gapfile = None

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hmp:f:b:k:s:w:g:')
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
        if opt[0] == '-g':
            gapfile = opt[1]

    return flask_host, db_path, key_path_prefix, password, mysql, db_user, db_password, gapfile

# MAIN


def getdict(dic, key, default):
    if key in dic:
        return dic[key]
    else:
        return default


def get_data(row):
    rssi = getdict(row, 'rssi', '')
    relative_time = getdict(row, 'relative_timestamp', '')
    interrogator_time = getdict(row, 'interrogator_timestamp', '')
    epc96 = getdict(row, 'epc96', '')
    doppler = getdict(row, 'doppler', '-1')
    phase = getdict(row, 'phase', '-1')
    antenna = getdict(row, 'antenna', '-1')
    rospecid = getdict(row, 'rospecid', '-1')
    channelindex = getdict(row, 'channelindex', '-1')
    tagseencount = getdict(row, 'tagseencount', '-1')
    accessspecid = getdict(row, 'accessspecid', '-1')
    inventoryparameterspecid = getdict(row, 'inventoryparameterspecid', '-1')
    lastseentimestamp = getdict(row, 'lastseentimestamp', '-1')

    return relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp


def insert_row(db, relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_password):
    db.insert_row(relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid, channelindex,
                  tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_pw=db_password)


def is_time_in_gap(relative_time, gaps, timescale=1e6):
    for gap in gaps:
        begintime = float(gap['time']) * timescale
        endtime = (float(gap['time']) + float(gap['duration'])) * timescale

        if float(relative_time) >= begintime and float(relative_time) <= endtime:
            return True

    return False


def process(row, outdb, db_pw, gaps=None, timescale=1e6):
    relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp = get_data(
        row)

    if (gaps is None) or (not (gaps is None) and is_time_in_gap(relative_time, gaps, timescale=timescale) == False):
        print('INSERTING', relative_time)
        insert_row(outdb, relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid,
                   channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_pw)
    else:
        print('ELIMINATING', relative_time)


def main():
    # Get options
    flask_host, db_path, key_path_prefix, password, mysql, db_user, db_password, gapfile = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    if mysql == True:
        database = MysqlDatabase(
            crypto=crypto, db_path=db_path, db_password=db_password, db_user=db_user)
    else:
        database = SqliteDatabase(crypto=crypto, db_path=db_path)

    outdb_path = 'out.db0'
    sqliteoutdb = SqliteDatabase(crypto=crypto, db_path=outdb_path)

    data = database.fetch_all(password)

    #print data

    myjson = data  # assumed to be a json array

    keys = dict()

    #print myjson

    if isinstance(myjson[0], dict):
        for k in list(myjson[0].keys()):
            keys[k] = 1
    elif isinstance(myjson[0], list):
        for k in list(myjson[0][0].keys()):
            keys[k] = 1

    #print 'keys', keys

    # Read in gaps, if any
    gaplist = []
    if not (gapfile is None):
        gapcsvfile = open(gapfile, 'rt')
        gapcsvreader = csv.DictReader(gapcsvfile)
        for gaprow in gapcsvreader:
            gaplist.append(gaprow)

    for batch in myjson:
        #print 'got:', batch
        if isinstance(batch, dict):
            #print 'dict:', batch
            process(batch, sqliteoutdb, password, gaps=gaplist)
        elif isinstance(batch, list):
            for row in batch:
                #print 'list:', row
                process(row, sqliteoutdb, password, gaps=gaplist)
        else:
            print('Error on data (not inserting):', batch)

    database.close_db_connection()
    sqliteoutdb.close_db_connection()
    os._exit(0)


if __name__ == "__main__":
    main()

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
