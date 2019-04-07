from werkzeug.serving import make_ssl_devcert
import ssl
from Crypto.Cipher import AES
from Crypto import Random
from Crypto.Util import Counter
import os
import os.path
import hashlib
import datetime
from dateutil import parser
import time


class MyCrypto:
    KEY_SIZE = 32
    BLOCK_SIZE = 16

    def __init__(self, hostname, key_path_prefix='key'):
        self.key_path_prefix = key_path_prefix

        self.pkeypath = key_path_prefix + '.key'
        self.certpath = key_path_prefix + '.crt'

        # Init SSL
        if not os.path.isfile(self.pkeypath) or not os.path.isfile(self.certpath):
            make_ssl_devcert(key_path_prefix, host=hostname)
            os.chmod(self.pkeypath, 0o600)
            os.chmod(self.certpath, 0o600)

        self.context = (self.certpath, self.pkeypath)

        # No database password yet, we'll set this on the first web call from the user and on each subsequent call ensure that it is the same as what was stored (else regenerate the key)
        self.db_password = None

    def pad(self, s):
        return s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)

    def unpad(self, s):
        return s[0:-ord(s[-1])]

    def get_ssl_context(self):
        return self.context

    def raw_time_counter_to_epoch(self, counter):
        # use this in the counter lambda defining the AES object if counter is an absolute datetime sensitive to microseconds (must be globally unique)
        timestamp = parser.parse(counter)
        delta = timestamp - datetime.datetime(1970, 1, 1)
        micros = '%d' % (delta.total_seconds() * 100 + delta.microseconds)
        return self.pad_timer_counter(micros)

    def pad_timer_counter(self, micros):
        micros_str = str(micros)
        padded = self.pad(micros_str)
        return padded

    def get_db_aes(self, db_password, counter):
        self.db_password = db_password
        self.db_password = self.db_password.encode('ascii')
        key = hashlib.sha512(self.db_password).hexdigest()[:self.KEY_SIZE]
        ctr = Counter.new(128, initial_value=int(counter))
        aes = AES.new(key, AES.MODE_CTR, counter=ctr)
        return aes

    def get_db_key(self, db_password, counter=None):
        self.db_password = db_password
        if counter == None:
            key = hashlib.sha512(self.db_password).hexdigest()[:self.KEY_SIZE]
        else:
            key = hashlib.sha512(self.db_password +
                                 str(counter)).hexdigest()[:self.KEY_SIZE]
        return key

# References:
#   http://stackoverflow.com/questions/12524994/encrypt-decrypt-using-pycrypto-aes-256
#   https://gist.github.com/crmccreary/5610068
#   http://werkzeug.pocoo.org/docs/0.10/serving/
