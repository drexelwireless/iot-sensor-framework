from database import Database
from database_sqlite import SqliteDatabase
from database_mysql import MysqlDatabase
from database_mongo import MongoDatabase
from mycrypto import MyCrypto
import sys
import getopt
import csv
import json
import os
import math
import numpy as np
import time

# OPTIONS


def usage(flask_host, db_path, key_path_prefix, password):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-b <path> - path to the database: default %s\n' \
        '\t-k <path> - path to tke ssl key: default %s\n' \
        '\t-m - Enable mysql instead of sqlite (also add -s xxx and -w xxx)\n' \
        '\t-o - Enable tinymongo instead of sqlite\n' \
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
    tinymongo = False
    db_user = 'rssi'
    db_password = ''

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hmop:f:b:k:s:w:')
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
        if opt[0] == '-o':
            tinymongo = True
        if opt[0] == '-s':
            db_user = opt[1]
        if opt[0] == '-w':
            db_password = opt[1]

    return flask_host, db_path, key_path_prefix, password, mysql, tinymongo, db_user, db_password

# MAIN


def main():
    # Get options
    flask_host, db_path, key_path_prefix, password, mysql, tinymongo, db_user, db_password = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    if mysql == True:
        database = MysqlDatabase(
            crypto=crypto, db_path=db_path, db_password=db_password, db_user=db_user)
    elif tinymongo == True:
        database = MongoDatabase(crypto=crypto, db_path=db_path)
    else:
        database = SqliteDatabase(crypto=crypto, db_path=db_path)

    data = database.fetch_all(password)

    #print(data)

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

    csvfile = open('out.csv', 'wt')
    mycsv = csv.DictWriter(csvfile, fieldnames=list(keys.keys()),
                           quoting=csv.QUOTE_MINIMAL)

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
            print('Error on data (not inserting):', batch)

    time.sleep(5)
    
    csvfile.close()
    database.close_db_connection()
    os._exit(0)


if __name__ == "__main__":
    main()

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
