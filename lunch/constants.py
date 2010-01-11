
# constants for the slave process
STATE_IDLE = "IDLE" #deprecated
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING" # success
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED" # success
STATE_NOSLAVE = "DEAD" # for master only

# Keys of the messages from the slave :
MESSAGE_MSG = "msg"
MESSAGE_ERROR = "error"
MESSAGE_STATE = "state"
MESSAGE_DIED = "died" # arg: duration in seconds (float)
MESSAGE_STATE = "state"

# answers from the slave :
ANSWER_OK = "OK" # when asking to run a command
ANSWER_BYE = "bye"
#ANSWER_STOPPING = "STOPPING"
#ANSWER_STARTING = "STARTING"
#ANSWER_STATUS = "STATUS"

# Keys of the commands from the master :
COMMAND_QUIT = "quit"
COMMAND_STATUS = "status"
COMMAND_COMMAND = "do" # arg: string
COMMAND_PING = "ping"
COMMAND_START = "run"
COMMAND_ENV = "env" # arg: json dict

