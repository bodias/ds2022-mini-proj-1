import _thread

from constants import process_states

class Process:
	def __init__(self, process_id, state, timeout_upper = 5):
		###################################################################
		# args: process_id: f'P{process_id + 1}'
		#		State: (HELD, WANTED, and DO-NOT-WANT) default: DO-NOT-WANT
		# 		timeout-upper-bound: default 5
		####################################################################
		self.id = process_id
		self.state = state
		self.timeout_lower = 5
		self.timeout_upper = timeout_upper

	def __str__(self):
		return f"{self.id}, {process_states[self.state]}"

	def __unicode__(self):
		return f"({self.id}, {process_states[self.state]})"

	__repr__ = __unicode__


	def start(self):
		_thread.start_new_thread(self.run, ())

	def run(self):
		while True:
			# Run background Tasks for process.
			...

	def set_timeout_upper(self, timeout_upper):
		self.timeout_upper = timeout_upper

	def set_state(self, state):
		self.state = state