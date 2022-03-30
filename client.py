import rpyc
from driver import connections


class ClientService(rpyc.Service):
	def __init__(self):
		self._conn = None

	def on_connect(self, conn):
		self._conn = conn
		# print("\nConnected on {}".format(date_time))

	def exposed_request_access(self, external_timestamp):
		"""
			When ProcessThread with "WANTED" state requests access to the Critical Section,
			This method broadcasts the request to other ProcessThread connections with their timestamp

			If all methods return positive callback from Remote procedure (cs_request_callback) call,
				TODO: Notify calling ProcessThread, and Take over critical section
			Else:
				TODO: Notify negative response to calling ProcessThread.
		"""
		flag = True
		for connection in connections:
			if connection != self._conn:
				flag = flag and connection.root.cs_request_callback(external_timestamp)
		if flag:
			return True
		else:
			return False

	def exposed_hold_critical_section(self, conn_id):
		"""
			TODO:
				1. Access current critical section state,
					a. If critical section is Free, allow access to the process. Return True
					b. If critical section is Held, deny access to the process. Return False
		"""
		return True

	def on_disconnect(self, conn):
		# print("disconnected on {}\n".format(date_time))
		...