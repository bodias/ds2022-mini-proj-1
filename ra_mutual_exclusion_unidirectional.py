import time
import threading
import random
import enum
import rpyc
from rpyc.utils.server import ThreadedServer
#from Queue import Queue
#import Queue
PROC_TIMEOUT_LOWER = 5
CS_TIMEOUT_LOWER = 10

class State(enum.Enum):
    DO_NOT_WANT = 0
    WANTED = 1
    HELD = 2

class MessageType(enum.Enum):
    REQUEST = 0
    RELEASE = 1
    ACK = 2
    TEST = 3

class ServerType(enum.Enum):
    SERVER = "server"
    CLIENT = "client"

class Message(object):
    def __init__(self, type, timestamp, sender, receiver):
        self.type = type
        self.timestamp = timestamp
        self.sender = sender
        self.receiver = receiver

    def __repr__(self):
        return f"Message {self.type} at {self.timestamp} from {self.sender} to {self.receiver}"

class Process:
    def __init__(self, id, server_port, cs_timeout_upper=10, proc_timeout_upper=5):
        self.id = id        
        self._state = State.DO_NOT_WANT
        self._cs_timeout_upper = cs_timeout_upper
        self._proc_timeout_upper = proc_timeout_upper
        self.server_port = server_port
        self._comm_server = CommServer(self, self.server_port)
        self.outgoing_conn = {}
        self.incoming_msg_queue = []
        self.request_resource_confirmation = []
        self.request_timestamp = None
        self._timer = None

    def __str__(self):
        return f"{self.id}, {self._state}"

    __repr__ = __str__
    
    def set_proc_timeout_upper(self, proc_timeout_upper):
        self._proc_timeout_upper = max(proc_timeout_upper, PROC_TIMEOUT_LOWER)

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
        # self.comm_server has its own thread and won't block the process
        self._comm_server.setDaemon(True)
        self._comm_server.start()        
        # Start main thread with timeout handling
        # 

    # Need to unpack values into primitive types for RPC call
    def send_message(self, msg: Message):
        self.outgoing_conn[msg.receiver].root.process_message(msg.type.value, msg.timestamp, msg.sender, msg.receiver)
            
    def process_incoming_message(self, msg: Message):
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
            print("Unknown message type")

    def is_resource_available(self):
        connected_processes = sorted(list(self.outgoing_conn.keys()))
        confirmation_received = [msg.sender for msg in self.request_resource_confirmation]
        confirmation_received.sort()
        print(f"Connected processes: {connected_processes}")
        print(f"confirmation received from: {confirmation_received}")
        if connected_processes == confirmation_received:
            return True
        return False    
    
    # def change_state(self):
    #     # If process is in DO_NO_WANT state randomly change to WANTED
    #     # If any other state (WANTED, HELD) don't do anything since these
    #     # changes are triggered by communication
    #     if self._state == State.DO_NOT_WANT:
    #         self._state(random.choice([State.DO_NOT_WANT, State.WANTED]))
    
    def lock_resource(self):
        # change state to HELD
        self._state = State.HELD
        print(f"{self.id} locked resource")

    def request_resource(self):
        # send request message to all other process (broadcast)     
        self._state = State.WANTED
        print(f"{self.id} requested resource")
        self.request_timestamp = self.get_timestamp()
        self.request_resource_confirmation = []
        for process, _ in self.outgoing_conn.items():       
            request_msg = Message(MessageType.REQUEST, self.request_timestamp, self.id, process)
            self.send_message(request_msg)

    def release_resource(self):
        # send back OK message to all waiting in the queue
        self._state = State.DO_NOT_WANT
        print(f"{self.id} released resource")
        for msg in self.incoming_msg_queue:
            self.send_message(Message(MessageType.ACK, time.monotonic, self.id, msg.sender))
    
    # def run(self):
    #     # Process manages its own resources
    #     # - Process timeout
    #     # - CS timeout
    #     while True:
    #         action = None
    #         if self._state == State.DO_NOT_WANT:
    #             self._timer = random.randint(PROC_TIMEOUT_LOWER, self._proc_timeout_upper)
    #             action = random.choice([None, self.request_resource])
    #         elif self._state == State.HELD:
    #             self._timer = random.randint(CS_TIMEOUT_LOWER, self._cs_timeout_upper)
    #             action = self.release_resource

    #         while self._timer:
    #             self.countdown()
    #         action()            


