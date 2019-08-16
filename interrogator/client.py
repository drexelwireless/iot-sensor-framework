from impinj import *
from impinj_r420 import *
from impinj_xarray_itemsense import *
import getopt
import sys
import os
import time

def usage(ip_address, db_host, db_password, cert_path, do_debug, device, antennas, dispatchsleep, tagpop):
    print('%s [<options>]' % sys.argv[0])
    print('where <options> are:\n' \
        '\t-h - show this help message\n' \
        '\t-i <127.0.0.1> - IP address of the interrogator: default %s\n' \
        '\t-o <https://localhost> - host where the database web service resides: default %s\n' \
        '\t-p <password> - password to the database web service: default %s\n' \
        '\t-c <certfile> - path to the certificate file for verifying SSL certificate or NONE to bypass: default %s\n' \
        '\t-a <antenna number> - antenna number to interrogate (can specify more than once), if supported by the interrogator: default %s\n' \
        '\t-l <time in seconds> - length of time to sleep the dispatcher in between transmissions of data to the server, to allow new messages to queue up for efficiency: default %s\n' \
        '\t-g <device> - device to use as the interrogator (impinj, r420, xarray): default %s\n' \
        '\t-t <pop> - sets tag population (4 good for 1 tag, 16 good for 2 tags): default %s\n' \
        '\t-d - Enable debugging: default %s\n' % (ip_address, db_host, db_password,
                                                   cert_path, antennas, dispatchsleep, device, tagpop, do_debug))
    sys.exit(1)


def getopts():
    # Defaults
    ip_address = "rfidreader.local"
    db_host = "https://localhost:5000"
    db_password = ""
    do_debug = False
    cert_path = "NONE"
    device = "Impinj"
    antennas = [1, 2, 3, 4]
    userantennas = []
    dispatchsleep = 0.5
    tagpop = 4

    # Check command line
    optlist, list = getopt.getopt(sys.argv[1:], 'hi:o:p:dc:g:a:n:l:t:')

    for opt in optlist:
        if opt[0] == '-h':
            usage(ip_address, db_host, db_password, cert_path, do_debug,
                  device, antennas, dispatchsleep, tagpop)
        if opt[0] == '-i':
            ip_address = opt[1]
        if opt[0] == '-o':
            db_host = opt[1]
        if opt[0] == '-p':
            db_password = opt[1]
        if opt[0] == '-d':
            do_debug = True
        if opt[0] == '-c':
            cert_path = opt[1]
        if opt[0] == '-g':
            device = opt[1]
        if opt[0] == '-a':
            userantennas.append(int(opt[1]))
        if opt[0] == '-l':
            dispatchsleep = float(opt[1])
        if opt[0] == '-t':
            tagpop = int(opt[1])

    if len(userantennas) > 0:
        antennas = userantennas

    #print ip_address, db_host, db_password, cert_path, do_debug, device, antennas, dispatchsleep

    return ip_address, db_host, db_password, cert_path, do_debug, device, antennas, dispatchsleep, tagpop


def print_stats(rfid):
    if rfid.latest_timestamp - rfid.start_timestamp > 0:
        rate = (rfid.count * 1.0) / \
            (rfid.latest_timestamp - rfid.start_timestamp)
        print('Read rate per interrogator unit time:', rate, rfid.count, 'reads over', rfid.latest_timestamp - \
            rfid.start_timestamp, 'time')

# Function to watch CTRL+C keyboard input

def prog_quit(rfid, QUITFILE='quit'):
    print("Create file " + QUITFILE + " to quit.")
    exiting = False
    while not exiting:
        try:
            if os.path.isfile(QUITFILE):
                print(QUITFILE + " has been found")
                exiting = True
                print_stats(rfid)
                rfid.close_server()
                # wait for server to terminate gracefully, including waiting for the database to shutdown cleanly which takes 5 seconds
                time.sleep(10)
            time.sleep(1)
        except:
            os._exit(0)

if __name__ == "__main__":
    ip_address, db_host, db_password, cert_path, do_debug, device, antennas, dispatchsleep, tagpop = getopts()

    if device.lower() == "impinj":
        rfid = Impinj(ip_address, db_host, db_password, cert_path,
                      do_debug, _dispatchsleep=dispatchsleep)
        t2 = threading.Thread(target=prog_quit, args=(rfid,))
        t2.start()
        rfid.start()
    elif device.lower() == "r420":
        rfid = ImpinjR420(ip_address, db_host, db_password, cert_path, do_debug,
                          _dispatchsleep=dispatchsleep, _antennas=antennas, _tagpop=tagpop)
        t2 = threading.Thread(target=prog_quit, args=(rfid,))
        t2.start()
        rfid.start()
    elif device.lower() == "xarray":
        rfid = ImpinjXArray(ip_address, db_host, db_password, cert_path,
                            do_debug, _dispatchsleep=dispatchsleep)
        t2 = threading.Thread(target=prog_quit, args=(rfid,))
        t2.start()
        rfid.start()
    else:
        os._exit(0)
