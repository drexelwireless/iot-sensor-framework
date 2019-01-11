import MySQLdb
import base64
import os
import numpy
import sys
import traceback
from database import Database
import Queue
import threading
import os
from time import sleep

class MysqlDatabase(Database):
    def __init__(self, crypto, db_path='localhost', db_name='rssidb', db_password='abc123', db_user='rssi', flush=False, dispatchsleep=0):
        Database.__init__(self, crypto, db_path=db_path, flush=flush)
        self.dispatchsleep = dispatchsleep
        self.db_name = db_name
        self.db_password = db_password
        self.db_user = db_user
        self.db = None
        self.dispatcher_db=None
        self.log_db=None
        self.insertion_queue = Queue.Queue()
        self.dispatcher_thread = threading.Thread(target = self.dispatcher, args=())
        self.dispatcher_thread.start()
        self.log_queue = Queue.Queue()
        self.log_thread = threading.Thread(target = self.log_dispatcher, args=())
        self.log_thread.start()

    def __del__(self):
        self.close_db_connection()

    def close_db_connection(self, thread='main'):
        sleep(5+2*self.dispatchsleep) # wait for dispatchers to finish
        
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
        #if not (self.db is None):
        #    self.db.commit()
        #    self.db.close()
        #    self.db = None

        if (self.db is None):
            self.db=MySQLdb.connect(passwd=self.db_password,db=self.db_name,user=self.db_user,host=self.db_path,use_unicode=True,charset='utf8', init_command='SET NAMES UTF8')
            self.init_database(self.db)
        
        if (self.dispatcher_db is None):
            self.dispatcher_db=MySQLdb.connect(passwd=self.db_password,db=self.db_name,user=self.db_user,host=self.db_path,use_unicode=True,charset='utf8', init_command='SET NAMES UTF8')
            self.init_database(self.dispatcher_db)
            
        if (self.log_db is None):
            self.log_db=MySQLdb.connect(passwd=self.db_password,db=self.db_name,user=self.db_user,host=self.db_path,use_unicode=True,charset='utf8', init_command='SET NAMES UTF8')
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
                print '*** Database error on query ' + str(q) + ' from thread ' + thread + ', retrying: %s' % e
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
        c.execute("SET NAMES utf8mb4;") #or utf8 or any other charset you want to handle
        c.execute("SET CHARACTER SET utf8mb4;") #same as above
        c.execute("SET character_set_connection=utf8mb4;") #same as above

        c.execute('''CREATE TABLE IF NOT EXISTS RSSI(id INTEGER PRIMARY KEY AUTO_INCREMENT, absolute_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, relative_timestamp BIGINT, interrogator_timestamp BIGINT, rssi VARBINARY(255), epc96 VARBINARY(255), doppler VARBINARY(255), phase VARBINARY(255), antenna INT, rospecid INT, channelindex INT, tagseencount INT, accessspecid INT, inventoryparameterspecid INT, lastseentimestamp BIGINT)''') # absolute_timestamp was DATETIME for more recent mysql
        c.execute('''CREATE TABLE IF NOT EXISTS AUDIT(id INTEGER PRIMARY KEY AUTO_INCREMENT, absolute_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP, log TEXT)''') # absolute_timestamp was DATETIME for more recent mysql

        conn.commit()

    def flush_database(self, conn):
        c = conn.cursor()
        c.execute('''DROP TABLE IF EXISTS RSSI''')
        conn.commit()
        self.db_log('DROP RSSI')

    def flush_audit(self, conn):
        c = conn.cursor()
        c.execute('''DROP TABLE AUDIT''')
        conn.commit()

    def db_log(self, text):
        row = ( text, )
        self.log_queue.put(row)

    # get max data time in the db
    def get_max_rel_time(self):
        conn = self.open_db_connection()
        c = conn.cursor()

        data = []

        result = self.query(c, "SELECT MAX(relative_timestamp) FROM RSSI")
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
            row = self.log_queue.get(block=True)
            c = conn.cursor()
            done = False
            while not done:
                try:
                    c.execute('INSERT INTO AUDIT (log) VALUES (%s)', row)
                    # conn.commit() # don't bother committing here, let the main database thread commit
                    done = True
                except:
                    e = sys.exc_info()[0]
                    print '*** Database error on audit insertion, retrying: %s' % e
                    traceback.print_exception(*(sys.exc_info()))
                    self.log_db.close()
                    self.log_db = None
                    self.open_db_connection()
                    c = self.log_db.cursor()
            c.close()
                    
        self.close_db_connection(thread='log')    

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
        
    # dispatch insertions from the queue so that the webserver can continue receiving requests
    # log each request to the Audit
    def dispatcher(self):
        self.open_db_connection()
        conn = self.dispatcher_db
        
        while 1:
            queuelist = []
            
            input_dict = self.insertion_queue.get(block=True)
            queuelist.append(input_dict)
                    
            #print input_dict
            
            # http://stackoverflow.com/questions/156360/get-all-items-from-thread-queue
            # while we're here, try to pick up any more items that were inserted into the queue
            while 1:
                try:
                    input_dict = self.insertion_queue.get_nowait()
                    queuelist.append(input_dict)
                except Queue.Empty:
                    break
            
            c = conn.cursor()
            
            rowlist = []
            for input_dict in queuelist:
                # the additional interrogatortime entries are for the encryption function which requires a counter to synchronize stream encryption and decryption; this time should be to the microsecond (6 places after the decimal for seconds) to ensure uniqueness, but can be less precise if the interrogator resolution is lower.  relative_time is expected in microseconds, and both relativetime and interrogatortime are assumed to be whole numbers (i.e. epoch time)
                relativetime = input_dict['relativetime']
                interrogatortime = input_dict['interrogatortime']
                rssi = input_dict['rssi']
                epc96 = input_dict['epc96']
                db_pw = input_dict['db_pw']
                doppler = input_dict['doppler']
                phase = input_dict['phase']
                antenna = input_dict['antenna']
                rospecid = input_dict['rospecid']
                channelindex = input_dict['channelindex']
                tagseencount = input_dict['tagseencount']
                accessspecid = input_dict['accessspecid']
                inventoryparameterspecid = input_dict['inventoryparameterspecid']
                lastseentimestamp = input_dict['lastseentimestamp']
            
                self.db_password = db_pw

                row = (relativetime, interrogatortime, self.db_encrypt(rssi, interrogatortime), self.db_encrypt(epc96, interrogatortime), self.db_encrypt(doppler, interrogatortime), self.db_encrypt(phase, interrogatortime), antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp)
                
                rowlist.append(row)
                
            result = self.query(c, 'INSERT INTO RSSI (relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)', rowlist, thread='dispatcher', executemany=True)
            c.close()
            conn.commit()
            
            if self.dispatchsleep > 0:
                sleep(self.dispatchsleep) # if desired, sleep the dispatcher for a short time to queue up some inserts and give the producer some CPU time
            
        self.close_db_connection(thread='dispatcher')

    # just insert into a queue for the dispatcher to insert in the background
    def insert_row(self, relativetime, interrogatortime, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp, db_pw = ''):
        input_dict = dict() # read by the consumer dispatcher
        input_dict['relativetime'] = relativetime
        input_dict['interrogatortime'] = interrogatortime
        input_dict['rssi'] = rssi
        input_dict['epc96'] = epc96
        input_dict['db_pw'] = db_pw
        input_dict['doppler'] = doppler
        input_dict['phase'] = phase
        input_dict['antenna'] = antenna
        input_dict['rospecid'] = rospecid
        input_dict['channelindex'] = channelindex
        input_dict['tagseencount'] = tagseencount
        input_dict['accessspecid'] = accessspecid
        input_dict['inventoryparameterspecid'] = inventoryparameterspecid
        input_dict['lastseentimestamp'] = lastseentimestamp
        
        self.insertion_queue.put(input_dict)    

    # log this request to the Audit
    def fetch_all(self, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI ORDER BY interrogator_timestamp ASC")
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = self.db_decrypt(row[4], row[3])
            d['epc96'] = self.db_decrypt(row[5], row[3])
            d['doppler'] = self.db_decrypt(row[6], row[3])
            d['phase'] = self.db_decrypt(row[7], row[3])
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        
        c.close()

        return data

    # log this request to the Audit
    def fetch_last_window(self, windowsize, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (windowsize, )
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI ORDER BY interrogator_timestamp ASC LIMIT %s", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = self.db_decrypt(row[4], row[3])
            d['epc96'] = self.db_decrypt(row[5], row[3])
            d['doppler'] = self.db_decrypt(row[6], row[3])
            d['phase'] = self.db_decrypt(row[7], row[3])
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        
        c.close()

        return data

    # log this request to the Audit
    def fetch_since(self, since, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (since,)
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE relative_timestamp >= %s ORDER BY interrogator_timestamp ASC", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = self.db_decrypt(row[4], row[3])
            d['epc96'] = self.db_decrypt(row[5], row[3])
            d['doppler'] = self.db_decrypt(row[6], row[3])
            d['phase'] = self.db_decrypt(row[7], row[3])
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        
        c.close()

        return data
        
    # log this request to the Audit
    def fetch_between_window(self, start, end, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        input = (start, end)
        result = self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE relative_timestamp >= %s AND relative_timestamp <= %s ORDER BY interrogator_timestamp ASC", input)
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = self.db_decrypt(row[4], row[3])
            d['epc96'] = self.db_decrypt(row[5], row[3])
            d['doppler'] = self.db_decrypt(row[6], row[3])
            d['phase'] = self.db_decrypt(row[7], row[3])
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
            data.append(d)
        
        c.close()

        return data

    # log this request to the Audit
    def fetch_last_n_sec(self, n, db_pw = ''):
        self.db_password = db_pw

        data = []
        conn = self.open_db_connection()
        c = conn.cursor()
        self.query(c, "SELECT id, absolute_timestamp, relative_timestamp, interrogator_timestamp, rssi, epc96, doppler, phase, antenna, rospecid, channelindex, tagseencount, accessspecid, inventoryparameterspecid, lastseentimestamp FROM RSSI WHERE absolute_timestamp >= NOW() - INTERVAL %s SECOND ORDER BY interrogator_timestamp ASC", (n,))
        for row in c:
            self.db_log('FETCH ' + str(row[0]))

            d = dict()
            d['id'] = row[0]
            d['absolute_timestamp'] = row[1]
            d['relative_timestamp'] = row[2]
            d['interrogator_timestamp'] = row[3]
            d['rssi'] = self.db_decrypt(row[4], row[3])
            d['epc96'] = self.db_decrypt(row[5], row[3])
            d['doppler'] = self.db_decrypt(row[6], row[3])
            d['phase'] = self.db_decrypt(row[7], row[3])
            d['antenna'] = row[8]
            d['rospecid'] = row[9]
            d['channelindex'] = row[10]
            d['tagseencount'] = row[11]
            d['accessspecid'] = row[12]
            d['inventoryparameterspecid'] = row[13]
            d['lastseentimestamp'] = row[14]
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
