import time
from logging import Logger
from queue import PriorityQueue, Empty
from threading import Thread, Lock, current_thread
from typing import TYPE_CHECKING, Optional

from minecraft.networking.packets import ChatPacket

if TYPE_CHECKING:
	from pcrc.pcrc_client import PcrcClient


class ChatPriority:
	Low = 1
	Normal = 0
	High = -1


class Message:
	__id_counter = 0
	__id_counter_lock = Lock()

	def __init__(self, priority, data):
		self.priority = priority
		self.data = data
		with Message.__id_counter_lock:
			self.id = Message.__id_counter + 1
			Message.__id_counter += 1

	def __lt__(self, other):
		if not isinstance(other, type(self)):
			return False
		return self.priority < other.priority or (self.priority == other.priority and self.id < other.id)


class ChatManager:
	def __init__(self, pcrc: 'PcrcClient'):
		self.logger: Logger = pcrc.logger
		self.__pcrc = pcrc
		self.__message_queue = PriorityQueue()
		self.__running = False
		self.__thread: Optional[Thread] = None
		self.__chat_spam_threshold = 0

	def start(self) -> None:
		if self.__thread is not None:
			self.logger.warning('Starting ChatManager again when it\'s running')
			self.stop()
		self.__running = True
		self.__thread = Thread(daemon=True, name='ChatManager', target=self.__run)
		self.__thread.start()

	def stop(self):
		if current_thread() == self.__thread:
			raise RuntimeError('Cannot invoke ChatManager.stop on its chat thread')
		self.__running = False
		if self.__thread is not None:
			self.__thread.join()
		while True:
			try:
				self.__message_queue.get_nowait()
			except Empty:
				break

	def add_chat(self, msg: str, priority: int = ChatPriority.Normal):
		self.logger.debug('Added chat "{}" with priority {} to queue'.format(msg, priority))
		self.__message_queue.put_nowait(Message(priority, msg))

	def __send_chat(self, message: Message):
		text = message.data
		packet = ChatPacket()
		packet.message = text
		self.__pcrc.send_packet(packet)
		self.logger.debug('Sent chat message "{}" to the server'.format(text))
		self.__chat_spam_threshold += 20

	# instant send all chat with priority <= p
	def flush_chats(self, priority: int = ChatPriority.Low):
		while True:
			try:
				msg: Message = self.__message_queue.get_nowait()
			except Empty:
				break
			if msg.priority > priority:
				self.__message_queue.put_nowait(msg)
				break
			self.__send_chat(msg)

	def on_received_TimeUpdatePacket(self):
		self.__chat_spam_threshold -= 20  # 20 gt passed
		if self.__chat_spam_threshold < 0:
			self.__chat_spam_threshold = 0

	def __can_chat(self):
		# vanilla threshold is 200 but I set it to 180 for safety
		return not self.__pcrc.config.get('chat_spam_protect') or self.__chat_spam_threshold + 20 < 180

	def __run(self):
		self.logger.info('Chat thread started')
		while self.__running:
			if self.__can_chat():
				try:
					msg: Message = self.__message_queue.get(timeout=0.01)
				except Empty:
					pass
				else:
					self.__send_chat(msg)
			else:
				time.sleep(0.01)
		self.logger.info('Chat thread stopped')
		self.__thread = None
