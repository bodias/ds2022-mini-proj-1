import signal
import sys
import time
import threading
import enum
#from Queue import Queue
#import Queue
from multiprocessing import Queue
initially_granted_proc = "A"
procs = {"A", "B", "C"}
resource_usage_counts = {"A": 0, "B": 0, "C": 0}
message_queues = {"A" : Queue(), "B": Queue(), "C": Queue()}

class State(enum.Enum):
    DO_NOT_WANT = 0
    WANTED = 1
    HELD = 2

class MessageType(enum.Enum):
    REQUEST = 0
    RELEASE = 1
    ACK = 2

class Message(object):
    def __init__(self, msg_type, timestamp, sender, receiver):
        self.msg_type = msg_type
        self.timestamp = timestamp
        self.sender = sender
        self.receiver = receiver

    def __repr__(self):
        return "Message {} at {} from {} to {}".format(
        	self.msg_type, self.timestamp, 
        	self.sender, self.receiver)

class Process(threading.Thread):

    def __init__(self, name, process_timeout, cs_timeout, other_processes):
        super(Process, self).__init__()
        self.name = name
        self.state = State.DO_NOT_WANT        
        self.other_processes = other_processes
        self.lamport_clock = 0 # tick after each "event"
        self.request_queue = []
        # self.request_queue.append(Message("request", 
        # 	-1, initially_granted, initially_granted))
        self.cs_request_timestamp = -1        
        self.cs_request_status = {proc: False for proc in self.other_processes}
        self.process_timeout = process_timeout
        self.cs_timeout = cs_timeout

    # def remove_request(self, msg_type, sender):
    #     index_of_req = -1
    #     for i in range(len(self.request_queue)):
    #         if self.request_queue[i].msg_type == msg_type and \
    #            self.request_queue[i].sender == sender:
    #             index_of_req = i
    #             break
    #     if i == -1:
    #         print("Unable to remove") 
    #     else:
    #         del self.request_queue[i]

    # def use_resource(self):
    #     print("Process {} is using resource".format(self.name))
    #     resource_usage_counts[self.name] += 1
    #     time.sleep(2)
    
    def request_resource(self):
        # send request message to all other process (broadcast)     
        self.request_timestamp = self.lamport_clock 
        for process in self.other_processes:       
            request_msg = Message(MessageType.REQUEST, self.lamport_clock, self.name, process.name)
            self.lamport_clock += 1
            message_queues[process.name].put(request_msg)
            self.cs_request_status[process.name] = False

    def release_resource(self):
        # send back OK message to all waiting in the queue
        for msg in self.request_queue:
            self.process_message(msg)

    def process_message(self, msg):
        # Based on msg_type handle appropriately
        if msg.msg_type == MessageType.REQUEST:
            # 1. receiver is not accessing the resource and doesn't want to access it
            #   OUTCOME: Send OK to back to sender
            if self.state == State.DO_NOT_WANT:
                ack_message = Message(MessageType.ACK, self.lamport_clock, self.name, msg.sender)
                message_queues[msg.sender].put(ack_message)
            # 2. Receiver already has access to the resource
            #   OUTCOME: Don't reply, queue the request
            elif self.state == State.HELD:
                self.request_queue.append(msg)
            # 3. Receiver is on the waiting list. Compare timestamps, lowest wins.
            #   OUTCOME: 
            #       If OWN timestamp > request Timestamp (current process loses), then send back OK
            #       Otherwise receiver queues incoming request and send nothing back
            elif self.state == State.WANTED:
                if self.request_timestamp > msg.timestamp:
                    ack_message = Message(MessageType.ACK, self.lamport_clock, self.name, msg.sender)
                    message_queues[msg.sender].put(ack_message)
                else:
                    self.request_queue.append(msg)

        elif msg.msg_type == MessageType.ACK:        
            # change status of the CS request    
            self.cs_request_status[msg.sended] = True
        else:
            print("Unknown message type")

    def check_available(self):
        # checks if all processes sent back OK
        for process, status in self.cs_request_status.items():
            if status == False:
                return False
        return True
        

    def run(self):
        seconds_passed = 0
        while True:

            if self.state == State.DO_NOT_WANT:
                # Process time outs and change the process state
                if seconds_passed > self.process_timeout:
                    # Change process state and reset timeout
                    self.state = State.WANTED                
                    seconds_passed = 0
                    # Request resource
                    print(f"Process {self.name} requesting resource")
                    self.request_resource()
                else:
                    pass
            
            # Want to get the resource, check if it has all acks
            # There is no timout for this state 
            elif self.state == State.WANTED:
                # check if CS is available
                if self.check_available():
                    # Hold the resource until cs_timeout
                    print(f"CS available, {self.name} now is using resource")
                    self.state = State.HELD
                else:
                    pass

            elif self.state == State.HELD:
                if seconds_passed > self.cs_timeout:
                    # Release CS
                    print(f"CS released by {self.name} after CS timeout")
                    self.state = State.DO_NOT_WANT
                    self.release_resource()
                else:
                    pass

            # do communication with others     
            # TODO: current implementation reads one message from queue per second
            #       perhaps messages should be read all at once emptying the queue?               
            msg = message_queues[self.name].get(block=True)        
            # Got a message, check if the timestamp 
            # is greater than our clock, if so advance it
            # TODO : Check if this feature is needed (updating own clock based on lamport)
            if msg.timestamp >= self.lamport_clock:
                self.lamport_clock = msg.timestamp + 1
            print("Got message {}".format(msg))
            self.process_message(msg)
            self.lamport_clock += 1

            seconds_passed += 1
            time.sleep(1)

if __name__=="__main__":
    # TODO: draw timeouts from interval
    process_timeout = 5
    cs_timeout = 10

    t1 = Process("A", process_timeout, cs_timeout, list(procs - set("A")))
    t2 = Process("B", process_timeout, cs_timeout, list(procs - set("B")))
    t3 = Process("C", process_timeout, cs_timeout, list(procs - set("C")))

    # Daemonizing threads means that if main thread dies, so do they. 
    # That way the process will exit if the main thread is killed.
    t1.setDaemon(True)
    t2.setDaemon(True)
    t3.setDaemon(True)

    try:
        t1.start()
        t2.start()
        t3.start()
        while True:
            # Need some arbitrary timeout here, seems a bit hackish. 
            # If we don't do this then the main thread will just block 
            # forever waiting for the threads to return and the 
            # keyboardinterrupt never gets hit. Interestingly regardless of the 
            # timeout, the keyboard interrupt still occurs immediately 
            # upon ctrl-c'ing
            t1.join(10)
            t2.join(10)
            t3.join(10)
    except KeyboardInterrupt:
        print("Ctrl-c pressed")
        sys.exit(1)