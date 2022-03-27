import _thread
import random
import time
from constants import process_states, timeout_lower, message_type
from message import Message
import queue

class Process:
	def __init__(self, process_id, state, timestamp = 0, timeout_upper = 5):
		######################################################################################################
		# args: process_id: f'P{process_id + 1}'
		#		State: 					(HELD, WANTED, and DO-NOT-WANT) default: DO-NOT-WANT
		#		timestamp: 				Lamport timestamp. Default 0
		# 		timeout-upper-bound: 	default 5
		#######################################################################################################
		self.id = process_id
		self.state = state
		self.timestamp = timestamp
		self.timeout_upper = timeout_upper
		self.timer = None

	def __str__(self):
		return f"{self.id}, {process_states[self.state]} {self.timestamp}, {self.timeout_upper}"

	def __unicode__(self):
		return f"({self.id}, {process_states[self.state]})"

	__repr__ = __unicode__


	def start(self, processes, message_queues):
		_thread.start_new_thread(self.run, (processes, message_queues))

	def run(self, processes, message_queues):
		while True:
			# Run background Tasks for process.
			timeout = random.randint(timeout_lower, self.timeout_upper)
			self.timer = timeout
			if self.state == "want":
				## Send timestamp and await `OK`
				for process in processes:
					if process.id != self.id:
						req_message = Message(message_type['req'], self.timestamp, self.id, process.id)
						message_queues[process.id].put(req_message)
						# self.cs_request_status[process.name] = False
			while self.timer:
				self.countdown()
				self.check_message(message_queues)
			self.change_state()

	def set_timeout_upper(self, timeout_upper):
		self.timeout_upper = max(timeout_upper, timeout_lower)

	def set_state(self, state):
		self.state = state

	def countdown(self):
		time.sleep(1)
		self.timer -= 1
		self.timestamp += 1

	def change_state(self):
		self.state = random.choice(["want", "do_not_want"])

	def check_message(self, message_queues):
		try:
			message = message_queues[self.id].get(block=False)
			if message.message_type == message_type['req']:
				if self.timestamp > message.timestamp:
					ack_msg = Message(message_type['ack'], self.timestamp, self.id, message.sender)
					message_queues[message.sender].put(ack_msg)
			elif message.message_type == message_type['ack']:
 				print(f"received ack from {message.sender}")
			else:
 				print(f"Unknown message: {message}")

		except queue.Empty:
			...

