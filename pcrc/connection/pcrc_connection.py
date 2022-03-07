from threading import Lock
from typing import TYPE_CHECKING

from minecraft.networking.connection import Connection, LoginReactor

if TYPE_CHECKING:
	from pcrc.pcrc_client import PcrcClient


class PcrcConnection(Connection):
	def __init__(self, *args, pcrc: 'PcrcClient', **kwargs):
		super().__init__(*args, **kwargs)
		self.pcrc: 'PcrcClient' = pcrc
		self.running_networking_thread = 0
		self.__running_networking_thread_lock = Lock()

	def add_running_networking_thread_amount(self, delta: int):
		with self.__running_networking_thread_lock:
			self.running_networking_thread += delta

	def connect(self):
		super().connect()
		if isinstance(self.reactor, LoginReactor):
			self.pcrc.on_protocol_version_decided(self.allowed_proto_versions.copy().pop())

	def has_running_thread(self):
		return self.running_networking_thread > 0

	__patched = False
