import requests

class Interrogator:
    def __init__(self, _db_host, _db_password, _cert_path="NONE", _debug=False, _dispatchsleep=0.25):
        self.start_timestamp = 0
        self.latest_timestamp = 0
        self.count = 0
        self.db_password = _db_password
        self.db_host = _db_host
        self.cert_path = _cert_path
        self.debug = _debug
        self.dispatchsleep = _dispatchsleep
        
    def sendhttp(self, url, headerdict=dict(), bodydict=dict(), method='POST'):
        if self.cert_path == 'NONE':
            verifypath = False
        else:
            verifypath = self.cert_path

        if method.lower() == 'get':
            fun = requests.get
        elif method.lower() == 'put':
            fun = requests.put
        elif method.lower() == 'post':
            fun = requests.post

        response = fun(url, verify = verifypath, data = json.dumps(bodydict), headers=headerdict)

        return response, response.text

    def close_server(self):
        pass

    def start(self):
        pass
