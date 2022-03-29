import rpyc
from rpyc.utils.server import ThreadedServer
import datetime
from constants import process_states, timeout_lower
import _thread
from process import Process
import time

running = False

date_time = datetime.datetime.now()
data, replicas = None, []



class ProcessService(rpyc.Service):

	def on_connect(self,conn):
		self._conn = conn
		print("\nconnected on {}".format(date_time))
	
	def exposed_init_process(self, thread_ID, state):
		self.process = Process(thread_ID, state)
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
		"""
		if self.process.state == "do_not_want":
			return True
		elif self.process.getMonotonic() > external_timestamp:
			return True
		else:
			return False

	def request_CS(self):
		"""
			Propogate cs_request from ProcessThread instance to ClientService instance
		"""
		return self._conn.root.request_access(self.process.getMonotonic())

	def on_disconnect(self,conn):  
		print("disconnected on {}\n".format(date_time))

if __name__=='__main__':
	try:
		t=ThreadedServer(ProcessService, port=18812)
		t.start()
	except Exception as e:
		raise e
	finally:
		print("Exiting")