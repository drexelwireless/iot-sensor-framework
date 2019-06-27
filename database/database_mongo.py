import base64
import os
import numpy
from database import Database
import threading
import queue
from time import sleep
import json
from tinymongo import TinyMongoClient
import time

class MongoDatabase(Database):
    def __init__(self, crypto, db_path='tinymongodata', flush=False, dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path, flush=flush)
        self.open_db_connection()
        self.dispatchsleep = dispatchsleep
        self.insertion_queue = queue.Queue()
        self.dispatcher_thread = threading.Thread(
            target=self.dispatcher, args=())
        self.dispatcher_thread.start()

    def dispatcher(self):
        while 1:
            queuelist = dict()

            (row, db_pw) = self.insertion_queue.get(block=True)
            if not (db_pw in queuelist):
                queuelist[db_pw] = []
            queuelist[db_pw].append(row)

            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    (row, db_pw) = self.insertion_queue.get_nowait()
                    if not (db_pw in queuelist):
                        queuelist[db_pw] = []
                    queuelist[db_pw].append(row)
                except queue.Empty:
                    break

            for db_pw in queuelist:
                self.db_password = db_pw

                # combine many rows together into a single insert, each with its own password
                rowlist = []
                for row in queuelist[db_pw]:
                    #print(row)
                    row['freeform'] = self.db_encrypt(row['freeform'], row['interrogator_timestamp']).decode("utf-8") 
                    row['absolute_timestamp'] = time.time()
                    rowlist.append(row)

                # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
                # c.executemany('INSERT INTO IOTD (relative_timestamp, interrogator_timestamp, freeform) VALUES (?,?,encrypt(?,?))', rowlist)
                print(rowlist)
                result = self.collection.insert_many(rowlist)
            # conn.commit()


            if self.dispatchsleep > 0:
                # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
                sleep(self.dispatchsleep)

        #conn.close()

    def close_db_connection(self, thread='main'):
        while self.insertion_queue.qsize() > 0:
            sleep(5+2*self.dispatchsleep)  # wait for dispatchers to finish

    def __del__(self):
        self.close_db_connection()

    def open_db_connection(self):
        # don't store the connection because each thread requires its own
        try:
            os.mkdir(self.db_path)
        except FileExistsError:
            #print("Warning: database path already exists:", self.db_path)
            pass
        os.chmod(self.db_path, 0o700)
        self.conn = TinyMongoClient(self.db_path)

        #sqlite3.enable_callback_tracebacks(True) # for user defined function exceptions
        
        #conn.create_function('encrypt', 2, self.db_encrypt)
        #conn.create_function('decrypt', 2, self.db_decrypt)

        self.init_database(self.conn)

        return self.conn

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
        counter = int(str(counter)[-self.crypto.MAX_COUNTER_DIGITS:])  # counter must be at most 16 digits, so take the rightmost 16 characters of the string

        aes = self.crypto.get_db_aes(self.db_password, counter)
        b64dec = base64.b64decode(s)
        dec = aes.decrypt(b64dec)
        unpaddec = self.crypto.unpad(dec)
        unpaddec = unpaddec.decode()
        return unpaddec

    def init_database(self, conn):
        if self.flush == True:
            self.flush_database(conn)
        self.db = conn.mydb
        self.collection = self.db.mycoll
        #c = conn.cursor()
        #c.execute('''CREATE TABLE IF NOT EXISTS IOTD(id INTEGER PRIMARY KEY, absolute_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, relative_timestamp BIGINT, interrogator_timestamp BIGINT, freeform TEXT)''')
        #conn.commit()

    def flush_database(self, conn):
        #c = conn.cursor()
        #c.execute('''DROP TABLE IF EXISTS IOTD''')
        #conn.commit()
        self.db.delete_many(query = None)

    # get max data time in the db
    def get_max_rel_time(self):
        #conn = self.open_db_connection()
        #c = conn.cursor()

        data = []

        #for row in c.execute("SELECT MAX(relative_timestamp) FROM IOTD"):
            #d = dict()
            #d['max_relative_timestamp'] = row[0]
            #data.append(d)
        #conn.commit()
        #conn.close()
        
        result = self.collection.find(sort=[('relative_timestamp', -1)], limit=1) #'-1' sorts data in descending order. so the maximum comes first.
        
        if len(result) >= 1:
            d = dict()
            d['max_relative_timestamp'] = result[0]['relative_timestamp']
            data.append(d)

        return data

    def insert_row(self, relativetime, interrogatortime, freeform, db_pw=''):
        # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
        # counter entries (i.e., interrogatortime) go after the field being entered into the row tuple
        freeformjson = json.dumps(freeform)
        #row = (relativetime, interrogatortime, freeformjson, interrogatortime)
        row = {}
        row['relative_timestamp'] = relativetime
        row['interrogator_timestamp'] = interrogatortime
        row['freeform'] = freeformjson

        self.insertion_queue.put((row, db_pw))  # to be read by dispatcher

    def fetch_all(self, db_pw=''):
        self.db_password = db_pw

        data = []
        #conn = self.open_db_connection()
        #c = conn.cursor()
        #for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(freeform, interrogator_timestamp) FROM IOTD ORDER BY interrogator_timestamp ASC"):
        result = self.collection.find(sort=[('interrogator_timestamp', 1)])
        for row in result:
            d = dict()
            #d['id'] = row[0]
            d['absolute_timestamp'] = row['absolute_timestamp']
            d['relative_timestamp'] = row['relative_timestamp']
            d['interrogator_timestamp'] = row['interrogator_timestamp']
            d['freeform'] = self.db_decrypt(row['freeform'], row['interrogator_timestamp'])
            data.append(d)
            
        #conn.commit()
        #conn.close()

        return data

    def fetch_last_window(self, windowsize, db_pw=''):
        self.db_password = db_pw

        data = []
        #conn = self.open_db_connection()
        #c = conn.cursor()
        input = (windowsize, )
        result = self.collection.find(sort=[('interrogator_timestamp', -1)], limit=windowsize)
        #for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(freeform, interrogator_timestamp) FROM IOTD ORDER BY interrogator_timestamp DESC LIMIT ?", input):
        for row in result:
            d = dict()
            #d['id'] = row[0]
            d['absolute_timestamp'] = row['absolute_timestamp']
            d['relative_timestamp'] = row['relative_timestamp']
            d['interrogator_timestamp'] = row['interrogator_timestamp']
            d['freeform'] = self.db_decrypt(row['freeform'], row['interrogator_timestamp'])
            data.append(d)
        
        #conn.commit()
        #conn.close()

        return data

    def fetch_since(self, since, db_pw=''):
        self.db_password = db_pw

        data = []
        #conn = self.open_db_connection()
        #c = conn.cursor()
        input = (since,)
        #for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(freeform, interrogator_timestamp) FROM IOTD WHERE relative_timestamp >= ? ORDER BY interrogator_timestamp ASC", input):
        result = self.collection.find(sort=[('interrogator_timestamp', 1)], filter = {'relative_timestamp':{'$gte' : since}}) #$lte for less than/equal to
        for row in result:
            d = dict()
            #d['id'] = row[0]
            d['absolute_timestamp'] = row['absolute_timestamp']
            d['relative_timestamp'] = row['relative_timestamp']
            d['interrogator_timestamp'] = row['interrogator_timestamp']
            d['freeform'] = self.db_decrypt(row['freeform'], row['interrogator_timestamp'])
            data.append(d)
        #conn.commit()
        #conn.close()

        return data

    def fetch_between_window(self, start, end, db_pw=''):
        self.db_password = db_pw

        data = []
        #conn = self.open_db_connection()
        #c = conn.cursor()
        input = (start, end)
        #for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(freeform, interrogator_timestamp) FROM IOTD WHERE relative_timestamp >= ? AND relative_timestamp <= ? ORDER BY interrogator_timestamp ASC", input):
        result = self.collection.find(sort=[('interrogator_timestamp', 1)], filter = {'relative_timestamp':{'$gte' : start, '$lte' : end}})
        for row in result:
            d = dict()
            #d['id'] = row[0]
            d['absolute_timestamp'] = row['absolute_timestamp']
            d['relative_timestamp'] = row['relative_timestamp']
            d['interrogator_timestamp'] = row['interrogator_timestamp']
            d['freeform'] = self.db_decrypt(row['freeform'], row['interrogator_timestamp'])
            data.append(d)
        #conn.commit()
        #conn.close()

        return data

    def fetch_last_n_sec(self, n, db_pw=''):
        self.db_password = db_pw

        data = []
        #conn = self.open_db_connection()
        #c = conn.cursor()
        #for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(freeform, interrogator_timestamp) FROM IOTD WHERE absolute_timestamp >= datetime(?, ?) ORDER BY interrogator_timestamp ASC", ('now', '-' + str(n) + ' seconds')):
        result = self.collection.find(sort=[('interrogator_timestamp',-1)], limit=n)
        for row in result:
            d = dict()
            #d['id'] = row[0]
            d['absolute_timestamp'] = row['absolute_timestamp']
            d['relative_timestamp'] = row['relative_timestamp']
            d['interrogator_timestamp'] = row['interrogator_timestamp']
            d['freeform'] = self.db_decrypt(row['freeform'], row['interrogator_timestamp'])
            data.append(d)
        #conn.commit()
        #conn.close()

        return data

    # no auditing in sqlite
    def flush_audit(self, conn):
        pass

    def get_audit(self):
        return []

    def db_log(self, text):
        pass

# References:
#   http://www.pythoncentral.io/introduction-to-sqlite-in-python/
#   https://docs.python.org/2/library/sqlite3.html
#   http://stackoverflow.com/questions/14461851/how-to-have-an-automatic-timestamp-in-sqlite
#   http://pymotw.com/2/sqlite3/

#if it's freeform that i'm pulling out of the query, i will have to decrypt it
#self.db_decrypt(y[['freeform'], y['interrogator_timestamp'])

#skip absolute_timestamp
