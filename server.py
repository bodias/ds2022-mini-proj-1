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
		return self.process

	def exposed_set_timeout_upper(self, timeout_upper):
		self.process.set_timeout_upper(timeout_upper)
		return None

	def exposed_cs_request_callback(self, external_timestamp):
		if self.process.state == "do_not_want":
			return True
		elif self.process.getMonotonic() > external_timestamp:
			return True
		else:
			return False

	def request_CS(self):
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