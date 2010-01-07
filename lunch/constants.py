
# constants for the slave process
STATE_IDLE = "IDLE" 
STATE_STARTING = "STARTING"
STATE_RUNNING = "RUNNING" # success
STATE_STOPPING = "STOPPING"
STATE_STOPPED = "STOPPED" # success
STATE_ERROR = "ERROR"
STATE_SLAVE_DEAD = "DEAD"

# Keys of the messages from the slave :
MESSAGE_MSG = "MSG"
MESSAGE_ERROR = "ERROR"
MESSAGE_LOG = "LOG"
MESSAGE_STATE = "STATE"
MESSAGE_DIED = "DIED" # arg: duration in seconds (float)
MESSAGE_STATE = "STATE"

# answers from the slave :
ANSWER_OK = "OK" # when asking to run a command
ANSWER_QUIT = "BYE"
ANSWER_PONG = "PONG"
ANSWER_STOPPING = "STOPPING"
ANSWER_STARTING = "STARTING"
ANSWER_STATUS = "STATUS"

# Keys of the commands from the master :
COMMAND_QUIT = "quit"
COMMAND_STATUS = "status"
COMMAND_COMMAND = "command" # arg: string
COMMAND_PING = "ping"
COMMAND_START = "run"
COMMAND_ENV = "env" # arg: json dict

