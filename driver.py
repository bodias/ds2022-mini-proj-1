import sys
import time

import rpyc
import datetime
import threading
from rpyc.utils.server import ThreadedServer
from process_service import ProcessService
from critical_section import CriticalSection

date_time = datetime.datetime.now()

connections, critical_section = [], CriticalSection()
"""
	Critical Section
	Instantiate Critical Section.
	args: 
		state: held or available 
			default: "available"
		Held by: [Process_id]
			default: None
		timeout-lower-bound: 
			constant 10
		timeout-upper-bound: 
			default 10
"""

class ListenerService(rpyc.Service):
	def on_connect(self, conn):
		...

	def on_disconnect(self, conn):
		...

	def exposed_initialize_connections(self, process_count):
		from connection_service import ConnectionService
		for process_id in range(process_count):
			conn = rpyc.connect("localhost", 18812, service = ConnectionService)
			conn.root.init_process(f"P{process_id + 1}", "do_not_want")
			print(f"Process P{process_id + 1} initialized")
			connections.append(conn)
		return None

	def exposed_handle_remote_command(self, command_args):
		remote_command = command_args[0]
		if len(command_args) > 3:
			print("Too many arguments", command_args)

		# handle exit
		elif remote_command == "exit":
			print("Exiting program")
			exit_program()
		# handle list
		elif remote_command == "list":
			try:
				"""
					Iterate through all connections and fetch process states
				"""
				for connection in connections:
					print(connection.root.get_state())
				return None
			except Exception as E:
				print("Error: ", E)

		# handle clock
		elif remote_command == "time-cs":
			try:
				if len(command_args) != 2 or not command_args[1].isdigit():
					print("Usage: 'time-cs <time(seconds)>'")
				else:
					# Handle `time-cs`
					# args: command_args[1] - Timeout for critical section
					critical_section.set_timeout(int(command_args[1]))
				return None
			except Exception as E:
				print("Error: ", E)

		# handle clock
		elif remote_command == "time-p":
			if len(command_args) != 2 or not command_args[1].isdigit():
				print("Usage: 'time-p <time(seconds)>'")
			else:
				try:
					for connection in connections:
						connection.root.set_timeout_upper(int(command_args[1]))
					return
				except:
					print("Error")

		# handle unsupported command
		else:
			print("Unsupported command:", remote_command)
		return None


def run_process_service(server):
	server.start()


def exit_program():
	for connection in connections:
		connection.close()
	sys.exit(0)


if __name__ == '__main__':
	# To run Server and driver processes separately, comment the following code block and run server in separate
	# terminal
	process_service = ThreadedServer(ProcessService, port = 18812)
	listener_service = ThreadedServer(ListenerService, port = 18811)

	try:
		# Launching the RPC server in a separate daemon thread (killed on exit)
		server_thread = threading.Thread(target=run_process_service, args=(process_service,), daemon=True)
		server_thread.start()
		listener_thread = threading.Thread(target=run_process_service, args=(listener_service,), daemon=True)
		listener_thread.start()
		while True:
			# Temporary workaround to give each connection time to communicate and keep connection alive
			for connection in connections:
				connection.root.get_state()
	except KeyboardInterrupt:
		print("Exiting")
	finally:
		exit_program()
