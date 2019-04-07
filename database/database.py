import base64
import numpy


class Database:
    def __init__(self, crypto, db_path='database.db', flush=False):
        self.db_path = db_path
        self.crypto = crypto
        self.flush = flush
        self.db_password = None

    def __del__(self):
        pass

    def close_db_connection(self, thread='main'):
        pass

    def open_db_connection(self):
        pass

    def init_database(self, conn):
        pass

    def flush_database(self, conn):
        pass

    def fetch_all(self, db_pw=''):
        return []

    def flush_audit(self, conn):
        pass

    def get_audit(self):
        return []

    def db_log(self, text):
        pass

    # get max data time in the db
    def get_max_rel_time(self):
        return -1

    # log this request to the Audit
    def insert_row(self, relativetime, interrogatortime, rssi, epc96, doppler, phase, antenna, db_pw=''):
        pass

    # log this request to the Audit
    def fetch_last_window(self, windowsize, db_pw=''):
        return []

    # log this request to the Audit
    def fetch_between_window(self, start, end, db_pw=''):
        return []

    # log this request to the Audit
    def fetch_since(self, since, db_pw=''):
        return []

    # log this request to the Audit
    def fetch_last_n_sec(self, n, db_pw=''):
        return []

    def dict_list_stats_by_tag(self, dictlist, tagcol, valcol):
        vals = dict()
        for d in dictlist:
            if not d[tagcol] in vals:
                vals[d[tagcol]] = []

            vals[d[tagcol]].append(float(d[valcol]))

        averages = []
        for v in vals:
            a = dict()
            a[tagcol] = v
            a['average'] = numpy.mean(vals[d[tagcol]])
            a['stdev'] = numpy.std(vals[d[tagcol]])
            averages.append(a)

        return averages

    # return an array of data dicts, each containing a start, end, and window
    # assumes dictlist is sorted by relative timestamp
    def break_into_timewindows(self, dictlist, width, timecol, valcol):
        data = []
        time = -1
        count = 0
        startcount = 0

        for d in dictlist:
            if time == -1:
                time = d[timecol]
                startcount = count
            elif abs(time - d[timecol]) >= width:
                x = dict()
                x['start'] = min(time, d[timecol])
                x['end'] = max(time, d[timecol])
                x['window'] = dictlist[startcount:count-1]
                x['size'] = len(dictlist[startcount:count-1])
                data.append(x)

                time = d[timecol]
                startcount = count

        if len(dictlist) % width != 0:
            x = dict()
            x['start'] = min(time, d[timecol])
            x['end'] = max(time, d[timecol])
            x['window'] = dictlist[startcount:len(dictlist)-1]
            x['size'] = len(dictlist[startcount:len(dictlist)-1])
            data.append(x)

        return data

    # return an array of data dicts, each containing a start, end, and data
    # assumes dictlist is sorted by relative timestamp
    def break_into_windows(self, dictlist, width, timecol, valcol):
        data = []

        for i in range(0, len(dictlist), width):
            window = dictlist[i:i+width]

            x = dict()
            x['start'] = i
            x['end'] = i+width
            x['window'] = window
            x['size'] = len(window)
            data.append(x)

        return data

# References:
#   http://www.pythoncentral.io/introduction-to-sqlite-in-python/
#   https://docs.python.org/2/library/sqlite3.html
#   http://stackoverflow.com/questions/14461851/how-to-have-an-automatic-timestamp-in-sqlite
#   http://pymotw.com/2/sqlite3/
