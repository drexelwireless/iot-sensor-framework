import json
import sys
from httplib2 import Http
from time import sleep, time

class ExampleClient():
    def __init__(self, _db_host, _db_password, _cert_path):
        self.start_timestamp = 0
        self.latest_timestamp = 0
        self.count = 0
        self.db_password = _db_password
        self.db_host = _db_host
        self.cert_path = _cert_path
        
        self.exiting = False

        if self.cert_path != 'NONE':
            self.http_obj = Http(ca_certs=self.cert_path)
        else:
            self.http_obj = Http(disable_ssl_certificate_validation=True)

    # input_dicts is an array of dict() items; this can also be a single dict
    # this can be called as often as one likes; however, there is a performance hit due to the I/O on each call
    # so a producer/consumer threaded paradigm and/or a batch array insert is desirable here
    def insert_tags(self, input_dicts):
        url = self.db_host + '/api/iot'

        resp, content = self.http_obj.request(uri=url, method='PUT', headers={
            'Content-Type': 'application/json; charset=UTF-8'}, body=json.dumps(input_dicts))

    def test_insert(self): 
        input_dicts = []
        
        for i in range(5):
            # freeform can be a dict of your choosing
            freeform = dict()
            freeform['data'] = dict()
            freeform['data']['name'] = 'test'
            freeform['data']['value'] = 1
            
            self.latest_timestamp = time()
            if self.start_timestamp == 0:
                self.start_timestamp = self.latest_timestamp
            
            # inputdict structure should not be changed; customize freeform instead!
            input_dict = dict()
            input_dict['data'] = dict()
            input_dict['data']['db_password'] = self.db_password
            input_dict['data']['freeform'] = freeform
            input_dict['data']['relative_time'] = self.latest_timestamp - self.start_timestamp
            input_dict['data']['interrogator_time'] = self.latest_timestamp

            input_dicts.append(input_dict)
            
            sleep(1)

        self.insert_tags(input_dicts)
        
    def retrieve(self):
        url = self.db_host + '/api/iot'
        
        body = dict()
        body['data'] = dict()
        body['data']['db_password'] = self.db_password
        
        resp, content = self.http_obj.request(uri=url, method='POST', headers={
            'Content-Type': 'application/json; charset=UTF-8'}, body=json.dumps(body))
            
        data = json.loads(content)

        print(data)
        
c = ExampleClient("https://localhost:5000", "abc123", "NONE")
c.test_insert()
c.retrieve()
