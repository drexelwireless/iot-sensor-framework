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
from Crypto.Util.py3compat import bchr, bord

class MyCrypto:
    KEY_SIZE = 32
    BLOCK_SIZE = 16
    MAX_COUNTER_DIGITS = 16
    MAX_COUNTER_BITS = 128

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
        
    # https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/Padding.py
    def pycryptopad(self, data_to_pad, block_size, style='pkcs7'):
        """Apply standard padding.
        :Parameters:
          data_to_pad : byte string
            The data that needs to be padded.
          block_size : integer
            The block boundary to use for padding. The output length is guaranteed
            to be a multiple of ``block_size``.
          style : string
            Padding algorithm. It can be *'pkcs7'* (default), *'iso7816'* or *'x923'*.
        :Return:
          The original data with the appropriate padding added at the end.
        """

        padding_len = block_size-len(data_to_pad)%block_size
        if style == 'pkcs7':
            padding = bchr(padding_len)*padding_len
        elif style == 'x923':
            padding = bchr(0)*(padding_len-1) + bchr(padding_len)
        elif style == 'iso7816':
            padding = bchr(128) + bchr(0)*(padding_len-1)
        else:
            raise ValueError("Unknown padding style")
            
        bdata_to_pad = bytearray(data_to_pad, 'utf-8')
        bpadded = bdata_to_pad + padding
        return bytes(bpadded)

    # https://github.com/dlitz/pycrypto/blob/master/lib/Crypto/Util/Padding.py
    def pycryptounpad(self, padded_data, block_size, style='pkcs7'):
        """Remove standard padding.
        :Parameters:
          padded_data : byte string
            A piece of data with padding that needs to be stripped.
          block_size : integer
            The block boundary to use for padding. The input length
            must be a multiple of ``block_size``.
          style : string
            Padding algorithm. It can be *'pkcs7'* (default), *'iso7816'* or *'x923'*.
        :Return:
            Data without padding.
        :Raises ValueError:
            if the padding is incorrect.
        """

        pdata_len = len(padded_data)
        if pdata_len % block_size:
            raise ValueError("Input data is not padded")
        if style in ('pkcs7', 'x923'):
            padding_len = bord(padded_data[-1])
            if int(padding_len)<1 or int(padding_len)>min(int(block_size), int(pdata_len)):
                raise ValueError("Padding is incorrect.")
            if style == 'pkcs7':
                if padded_data[-padding_len:]!=bchr(padding_len)*padding_len:
                    raise ValueError("PKCS#7 padding is incorrect.")
            else:
                if padded_data[-padding_len:-1]!=bchr(0)*(padding_len-1):
                    raise ValueError("ANSI X.923 padding is incorrect.")
        elif style == 'iso7816':
            padding_len = pdata_len - padded_data.rfind(bchr(128))
            if padding_len<1 or padding_len>min(block_size, pdata_len):
                raise ValueError("Padding is incorrect.")
            if padding_len>1 and padded_data[1-padding_len:]!=bchr(0)*(padding_len-1):
                raise ValueError("ISO 7816-4 padding is incorrect.")
        else:
            raise ValueError("Unknown padding style")
        return padded_data[:-padding_len]
    
    def pad(self, s):
        #padded = s + (self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE) * chr(self.BLOCK_SIZE - len(s) % self.BLOCK_SIZE)
        padded = self.pycryptopad(s, self.BLOCK_SIZE, style='pkcs7')
        return padded

    def unpad(self, s):
        #unpadded = s[0:-ord(s[-1])]
        unpadded = self.pycryptounpad(s, self.BLOCK_SIZE, style='pkcs7')
        return unpadded

    def get_ssl_context(self):
        return self.context

    def get_db_aes(self, db_password, counter):
        self.db_password = db_password
        self.db_password = self.db_password.encode('ascii')
        key = hashlib.sha512(self.db_password).hexdigest()[:self.KEY_SIZE]
        ctr = Counter.new(self.MAX_COUNTER_BITS, initial_value=counter)
        aes = AES.new(key.encode("utf8"), AES.MODE_CTR, counter=ctr)
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
