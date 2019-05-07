import base64
import os
import numpy
import sys
import traceback
from database import Database
import queue
import threading
import os
from time import sleep
import pymysql
import json

class MysqlDatabase(Database):
    def __init__(self, crypto, db_path='localhost', db_name='iotdatabase', db_password='abc123', db_user='dbuser', flush=False, dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path, flush=flush)
        self.dispatchsleep = dispatchsleep
        self.db_name = db_name
        self.db_password = db_password
        self.db_user = db_user
        self.db = None
        self.dispatcher_db = None
        self.log_db = None
        self.insertion_queue = queue.Queue()
        self.dispatcher_thread = threading.Thread(
            target=self.dispatcher, args=())
        self.dispatcher_thread.start()
        self.log_queue = queue.Queue()
        self.log_thread = threading.Thread(target=self.log_dispatcher, args=())
        self.log_thread.start()

    def __del__(self):
        self.close_db_connection()

    def get_queue_data(self, q):
        # q.get(block=True)
        while 1:
            try:
                input_dict = q.get_nowait() 
                return input_dict
            except queue.Empty:
                sleep(0.1)
                continue

    def close_db_connection(self, thread='main'):
        sleep(5+2*self.dispatchsleep)  # wait for dispatchers to finish

        if thread == 'main':
            if not self.db is None:
                if self.db.open == 1:
                    self.db.commit()
                    self.db.close()
                self.db = None

        # can't manipulate these sub connections within the main thread
        if thread == 'log':
            if not self.log_db is None:
                if self.log_db.open == 1:
                    self.log_db.commit()
                    self.log_db.close()
                self.log_db = None

        # can't manipulate these sub connections within the main thread
        if thread == 'dispatcher':
            if not self.dispatcher_db is None:
                if self.dispatcher_db.open == 1:
                    self.dispatcher_db.commit()
                    self.dispatcher_db.close()
                self.dispatcher_db = None

    def open_db_connection(self):
        # idiom to be used for each database connection to use a new database connection each time
        # if not (self.db is None):
        #    self.db.commit()
        #    self.db.close()
        #    self.db = None

        if (self.db is None):
            self.db = pymysql.connect(self.db_path, self.db_user, self.db_password, self.db_name, charset='utf8', use_unicode=True)

            self.init_database(self.db)

        if (self.dispatcher_db is None):
            self.dispatcher_db = pymysql.connect(self.db_path, self.db_user, self.db_password, self.db_name, charset='utf8', use_unicode=True)
            self.init_database(self.dispatcher_db)

        if (self.log_db is None):
            self.log_db = pymysql.connect(self.db_path, self.db_user, self.db_password, self.db_name, charset='utf8', use_unicode=True)
            self.init_database(self.log_db)

        return self.db

    def query(self, cursor, q, params=None, thread='main', executemany=False):
        done = False
        while not done:
            try:
                if not (params is None):
                    if executemany == False:
                        result = cursor.execute(q, params)
                    else:
                        result = cursor.executemany(q, params)
                else:
                    result = cursor.execute(q)

                if thread == 'main':
                    self.db.commit()
                elif thread == 'log':
                    self.log_db.commit()
                elif thread == 'dispatcher':
                    self.dispatcher_db.commit()
                done = True
            except:
                e = sys.exc_info()[0]
                print('*** Database error on query ' + \
                    str(q) + ' from thread ' + thread + ', retrying: %s' % e)
                traceback.print_exception(*(sys.exc_info()))
                if thread == 'main':
                    self.db.close()
                    self.db = None
                    self.db = self.open_db_connection()
                    cursor = self.db.cursor()
                elif thread == 'log':
                    self.log_db.close()
                    self.log_db = None
                    self.open_db_connection()
                    cursor = self.log_db.cursor()
                elif thread == 'dispatcher':
                    self.dispatcher_db.close()
                    self.dispatcher_db = None
                    self.open_db_connection()
                    cursor = self.dispatcher_db.cursor()
        return result

    def init_database(self, conn):
        if self.flush == True:
            self.flush_database(conn)

        # http://stackoverflow.com/questions/6202726/writing-utf-8-string-to-mysql-with-python
        c = conn.cursor()
        # or utf8 or any other charset you want to handle
        c.execute("SET NAMES utf8mb4;")
        c.execute("SET CHARACTER SET utf8mb4;")  # same as above
        c.execute("SET character_set_connection=utf8mb4;")  # same as above

        c.execute('''CREATE TABLE IF NOT EXISTS IOTD(id INTEGER PRIMARY KEY AUTO_INCREMENT, absolute_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, relative_timestamp BIGINT, interrogator_timestamp BIGINT, freeform VARBINARY(64535))''')  # absolute_timestamp was DATETIME for more recent mysql
        c.execute('''CREATE TABLE IF NOT EXISTS AUDIT(id INTEGER PRIMARY KEY AUTO_INCREMENT, absolute_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, log TEXT)''')  # absolute_timestamp was DATETIME for more recent mysql

        conn.commit()

    def flush_database(self, conn):
        c = conn.cursor()
        c.execute('''DROP TABLE IF EXISTS IOTD''')
        conn.commit()
        self.db_log('DROP IOTD')

    def flush_audit(self, conn):
        c = conn.cursor()
        c.execute('''DROP TABLE AUDIT''')
        conn.commit()

    def db_log(self, text):
        row = (text, )
        self.log_queue.put(row)

    # get max data time in the db
    def get_max_rel_time(self):
        conn = self.open_db_connection()
        c = conn.cursor()

        data = []

        result = self.query(c, "SELECT MAX(relative_timestamp) FROM IOTD")
        for row in c:
            d = dict()
            d['max_relative_timestamp'] = row[0]
            data.append(d)

        c.close()

        return data

    def log_dispatcher(self):
        self.open_db_connection()
        conn = self.log_db

        while 1:
            print('Getting data from log dispatcher...')  
            row = self.get_queue_data(self.log_queue)
            print('Data received from log dispatcher...')
            c = conn.cursor()
            done = False
            while not done:
                try:
                    c.execute('INSERT INTO AUDIT (log) VALUES (%s)', row)
                    # conn.commit() # don't bother committing here, let the main database thread commit
                    done = True
                except:
                    e = sys.exc_info()[0]
                    print('*** Database error on audit insertion, retrying: %s' % e)
                    traceback.print_exception(*(sys.exc_info()))
                    self.log_db.close()
                    self.log_db = None
                    self.open_db_connection()
                    c = self.log_db.cursor()
            c.close()

            sleep(1)

        self.close_db_connection(thread='log')

    def db_encrypt(self, s, counter):
        # counter = int(counter) % 10^16 # counter must be at most 16 digits
        counter = int(str(counter)[-self.crypto.MAX_COUNTER_DIGITS:])  # counter must be at most 16 digits, take rightmost 16 characters

        if type(s) is int:
            val = str(s)
        elif type(s) is float:
            val = str(s)
        else:
            val = s

        aes = self.crypto.get_db_aes(self.db_password, counter)
        padded = self.crypto.pad(val)
        enc = aes.encrypt(padded)
        b64enc = base64.b64encode(enc)
        return b64enc

    def db_decrypt(self, s, counter):
        # counter = int(counter) % 10^16 # counter must be at most 16 digits
        counter = int(str(counter)[-self.crypto.MAX_COUNTER_DIGITS:])  # counter must be at most 16 digits, take rightmost 16 characters

        aes = self.crypto.get_db_aes(self.db_password, counter)
        b64dec = base64.b64decode(s)
        dec = aes.decrypt(b64dec)
        unpaddec = self.crypto.unpad(dec)
        unpaddec = unpaddec.decode()
        return unpaddec

    # dispatch insertions from the queue so that the webserver can continue receiving requests
    # log each request to the Audit
    def dispatcher(self):
        self.open_db_connection()
        conn = self.dispatcher_db

        while 1:
            queuelist = []

            print('Getting data from dispatcher...')
            input_dict = self.get_queue_data(self.insertion_queue)
            print('Data received from dispatcher...')
            queuelist.append(input_dict)

            #print input_dict

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_dict = self.insertion_queue.get_nowait()
                    queuelist.append(input_dict)
                except queue.Empty:
                    break

            c = conn.cursor()

            rowlist = []
            for input_dict in queuelist:
                # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
                relativetime = input_dict['relativetime']
                interrogatortime = input_dict['interrogatortime']
                freeform = input_dict['freeform']
                freeformjson = json.dumps(freeform)

                row = (relativetime, interrogatortime, self.db_encrypt(freeformjson, interrogatortime))

                rowlist.append(row)

            result = self.query(c, 'INSERT INTO IOTD (relative_timestamp, interrogator_timestamp, freeform) VALUES (%s,%s,%s)', rowlist, thread='dispatcher', executemany=True)
            c.close()
            conn.commit()

            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

        self.close_db_connection(thread='dispatcher')

    # just insert into a queue for the dispatcher to insert in the background
    def insert_row(self, relativetime, interrogatortime, freeform, db_pw=''):
        input_dict = dict()  # read by the consumer dispatcher
        input_dict['relativetime'] = relativetime
        input_dict['interrogatortime'] = interrogatortime
        input_dict['freeform'] = freeform

        self.insertion_queue.put(input_dict)

    # log this request to the Audit
    def fetch_all(self, db_pw=''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, freeform FROM IOTD ORDER BY interrogator_timestamp ASC")
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['freeform'] = self.db_decrypt(row[4], row[3])
            data.append(d)

        c.close()

        return data

    # log this request to the Audit
    def fetch_last_window(self, windowsize, db_pw=''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (windowsize, )
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, freeform FROM IOTD ORDER BY interrogator_timestamp ASC LIMIT %s", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['freeform'] = self.db_decrypt(row[4], row[3])
            data.append(d)

        c.close()

        return data

    # log this request to the Audit
    def fetch_since(self, since, db_pw=''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (since,)
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, freeform FROM IOTD WHERE relative_timestamp >= %s ORDER BY interrogator_timestamp ASC", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['freeform'] = self.db_decrypt(row[4], row[3])
            data.append(d)

        c.close()

        return data

    # log this request to the Audit
    def fetch_between_window(self, start, end, db_pw=''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (start, end)
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, freeform FROM IOTD WHERE relative_timestamp >= %s AND relative_timestamp <= %s ORDER BY interrogator_timestamp ASC", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['freeform'] = self.db_decrypt(row[4], row[3])
            data.append(d)

        c.close()

        return data

    # log this request to the Audit
    def fetch_last_n_sec(self, n, db_pw=''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, freeform FROM IOTD WHERE absolute_timestamp >= NOW() - INTERVAL %s SECOND ORDER BY interrogator_timestamp ASC", (n,))
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['freeform'] = self.db_decrypt(row[4], row[3])
            data.append(d)

        c.close()

        return data

    def get_audit(self):
        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        self.db_log('FETCH AUDIT')
        result = self.query(c, "SELECT id, absolute_timestamp, log FROM AUDIT")
        for row in c:
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['log'] = row[2]
            data.append(d)

        c.close()

        return data

# References:
#   http://mysql-python.sourceforge.net/MySQLdb.html#mysqldb
