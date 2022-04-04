import random
from constants import cs_default_timeout, cs_states


class CriticalSection:
	def __init__(self, timeout = cs_default_timeout, state="available"):
		self.timeout = timeout
		self.state = state
		self.held_by = None

	def __str__(self):
		return f"{cs_states[self.state]}: held_by {self.held_by} {self.timeout}"

	__repr__ = __str__

	def get_state(self):
		return self.state

	def set_state(self, state):
		self.state = state

	def get_timeout(self):
		return random.randint(cs_default_timeout, self.timeout)

	def set_timeout(self, timeout):
		self.timeout = max(self.timeout, timeout)

	def takeover(self, process_id):
		if self.state == "available":
			self.held_by = process_id
			self.state = "held"
			return self.get_timeout()
			print(self)
		return 0

	def release(self, process_id):
		if self.state == "held" and self.held_by == process_id:
			self.held_by = None
			self.state = "available"
			return True
		return False
