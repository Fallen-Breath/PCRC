import time
# convert file size to MB
from typing import Optional, Callable, Any

from minecraft.networking.types import PositionAndLook


def B2MB(file_size):
	return format(file_size / 1024 / 1024, '.2f')


# convert file size to KB
def B2KB(file_size):
	return format(file_size / 1024, '.2f')


def get_milli_time():
	return int(time.time() * 1000)


def format_pos(pos: PositionAndLook) -> str:
	return '({.2f}, {.2f}, {.2f})'.format(pos.x, pos.y, pos.z)


# Returns a string like h:m for given millis
def format_milli(millis: int) -> str:
	seconds = millis // 1000 % 60
	minutes = millis // (1000 * 60) % 60
	hours = millis // (1000 * 60 * 60)
	return '{:0>2}:{:0>2}:{:0>2}'.format(hours, minutes, seconds)


def chain_callback(*callbacks: Optional[Callable[[], Any]]) -> Callable[[], Any]:
	def callback():
		for cb in callbacks:
			if callable(cb):
				cb()
	return callback
