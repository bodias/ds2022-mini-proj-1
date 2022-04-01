import time
import threading
import random
import rpyc
from rpyc.utils.server import ThreadedServer
from constants import ServerType, State, MessageType
from constants import PROC_TIMEOUT_LOWER, CS_TIMEOUT_LOWER

class Message(object):
    """ Message object for communication.
    It serves to encapsulate parameters of the message
    """
    def __init__(self, type: MessageType, timestamp, sender:str, receiver:str):
        """ Constructor

        Parameters:
            type: one of the types in MessageType (MessageType.ACK, MessageType.REQUEST)
            timestamp: timestamp when the message was sent
            sender: process id of the message sender
            receiver: process id of the message receiver
        """
        self.type = type
        self.timestamp = timestamp
        self.sender = sender
        self.receiver = receiver

    def __repr__(self):
        return f"Message {self.type} at {self.timestamp} from {self.sender} to {self.receiver}"

class Process(threading.Thread):
    def __init__(self, id, server_port:int, cs_timeout_upper=10, proc_timeout_upper=5, verbose=0):
        super(Process, self).__init__()
        self.id = id        
        self._state = State.DO_NOT_WANT
        self._cs_timeout_upper = cs_timeout_upper
        self._proc_timeout_upper = proc_timeout_upper
        self.server_port = server_port
        self._comm_server = CommServer(self, self.server_port, verbose=verbose)
        self.outgoing_conn = {}
        self.incoming_msg_queue = []
        self.request_resource_confirmation = []
        self.request_timestamp = None
        self._timer = None
        self._running = True
        self.verbose = verbose

    def __str__(self):
        return f"{self.id}, {self._state.name}"

    __repr__ = __str__
    
    def set_proc_timeout_upper(self, proc_timeout_upper: int):
        self._proc_timeout_upper = max(proc_timeout_upper, PROC_TIMEOUT_LOWER)
        if self.verbose:
            print(f"Process {self.id} timeout upper bound set to {self._proc_timeout_upper}. ([{PROC_TIMEOUT_LOWER}, {self._proc_timeout_upper}])")

    def set_cs_timeout_upper(self, cs_timeout_upper: int):
        self._cs_timeout_upper = max(cs_timeout_upper, CS_TIMEOUT_LOWER)
        if self.verbose:
            print(f"Process {self.id} Critical Section timeout upper bound set to {self._cs_timeout_upper}. ([{CS_TIMEOUT_LOWER}, {self._cs_timeout_upper}])")

    def get_timestamp(self):
        return time.monotonic()

    def countdown(self):
        time.sleep(1)
        self._timer -= 1

    def connect_to(self, process):
        try:
            conn = rpyc.connect(host="localhost", port=process.server_port, service=Communication(ServerType.CLIENT, self))
            self.outgoing_conn[process.id] = conn
        except:
            # TODO: deal with exception
            raise
    
    def start_comms(self):
        """ 
        Initiate RPyc server that handles incomming messages
        self._comm_server is a class that implements threads so it
        can start the ThreadedServer without blocking the caller.

        Each process will have ONE thread with a RPyC server.
        """
        self._comm_server.setDaemon(True)
        self._comm_server.start()        

    def send_message(self, msg: Message):
        """
        Sends message to connected clients in the message using RPC through RPyC.
        A message has ONE sender and ONE receiver (it's "unicast")
        The message is sent through the "conn" object result of rpyc.connect()
        that is stored for all connected process (outgoing messages)

        Need to unpack values into primitive types because RPC call doesn't
        Handle well objects
        """
        self.outgoing_conn[msg.receiver].root.process_message(msg.type.value, msg.timestamp, msg.sender, msg.receiver)
            
    def process_incoming_message(self, msg: Message):
        """
        Process all incomming messages comming through the RPyC ThreadedServer.
        This function is called every time a message is received in the RPC server,
        handling the message following Ricart Agrawala algorithm.
        """
        if self.verbose:
            print(f"{str(msg.type)} SENDER: {msg.sender}-> RECEIVER: {msg.receiver} - {msg.timestamp}")
    
        # Based on msg_type handle appropriately
        if msg.type == MessageType.REQUEST:
            # 1. receiver is not accessing the resource and doesn't want to access it
            #   OUTCOME: Send OK to back to sender
            if self._state == State.DO_NOT_WANT:
                ack_message = Message(MessageType.ACK, self.get_timestamp(), self.id, msg.sender)
                self.send_message(ack_message)
             # 2. Receiver already has access to the resource
             #   OUTCOME: Don't reply, queue the request
            elif self._state == State.HELD:
                self.incoming_msg_queue.append(msg)
            # 3. Receiver is on the waiting list. Compare timestamps, lowest wins.
            #   OUTCOME: 
            #       If OWN timestamp > request Timestamp (current process loses), then send back OK
            #       Otherwise receiver queues incoming request and send nothing back
            elif self._state == State.WANTED:
                if self.request_timestamp > msg.timestamp:
                    ack_message = Message(MessageType.ACK, self.get_timestamp(), self.id, msg.sender)
                    self.send_message(ack_message)
                else:
                    self.incoming_msg_queue.append(msg)

        elif msg.type == MessageType.ACK:        
            # ACK received, update list of request confirmation
            self.request_resource_confirmation.append(msg)
            if self.is_resource_available():
                self.lock_resource()                
        else:
            raise Exception("Unknown message type")

    def is_resource_available(self):
        """
        Checks if resource (CS) is available by checking if the list of process
        that have confirmed (ACKed) the request is the same as the list of connected
        processes.
        """
        connected_processes = sorted(list(self.outgoing_conn.keys()))
        confirmation_received = [msg.sender for msg in self.request_resource_confirmation]
        confirmation_received.sort()
        if self.verbose:
            print(f"Connected processes: {connected_processes}")
            print(f"confirmation received from: {confirmation_received}")
        if connected_processes == confirmation_received:
            return True
        return False    
    
    def lock_resource(self):
        """
        locks critical serction - Change state to HELD
        """
        # change state to HELD
        self._state = State.HELD
        if self.verbose:
            print(f"{self.id} locked resource")

    def request_resource(self):
        """
        request critical serction - Change state to WANTED.
        Broadcast to all connected process requesting the CS, clear the list
        of request confirmation received.
        """
        # send request message to all other process (broadcast)     
        self._state = State.WANTED
        if self.verbose:
            print(f"{self.id} requested resource")
        # TODO: should the timestamp vary for erach message?
        self.request_timestamp = self.get_timestamp()
        self.request_resource_confirmation = []
        for process, _ in self.outgoing_conn.items():       
            request_msg = Message(MessageType.REQUEST, self.request_timestamp, self.id, process)
            self.send_message(request_msg)

    def release_resource(self):
        """
        Release critical serction - Change state to DO_NOT_WANT.
        Send ACK to all messages received while process was in HELD state.
        """
        # send back OK message to all waiting in the queue
        self._state = State.DO_NOT_WANT
        if self.verbose:
            print(f"{self.id} released resource")
        for msg in self.incoming_msg_queue:
            self.send_message(Message(MessageType.ACK, time.monotonic, self.id, msg.sender))
    
    def kill(self):
        self._running = False
    
    def run(self):
        """ 
        Main thread. Each process manages its own resources:
        - Process timeout
        - CS timeout        

        Every loop will take time-cs or time-p seconds depending on the current state:
        - If DO_NOT_WANT: timer is draw from [5, t]. When time is out then randomly choses if
            process it request CS (change state to WANTED)
        - if WANTED: do nothing. Wanted is waiting for confirmation of requests through RPyC server
        - if HELD: timer is draw from [10, t]. When time is out then release the CS
        """
        print(f"Starting thread in process {self.id}")
        while self._running:
            action = None
            if self._state == State.DO_NOT_WANT:
                self._timer = random.randint(PROC_TIMEOUT_LOWER, self._proc_timeout_upper)
                action = random.choice([None, self.request_resource])
            elif self._state == State.HELD:
                self._timer = random.randint(CS_TIMEOUT_LOWER, self._cs_timeout_upper)
                action = self.release_resource

            while self._timer:
                self.countdown()
            if action:
                action()            
        print(f"Thread in process {self.id} ended.")


