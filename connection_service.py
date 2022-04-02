import rpyc
from ra_program_server import connections, critical_section, verbose


class ConnectionService(rpyc.Service):
	def __init__(self):
		self._conn = None

	def on_connect(self, conn):
		self._conn = conn
		# print("\nConnected on {}".format(date_time))

	def exposed_request_access(self, process_id, external_timestamp):
		"""
			When ProcessThread with "WANTED" state requests access to the Critical Section,
			This method broadcasts the request to other ProcessThread connections with their timestamp

			If all methods return positive callback from Remote procedure (cs_request_callback) call,
				a. Notify calling ProcessThread.
				b. Take over critical section.
			Else:
				Notify negative response to calling ProcessThread.
		"""
		flag = True
		for connection in connections:
			if connection != self._conn:
				flag = flag and connection.root.cs_request_callback(external_timestamp)
		if flag:
			if verbose:
				print(f"ConnectionService: {process_id} received OK from all processes")
			return True
		if verbose:
			print(f"ConnectionService: {process_id} received one or more denials.")
		return False

	def exposed_hold_critical_section(self, conn_id):
		"""
			1. Access current critical section state,
				a. If critical section is Free, allow access to the process. Return True
				b. If critical section is Held, deny access to the process. Return False
		"""
		return critical_section.takeover(conn_id)

	def exposed_release_critical_section(self, conn_id):
		"""
			1. Access current critical section state,
				a. If critical section is Free, allow access to the process. Return True
				b. If critical section is Held, deny access to the process. Return False
		"""
		return critical_section.release(conn_id)

	def on_disconnect(self, conn):
		# print("disconnected on {}\n".format(date_time))
		...
