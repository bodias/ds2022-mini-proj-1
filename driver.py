import sys
from ra_mutual_exclusion_unidirectional import Process
from constants import PROC_TIMEOUT_LOWER, CS_TIMEOUT_LOWER

def handle_remote_command(command_args, process_list):
	remote_command = command_args[0]
	if len(command_args) > 3:
		print("Too many arguments")

	# handle exit
	elif remote_command == "exit":
		print("Exiting program")
		exit_program(process_list)
	# handle list
	elif remote_command == "list":
		try:
			"""
				Iterate through all connections and fetch process states
			"""
			for process in process_list:
				print(process)
		except Exception as E:
			print("Error: ", E)

	# handle clock
	elif remote_command == "time-cs":
		try:
			if len(command_args) != 2 or not command_args[1].isdigit():
				print("Usage: 'time-cs <time(seconds)>'")
			else:
				for process in process_list:
					process.set_cs_timeout_upper(int(command_args[1]))
				print(f"Critical section timeout upper bound set to {max(CS_TIMEOUT_LOWER, int(command_args[1]))}.")
		except Exception as E:
			print("Error: ", E)

	# handle clock
	elif remote_command == "time-p":
		try:
			if len(command_args) != 2 or not command_args[1].isdigit():
				print("Usage: 'time-p <time(seconds)>'")
			else:
				for process in process_list:
					process.set_proc_timeout_upper(int(command_args[1]))
				print(f"Process timeout upper bound set to {max(PROC_TIMEOUT_LOWER, int(command_args[1]))}.")
		except:
			print("Error")

	# handle unsupported command
	else:
		print("Unsupported command:", remote_command)

def initialize_processes(process_count, verbose=0):
	initial_port = 18812
	process_list = []
	# Create all processes and start comm server (incoming comms)
	for process_id in range(process_count):
		process = Process(f"P{process_id + 1}", initial_port, verbose=verbose)
		initial_port += 1
		print(f"Process P{process_id + 1} initialized.")
		process.start_comms() 
		print(f"Communication in P{process_id + 1} started.")
		process_list.append(process)

	# Connect all process one by one (clients, outgoing comms)
	for server in process_list:
		for client in process_list:
			if client.id != server.id:
				client.connect_to(server)

	for process in process_list:		
		print(f"{process.id} connections: {list(process.outgoing_conn.keys())}")
		process.setDaemon(True)
		process.start()		

	return process_list

def exit_program(process_list):
	for process in process_list:
		process.kill()
	sys.exit(0)

if __name__ == '__main__':

	process_list = None
	verbose = 0
	if len(sys.argv) > 1:
		if int(sys.argv[1]) > 0:
			# if third argument is --verbose, show output of commands
			if len(sys.argv) == 3:
				if sys.argv[2] == "--verbose":
					verbose = 1
			process_list = initialize_processes(int(sys.argv[1]), verbose=verbose)
		else:
			print("No of connections cannot be less than 1.")
			sys.exit(0)
	else:
		print("Usage: 'driver_service.py <number_of_connections>'")
		sys.exit(0)

	try:
		while True:
			command = input("$ ")
			handle_remote_command(command.lower().split(" "), process_list)
	except KeyboardInterrupt as e:
		print("Exiting")
	finally:
		exit_program(process_list)
