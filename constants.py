import enum

PROC_TIMEOUT_LOWER = 5
CS_TIMEOUT_LOWER = 10

class State(enum.Enum):
    DO_NOT_WANT = 0
    WANTED = 1
    HELD = 2
    
class MessageType(enum.Enum):
    REQUEST = 0
    ACK = 2
    TEST = 3

class ServerType(enum.Enum):
    SERVER = "server"
    CLIENT = "client"