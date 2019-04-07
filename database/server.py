import sys
import getopt
from webserver import ws_start
from database import Database
from database_sqlite import SqliteDatabase
from database_mysql import MysqlDatabase
from database_redcap import REDCapDatabase
from mycrypto import MyCrypto
import os
import threading
import time

# OPTIONS

def usage(flask_port, flask_host, do_debug, db_path, flush, key_path_prefix, dispatchsleep):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-f <0.0.0.0> - IP address (127.0.0.1) on which the server should run: default %s\n' \
        '\t-p <port> - port on which the server should run: default %d\n' \
        '\t-d - Enable debugging: default %s\n' \
        '\t-m - Enable mysql instead of sqlite (also add -s xxx and -w xxx for user and password to the database)\n' \
        '\t-r - Enable redcap instead of sqlite (also add -t xxx for the API token)' \
        '\t-b <path> - path or hostname to the database or API endpoint: default %s\n' \
        '\t-l - flush the database on run: default %s\n' \
        '\t-e <time in seconds> - length of time to sleep the dispatcher in between transmissions of data to the database, to allow new messages to queue up from the client for efficiency: default %s\n' \
        '\t-k <path> - path to tke ssl key: default %s\n' % (
            flask_host, flask_port, do_debug, db_path, flush, dispatchsleep, key_path_prefix))
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
    db_user = 'rssi'
    db_password = 'abc123'
    flush = False
    dispatchsleep = 0
    redcap_token = ''

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hp:f:db:k:ms:w:e:lrt:')
    for opt in optlist:
        if opt[0] == '-h':
            usage(flask_port, flask_host, do_debug, db_path,
                  flush, key_path_prefix, dispatchsleep)
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
            redcap_token = opt[1]

    if do_debug:
        print('Parameters: [flask host = %s, flask port = %d, debug = %s, database = %s, key = %s, mysql = %d, db_user = %s, db_password = %s, flush = %s, dispatchsleep = %s, redcap = %s, redcap_token = %s]' % (
            flask_host, flask_port, do_debug, db_path, key_path_prefix, mysql, db_user, db_password, flush, dispatchsleep, redcap, redcap_token))

    return flask_port, flask_host, do_debug, db_path, key_path_prefix, mysql, db_user, db_password, flush, dispatchsleep, redcap, redcap_token

# Function to watch CTRL+C keyboard input


def prog_quit(QUITFILE='quit'):
    print("Create file " + QUITFILE + " to quit.")
    while 1:
        try:
            if os.path.isfile(QUITFILE):
                print(QUITFILE + " has been found")
                os._exit(0)
            time.sleep(1)
        except:
            os._exit(0)

def start_wserver(crypto, database, flask_host, flask_port, do_debug):
    ws_start(crypto, database, flask_host=flask_host,
             flask_port=flask_port, do_debug=do_debug)


# MAIN
if __name__ == '__main__':
    # Get options
    flask_port, flask_host, do_debug, db_path, key_path_prefix, mysql, db_user, db_password, flush, dispatchsleep, redcap, redcap_token = getopts()

    # Start up the database module and the database AES / web server SSL module
    crypto = MyCrypto(hostname=flask_host, key_path_prefix=key_path_prefix)
    if redcap == True:
        database = REDCapDatabase(
            crypto=crypto, db_path=db_path, token=redcap_token, dispatchsleep=dispatchsleep)
    elif mysql == True:
        database = MysqlDatabase(crypto=crypto, db_path=db_path, db_password=db_password,
                                 db_user=db_user, flush=flush, dispatchsleep=dispatchsleep)
    else:
        database = SqliteDatabase(
            crypto=crypto, db_path=db_path, flush=flush, dispatchsleep=dispatchsleep)

    # enable graceful shutdown
    t2 = threading.Thread(target=prog_quit, args=())
    t2.start()

    # Start up the web server
    start_wserver(crypto, database, flask_host, flask_port, do_debug)

# Requires
# SET VS90COMNTOOLS=%VS120COMNTOOLS%, on Windows
# easy_install flask, not pip
# easy_install pycrypto
# pip install pyOpenSSL, not easy install
# pip install numpy