# Only needed to be an independent thread on the ThreadedServer
# Because it blocks when calling server.start() in the Process class
class CommServer(threading.Thread):
    def __init__(self, process, port):
        super(CommServer, self).__init__()
        self.port = port
        self.server = ThreadedServer(Communication(ServerType.SERVER, process), port = self.port)

    def run(self):
        print(f"starting server on port {self.port}")
        self.server.start()

class Communication(rpyc.Service):
    def __init__(self, server_type, process):
        super(Communication, self).__init__()
        self.server_type = server_type
        self.process = process
        self._conn = None
        if self.server_type == ServerType.SERVER:
            print(f"Initializing communication server in {self.process.id}")
        elif self.server_type == ServerType.CLIENT:
            print(f"Initializing communication client in {self.process.id}")
        
    def on_connect(self, conn):
        self._conn = conn
        incomming_conn_id = self._conn.root.get_process_id()        
        print(f"{self.server_type} {self.process.id} accepted connection from {incomming_conn_id}")
    
    def exposed_get_process_id(self):
        return self.process.id

    def exposed_process_message(self, msg_type, timestamp, sender, receiver):
        """
        Only route the message back to the process object.
        Process has the implementation of messaging handling
        """
        print(f"Handling msg {str(msg_type)} from 'Communication' class")        
        # This was causing lock because it triggers communication on the opposite direction
        #sender = self._conn.root.get_process_id()
        self.process.process_incoming_message(Message(MessageType(msg_type), timestamp, sender, receiver))

if __name__=="__main__":
    start_port = 18812
    P_A = Process("A", 18812, 10, 5)
    P_B = Process("B", 18813, 10, 5)
    P_C = Process("C", 18814, 10, 5)

    P_A.start_comms() 
    print("Server A started")
    P_B.start_comms()
    print("Server B started")
    P_C.start_comms()
    print("Server C started")

    
    P_A.connect_to(P_B)
    P_A.connect_to(P_C)

    P_B.connect_to(P_A)
    P_B.connect_to(P_C)    

    P_C.connect_to(P_A)
    P_C.connect_to(P_B)
    time.sleep(1) # wait for communication
    print(f"A connections: {list(P_A.outgoing_conn.keys())}")
    print(f"B connections: {list(P_B.outgoing_conn.keys())}")
    print(f"C connections: {list(P_C.outgoing_conn.keys())}")

    P_A.outgoing_conn['B'].root.process_message(MessageType.TEST.value, time.monotonic(),'A','B')
    P_A.outgoing_conn['C'].root.process_message(MessageType.TEST.value, time.monotonic(),'A','C')
    
    P_B.outgoing_conn['A'].root.process_message(MessageType.TEST.value, time.monotonic(),'B','A')
    P_B.outgoing_conn['C'].root.process_message(MessageType.TEST.value, time.monotonic(),'B','C')

    P_C.outgoing_conn['A'].root.process_message(MessageType.TEST.value, time.monotonic(),'C','A')
    P_C.outgoing_conn['B'].root.process_message(MessageType.TEST.value, time.monotonic(),'C','B')
    time.sleep(1)

    # SIMULATION
    print("### SIMULATION OF A LIST OF REQUEST/RELEASE")

    P_A.request_resource()
    P_B.request_resource()
    P_C.request_resource()
    time.sleep(2)
    P_A.release_resource()
    time.sleep(2)
    P_B.release_resource()

   