class CommServer(threading.Thread):
    """
    Only needed to be an independent thread on the ThreadedServer
    because it blocks when calling server.start() in the Process class
    TODO: Does python support multiple inheritance? 
    """
    def __init__(self, process:Process, port:int, verbose=0):
        super(CommServer, self).__init__()
        self.port = port
        self.server = ThreadedServer(Communication(ServerType.SERVER, process, verbose=verbose), port = self.port)

    def run(self):
        self.server.start()

class Communication(rpyc.Service):
    """
    RPyC service that can be instantiated as ThreadedServer or Client.
    It has a pointer to the process that holds the server in self.process.
    Every communication received through RPC is then redirected to the 
    "self.process.process_incoming_message" to handle the message
    """
    def __init__(self, server_type:ServerType, process:Process, verbose=0):
        super(Communication, self).__init__()
        self.server_type = server_type
        self.process = process
        self._conn = None
        self.verbose = verbose
        if self.verbose:
            print(f"Initializing communication {ServerType.SERVER.name} in {self.process.id}")
        
    def on_connect(self, conn):
        self._conn = conn
        incomming_conn_id = self._conn.root.get_process_id()        
        if self.verbose:
            print(f"{self.server_type.name} {self.process.id} accepted connection from {incomming_conn_id}")
    
    def exposed_get_process_id(self):
        return self.process.id

    def exposed_process_message(self, msg_type, timestamp, sender, receiver):
        """
        Only route the message back to the process object.
        Process has the implementation of messaging handling
        """
        if self.verbose:
            print(f"Handling msg {str(msg_type)} from 'Communication' class")        
        # This was causing lock because it triggers communication on the opposite direction
        #sender = self._conn.root.get_process_id()
        self.process.process_incoming_message(Message(MessageType(msg_type), timestamp, sender, receiver))

