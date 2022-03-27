
class Message:
	def __init__(self, message_type, timestamp, sender, receiver):
		self.message_type = message_type
		self.timestamp = timestamp
		self.sender = sender
		self.receiver = receiver

	def __repr__(self):
		return f"Message {self.message_type} at {self.timestamp} from {self.sender} to {self.receiver}"
