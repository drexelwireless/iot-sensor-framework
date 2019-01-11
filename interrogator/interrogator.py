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

	def close_server(self):
		pass

	def start(self):
		pass