if __name__=="__main__":
    # start_port = 18812
    # P_A = Process("A", 18812, 10, 5)
    # P_B = Process("B", 18813, 10, 5)
    # P_C = Process("C", 18814, 10, 5)

    # P_A.start_comms() 
    # print("Server A started")
    # P_B.start_comms()
    # print("Server B started")
    # P_C.start_comms()
    # print("Server C started")
    
    # P_A.connect_to(P_B)
    # P_A.connect_to(P_C)

    # P_B.connect_to(P_A)
    # P_B.connect_to(P_C)    

    # P_C.connect_to(P_A)
    # P_C.connect_to(P_B)
    # time.sleep(1) # wait for communication
    # print(f"A connections: {list(P_A.outgoing_conn.keys())}")
    # print(f"B connections: {list(P_B.outgoing_conn.keys())}")
    # print(f"C connections: {list(P_C.outgoing_conn.keys())}")

    # P_A.outgoing_conn['B'].root.process_message(MessageType.TEST.value, time.monotonic(),'A','B')
    # P_A.outgoing_conn['C'].root.process_message(MessageType.TEST.value, time.monotonic(),'A','C')
    
    # P_B.outgoing_conn['A'].root.process_message(MessageType.TEST.value, time.monotonic(),'B','A')
    # P_B.outgoing_conn['C'].root.process_message(MessageType.TEST.value, time.monotonic(),'B','C')

    # P_C.outgoing_conn['A'].root.process_message(MessageType.TEST.value, time.monotonic(),'C','A')
    # P_C.outgoing_conn['B'].root.process_message(MessageType.TEST.value, time.monotonic(),'C','B')
    # time.sleep(1)

    # # SIMULATION
    # print("### SIMULATION OF A LIST OF REQUEST/RELEASE")

    # P_A.request_resource()
    # P_B.request_resource()
    # P_C.request_resource()
    # time.sleep(2)
    # P_A.release_resource()
    # time.sleep(2)
    # P_B.release_resource()

    P_A = Process("A", 18812, 10, 5, verbose=1)
    P_B = Process("B", 18813, 10, 5, verbose=1)

    P_A.start_comms() 
    print("Server A started")
    P_B.start_comms()
    print("Server B started")

    P_A.connect_to(P_B)
    P_B.connect_to(P_A)
    print(P_A)
    print(P_B)
    P_A.start()
    P_B.start()
