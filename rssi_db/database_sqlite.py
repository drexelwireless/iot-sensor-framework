import sqlite3
import base64
import os
import numpy
from database import Database
import threading
import Queue
from time import sleep

class SqliteDatabase(Database):
    def __init__(self, crypto, db_path='database.db', flush=False, dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path, flush=flush)
        self.dispatchsleep = dispatchsleep
        self.insertion_queue = Queue.Queue()
        self.dispatcher_thread = threading.Thread(target = self.dispatcher, args=())
        self.dispatcher_thread.start()

    def dispatcher(self):
        conn = self.open_db_connection()
        c = conn.cursor()
        
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
                except Queue.Empty:
                    break
                                           
            for db_pw in queuelist:
                self.db_password = db_pw
            
                # combine many rows together into a single insert, each with its own password
                rowlist = []
                for row in queuelist[db_pw]:
                    rowlist.append(row)
                    
                    #print row
                    
                # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
                c.executemany('INSERT INTO RSSI (relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp) VALUES (?,?,encrypt(?,?),encrypt(?,?),encrypt(?,?),encrypt(?,?),?,?,?,?,?,?,?)', rowlist)
            conn.commit()
            
            if self.dispatchsleep > 0:
                sleep(self.dispatchsleep) # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
            
        conn.close()        

    def close_db_connection(self, thread='main'):
        sleep(5+2*self.dispatchsleep) # wait for dispatchers to finish

    def __del__(self):
        self.close_db_connection()

    def open_db_connection(self):
        # don't store the connection because each thread requires its own
        conn = sqlite3.connect(self.db_path)
        os.chmod(self.db_path, 0600)
        
        conn.create_function('encrypt', 2, self.db_encrypt)
        conn.create_function('decrypt', 2, self.db_decrypt)    

        self.init_database(conn)
        
        return conn # don't forget to conn.close()

    def db_encrypt(self, s, counter):
        #counter = int(counter) % 10^16 # counter must be at most 16 digits
        counter = int(str(counter)[-16:]) # counter must be at most 16 digits

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
        #counter = int(counter) % 10^16 # counter must be at most 16 digits
        counter = int(str(counter)[-16:]) # counter must be at most 16 digits
        
        aes = self.crypto.get_db_aes(self.db_password, counter)
        b64dec = base64.b64decode(s)
        dec = aes.decrypt(b64dec)
        unpaddec = self.crypto.unpad(dec)
        return unpaddec
            
    def init_database(self, conn):        
        if self.flush == True:
            self.flush_database(conn)
            
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS RSSI(id INTEGER PRIMARY KEY, absolute_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, relative_timestamp BIGINT, interrogator_timestamp BIGINT, rssi TEXT, epc96 TEXT, doppler TEXT, phase TEXT, antenna TEXT, rospecid TEXT, channelindex TEXT, tagseencount TEXT, accessspecid TEXT, inventoryparameterspecid TEXT, lastseentimestamp TEXT)''')
        conn.commit()
        
    def flush_database(self, conn):
        c = conn.cursor()
        c.execute('''DROP TABLE IF EXISTS RSSI''')
        conn.commit()
        
    # get max data time in the db
    def get_max_rel_time(self):
        conn = self.open_db_connection()
        c = conn.cursor() 
        
        data = []   
        
        for row in c.execute("SELECT MAX(relative_timestamp) FROM RSSI"):            
            d = dict()
            d['max_relative_timestamp'] = row[0]
            data.append(d)
        conn.commit()
        conn.close()
        
        return data  
        
    def insert_row(self, relativetime, interrogatortime, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_pw = ''):        
        # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
        row = (relativetime, interrogatortime, rssi, interrogatortime, epc96, interrogatortime, doppler, interrogatortime, phase, interrogatortime, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp) 
        
        self.insertion_queue.put((row, db_pw)) # to be read by dispatcher
            
    def fetch_all(self, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(rssi, interrogator_timestamp), decrypt(epc96, interrogator_timestamp), decrypt(doppler, interrogator_timestamp), decrypt(phase, interrogator_timestamp), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI ORDER BY interrogator_timestamp ASC"):
            
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = row[4]
            d['epc96'] = row[5]
            d['doppler'] = row[6]
            d['phase'] = row[7]
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        conn.commit()
        conn.close()
        
        return data
        
    def fetch_last_window(self, windowsize, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (windowsize, )
        for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(rssi, interrogator_timestamp), decrypt(epc96, interrogator_timestamp), decrypt(doppler, interrogator_timestamp), decrypt(phase, interrogator_timestamp), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI ORDER BY interrogator_timestamp ASC LIMIT ?", input):
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = row[4]
            d['epc96'] = row[5]
            d['doppler'] = row[6]
            d['phase'] = row[7]
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        conn.commit()            
        conn.close()
        
        return data        

    def fetch_since(self, since, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (since,)
        for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(rssi, interrogator_timestamp), decrypt(epc96, interrogator_timestamp), decrypt(doppler, interrogator_timestamp), decrypt(phase, interrogator_timestamp), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE relative_timestamp >= ? ORDER BY interrogator_timestamp ASC", input):
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = row[4]
            d['epc96'] = row[5]
            d['doppler'] = row[6]
            d['phase'] = row[7]
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        conn.commit()
        conn.close()
        
        return data    
            
    def fetch_between_window(self, start, end, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (start, end)
        for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(rssi, interrogator_timestamp), decrypt(epc96, interrogator_timestamp), decrypt(doppler, interrogator_timestamp), decrypt(phase, interrogator_timestamp), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE relative_timestamp >= ? AND relative_timestamp <= ? ORDER BY interrogator_timestamp ASC", input):
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = row[4]
            d['epc96'] = row[5]
            d['doppler'] = row[6]
            d['phase'] = row[7]
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        conn.commit()
        conn.close()
        
        return data    

    def fetch_last_n_sec(self, n, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        for row in c.execute("SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, decrypt(rssi, interrogator_timestamp), decrypt(epc96, interrogator_timestamp), decrypt(doppler, interrogator_timestamp), decrypt(phase, interrogator_timestamp), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE absolute_timestamp >= datetime(?, ?) ORDER BY interrogator_timestamp ASC", ('now', '-' + str(n) + ' seconds')):
            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = row[4]
            d['epc96'] = row[5]
            d['doppler'] = row[6]
            d['phase'] = row[7]
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        conn.commit()
        conn.close()
        
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
