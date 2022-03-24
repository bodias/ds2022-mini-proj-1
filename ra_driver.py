import sys
from process import Process

processes = []

def handle_remote_command(command_args):
	remote_command = command_args[0]
	if len(command_args) > 3:
		print("Too many arguments")

	# handle exit
	elif remote_command == "exit":
		print("Exiting program")
		# TODO: kill process threads
		sys.exit(0)
	# handle list
	elif remote_command == "list":
		try:
			# TODO: List Processes along with their status
			for process in processes:
				print(process)
		except:
			print("Error")

	# handle clock
	elif remote_command == "time-cs":
		try:
			if len(command_args) != 2 or not command_args[1].isdigit():
				print("Usage: 'time-cs <time(seconds)>'")
			else:
				...
				# TODO: Handle time-cs  
					# args: command_args[1] - Timeout for critical section
		except:
			print("Error")

	# handle clock
	elif remote_command == "time-p":
		try:
			if len(command_args) != 2 or not command_args[1].isdigit():
				print("Usage: 'time-p <time(seconds)>'")
			else:
				...
				# TODO: Handle time-p call
					# args: command_args[1] - Timeout interval for all processes
		except:
			print("Error")

	# handle unsupported command        
	else:
		print("Unsupported command:", remote_command)


def initialize_processes(process_count):
	for process_id in range(process_count):
		# instantiate new process.
			# args: process_id: f'P{process_id + 1}'
			# 		State: (HELD, WANTED, and DO-NOT-WANT) default: DO-NOT-WANT
			# 		timeout-lower-bound: Fixed 5
			# 		timeout-upper-bound: default 5
		process = Process(f"P{process_id + 1}", "do_not_want")
		processes.append(process)
		
	# Instantiate Critical Section.
		# args: state: HELD or Available
		# 		Held by: Process_id
		# 		timeout-lower-bound: fixed 10
		# 		timeout-upper-bound: default 10




if __name__ == '__main__':
	if len(sys.argv) > 1:
		initialize_processes(int(sys.argv[1]))
	else:
		print("Usage: 'driver_service.py <number_of_processes>'")
		sys.exit(0)

	while True:
		command = input("$ ")
		handle_remote_command(command.lower().split(" "))