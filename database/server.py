import sys
import getopt
from webserver import ws_start
from database import Database
from database_sqlite import SqliteDatabase
from database_mysql import MysqlDatabase
from database_redcaprssi import REDCapRSSIDatabase
from database_mongo import MongoDatabase
from database_variot import VarIOTDatabase
from mycrypto import MyCrypto
import os
import threading
import time
import requests
import signal

# OPTIONS

def usage(flask_port, flask_host, do_debug, db_path, flush, key_path_prefix, dispatchsleep, memory):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-p <port> - port on which the server should run: default %d\n' \
        '\t-d - Enable debugging: default %s\n' \
        '\t-m - Enable mysql instead of sqlite (also add -s xxx and -w xxx for user and password to the database)\n' \
        '\t-o - Enable mongodb instead of sqlite\n' \
        '\t-r - Enable redcap instead of sqlite (also add -t xxx for the API token)' \
        '\t-v - Enable VarIOT instead of sqlite (also add -t xxx for the API token, -b for the hostname of the API endpoint, -c xxx for the device ID)' \
        '\t-b <path> - path or hostname to the database or API endpoint: default %s\n' \
        '\t-l - flush the database on run: default %s\n' \
        '\t-e <time in seconds> - length of time to sleep the dispatcher in between transmissions of data to the database, to allow new messages to queue up from the client for efficiency: default %s\n' \
        '\t-k <path> - path to the ssl key: default %s\n' \
        '\t-y - Enable in-memory database if supported: default %s\n' % (
            flask_host, flask_port, do_debug, db_path, flush, dispatchsleep, key_path_prefix, memory))
    sys.exit(1)


def getopts():
    # Defaults
    flask_port = 5000
    flask_host = '0.0.0.0'
    do_debug = False
    db_path = 'database.db'
    key_path_prefix = 'key'
    mysql = False
    redcap = False
    tinymongo = False
    variot = False
    db_user = 'dbuser'
    db_password = 'abc123'
    flush = False
    dispatchsleep = 0
    token = ''
    device = '0000000000'
    memory = False

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hp:f:db:k:mos:w:e:lrt:vc:y')
    for opt in optlist:
        if opt[0] == '-h':
            usage(flask_port, flask_host, do_debug, db_path,
                  flush, key_path_prefix, dispatchsleep, memory)
        if opt[0] == '-p':
            flask_port = int(opt[1])
        if opt[0] == '-f':
            flask_host = opt[1]
        if opt[0] == '-d':
            do_debug = True
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
        if opt[0] == '-l':
            flush = True
        if opt[0] == '-e':
            dispatchsleep = float(opt[1])
        if opt[0] == '-r':
            redcap = True
        if opt[0] == '-t':
            token = opt[1]
        if opt[0] == '-c':
            device = opt[1]
        if opt[0] == '-v':
            variot = True
        if opt[0] == '-y':
            memory = True

    if do_debug:
        print('Parameters: [flask host = %s, flask port = %d, debug = %s, database = %s, key = %s, mysql = %d, mongo = %d, db_user = %s, db_password = %s, flush = %s, dispatchsleep = %s, redcap = %s, variot = %s, token = %s, device = %s, memory = %s]' % (
            flask_host, flask_port, do_debug, db_path, key_path_prefix, mysql, tinymongo, db_user, db_password, flush, dispatchsleep, redcap, variot, token, device, memory))

    return flask_port, flask_host, do_debug, db_path, key_path_prefix, mysql, tinymongo, db_user, db_password, flush, dispatchsleep, redcap, variot, token, device, memory

# Function to watch CTRL+C keyboard input


def prog_quit(database, QUITFILE='quit'):
    print("Create file " + QUITFILE + " to quit.")
    while 1:
        if os.path.isfile(QUITFILE):
            print(QUITFILE + " has been found")
            database.close_db_connection()
                
            print("Press CTRL-C to finish quit") # do this instead of os._exit per below
            sys.exit() # don't do os._exit(0) since some db drivers use atexit to flush from cache

        time.sleep(1)

def start_wserver(crypto, database, flask_host, flask_port, do_debug):
    ws_start(crypto, database, flask_host=flask_host,
             flask_port=flask_port, do_debug=do_debug)


# MAIN
if __name__ == '__main__':
    # Get options
    flask_port, flask_host, do_debug, db_path, key_path_prefix, mysql, tinymongo, db_user, db_password, flush, dispatchsleep, redcap, variot, token, device, memory = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    if redcap == True:
        database = REDCapRSSIDatabase(
            crypto=crypto, db_path=db_path, token=token, dispatchsleep=dispatchsleep)
    elif mysql == True:
        database = MysqlDatabase(crypto=crypto, db_path=db_path, db_password=db_password,
                                 db_user=db_user, flush=flush, dispatchsleep=dispatchsleep)
    elif tinymongo == True:
        database = MongoDatabase(crypto=crypto, db_path=db_path, flush=flush, dispatchsleep=dispatchsleep, memory=memory)
    elif variot == True:
        database = VarIOTDatabase(crypto=crypto, db_path=db_path, dispatchsleep=dispatchsleep, token=token, device=device)
    else:
        database = SqliteDatabase(
            crypto=crypto, db_path=db_path, flush=flush, dispatchsleep=dispatchsleep, memory=memory)

    # enable graceful shutdown
    t2 = threading.Thread(target=prog_quit, args=(database,))
    t2.start()

    # Start up the web server
    start_wserver(crypto, database, flask_host, flask_port, do_debug)

# Requires
# SET VS90COMNTOOLS=%VS120COMNTOOLS%, on Windows
# easy_install flask, not pip
# easy_install pycrypto
# pip install pyOpenSSL, not easy install
# pip install numpy
