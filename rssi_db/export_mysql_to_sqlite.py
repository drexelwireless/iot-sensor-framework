from database import Database
from database_sqlite import SqliteDatabase
from database_mysql import MysqlDatabase
from mycrypto import MyCrypto
import sys
import getopt
import csv
import json
import os
import time

# OPTIONS


def usage(flask_host, db_path, key_path_prefix, password, mysqldb_path, db_user, db_password):
    print '%s [<options>]' % sys.argv[0]
    print 'where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-b <path> - path to the sqlite database: default %s\n' \
        '\t-k <path> - path to tke ssl key: default %s\n' \
        '\t-m <host> - Use mysql host <host> (also add -s xxx and -w xxx)\n' \
        '\t-p <password> - database password: default %s\n' \
        '\t-m <mysql host> - path to mysql database hostname: default %s\n' \
        '\t-s <mysql user> - username for mysql database: default %s\n' \
        '\t-w <mysql password> - password for the mysql username: default %s\n' % (
            flask_host, db_path, key_path_prefix, password, mysqldb_path, db_user, db_password)
    sys.exit(1)


def getopts():
    # Defaults
    flask_host = '0.0.0.0'
    sqlitedb_path = 'database.db'
    mysqldb_path = 'localhost'
    key_path_prefix = 'key'
    password = ''
    db_user = 'rssi'
    db_password = ''  # db_password is the mysql user password, as opposed to the flask webservice crypto password

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hm:p:f:b:k:s:w:')
    for opt in optlist:
        if opt[0] == '-h':
            usage(flask_host, sqlitedb_path, key_path_prefix,
                  password, mysqldb_path, db_user, db_password)
        if opt[0] == '-p':
            password = opt[1]
        if opt[0] == '-f':
            flask_host = opt[1]
        if opt[0] == '-b':
            sqlitedb_path = opt[1]
        if opt[0] == '-k':
            key_path_prefix = opt[1]
        if opt[0] == '-m':
            mysqldb_path = opt[1]
        if opt[0] == '-s':
            db_user = opt[1]
        if opt[0] == '-w':
            db_password = opt[1]

    return flask_host, mysqldb_path, sqlitedb_path, key_path_prefix, password, db_user, db_password


def getdict(dic, key, default):
    if key in dic:
        return dic[key]
    else:
        return default

# MAIN


def main():
    # Get options
    flask_host, mysqldb_path, sqlitedb_path, key_path_prefix, password, db_user, db_password = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    mysqldb = MysqlDatabase(
        crypto=crypto, db_path=mysqldb_path, db_password=db_password, db_user=db_user)

    # this is sorted by interrogator_timestamp
    data = mysqldb.fetch_all(password)

    myjson = data  # assumed to be a json array

    rows = 0
    # keep track of how many database runs you find (each time the relative time reverts to 0)
    db_runs = 0
    sqlitedb = None  # database connection will be created as needed; each time the relative timestamp reverts to 0

    for row in myjson:
        #print row
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
        inventoryparameterspecid = getdict(
            row, 'inventoryparameterspecid', '-1')
        lastseentimestamp = getdict(row, 'lastseentimestamp', '-1')

        if relative_time == 0 or rows == 0 or sqlitedb is None:
            db_runs = db_runs + 1
            #print 'Creating database', sqlitedb_path + str(db_runs)
            if not (sqlitedb is None):
                sqlitedb.close_db_connection()
            sqlitedb = SqliteDatabase(
                crypto=crypto, db_path=sqlitedb_path + str(db_runs))

        rows = rows + 1

        #print 'Adding row', rssi, relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, 'with password', db_password
        sqlitedb.insert_row(relative_time, interrogator_time, rssi, epc96, doppler, phase, antenna, rospecid,
                            channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_password)

    time.sleep(10)

    mysqldb.close_db_connection()
    if not (sqlitedb is None):
        sqlitedb.close_db_connection()

    time.sleep(10)
    os._exit(0)


if __name__ == "__main__":
    main()

# References:
#   http://kailaspatil.blogspot.com/2013/07/python-script-to-convert-json-file-into.html
