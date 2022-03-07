from enum import Enum, auto


class ConnectionState(Enum):
	disconnected = auto()
	connecting = auto()
	connected = auto()
	disconnecting = auto()


class RecordingState(Enum):
	stopped = auto()
	recording = auto()
	saving = auto()
