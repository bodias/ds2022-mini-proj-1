import rpyc
import sys

server = "localhost"

if len(sys.argv) > 1:
	if int(sys.argv[1]) > 0:
		try:
			conn = rpyc.connect(server, 18811)
			if conn.root:
				conn.root.initialize_connections(int(sys.argv[1]))
				while True:
					try:
						remote_command = input("Input the Command:\t").lower().split(" ")
						conn.root.handle_remote_command(remote_command)
						if remote_command[0] == "exit":
							sys.exit(0)
					except KeyboardInterrupt:
						print("\nKeyboardInterrupt detected. Disconnecting from server.")
						conn.close()
						break
		except EOFError:
			print("Connection Terminated.")
		finally:
			print("Exiting.")

	else:
		print("No of connections cannot be less than 1.")
		sys.exit(0)
else:
	print("Usage: 'driver_service.py <number_of_connections>'")
	sys.exit(0)