import rpyc
from rpyc.utils.server import ThreadedServer
import datetime
from process import Process

running = False

date_time = datetime.datetime.now()
data, replicas = None, []


class ProcessService(rpyc.Service):

	def __init__(self):
		self.process = None
		self._conn = None

	def on_connect(self,conn):
		self._conn = conn
		# print("\nConnected on {}".format(date_time))
	
	def exposed_init_process(self, thread_id, state):
		self.process = Process(thread_id, state)
		self.process.start(self)

	def exposed_get_state(self):
		"""
			Passing ProcessThread to driver (for LIST command)
		"""
		return self.process.get_state()

	def exposed_set_timeout_upper(self, timeout_upper):
		"""
			Updating Process Timeout in ProcessThread (for TIME-P command)
		"""
		self.process.set_timeout_upper(timeout_upper)
		return None

	def exposed_cs_request_callback(self, external_timestamp):
		"""
			Check Process Monotonic clock and formulate response for Calling ClientService


		 	1. receiver is not accessing the resource and doesn't want to access it
				OUTCOME: Send OK to back to sender

			2. Receiver already has access to the resource
				TODO: IDEAL OUTCOME: Don't reply, queue the request
				Current implementation: Reply the denial message.

			3. Receiver is on the waiting list. Compare timestamps, lowest wins.
				OUTCOME:
					If OWN timestamp > request Timestamp (current process loses), then send back OK
					Otherwise receiver queues incoming request and send nothing back.
		"""
		if self.process.state == "do_not_want":
			return True
		elif self.process.state == "held":
			return False
		elif self.process.state == "want" and self.process.get_timestamp() > external_timestamp:
			return True
		else:
			return False

	def request_critical_section(self, process_id):
		"""
			Propagate cs_request from ProcessThread instance to ClientService instance
		"""
		return self._conn.root.request_access(process_id, self.process.get_timestamp())

	def access_critical_section(self):
		"""
			Propagate cs_access call from ProcessThread instance to ClientService instance
		"""
		return self._conn.root.hold_critical_section(self.process.id)

	def release_critical_section(self):
		"""
			Propagate critical_section RELEASE call from ClientService instance to ProcessThread instance
		"""
		return self._conn.root.release_critical_section(self.process.id)

	def on_disconnect(self, conn):
		# print("disconnected on {}\n".format(date_time))
		...


if __name__ == '__main__':
	try:
		server = ThreadedServer(ProcessService, port = 18812)
		server.start()
	except Exception as e:
		raise e
	finally:
		print("Exiting")
