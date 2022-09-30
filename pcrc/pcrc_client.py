import json
import socket
import time
import traceback
from threading import Lock, Event
from typing import Optional, Callable, Any

from minecraft.networking.packets import Packet, JoinGamePacket
from minecraft.networking.packets.clientbound.play import DisconnectPacket, ChatMessagePacket, TimeUpdatePacket
from pcrc import protocol
from pcrc.config import Config, SettableOptions
from pcrc.connection.pcrc_authentication import Authenticator
from pcrc.connection.pcrc_connection import PcrcConnection
from pcrc.input import InputManager, StdinInputManager
from pcrc.logger import PcrcLogger
from pcrc.recording.chat import ChatManager, ChatPriority
from pcrc.recording.recorder import Recorder
from pcrc.states import ConnectionState
from pcrc.utils import misc_util
from pcrc.utils.retry_counter import RetryCounter
from pcrc.utils.translation import Translation


class PcrcClient:
	def __init__(self, *, input_manager: Optional[InputManager] = None):
		self.logger: PcrcLogger = PcrcLogger()
		self.config = Config()
		self.translation = Translation()
		self.chat_manager = ChatManager(self)
		self.recorder = Recorder(self)
		self.input_manager = input_manager or StdinInputManager()
		self.authenticator = Authenticator.get_class(self.config.get('authenticate_type'))(self)
		self.retry_counter = RetryCounter(self.config.get('auto_relogin_attempts'))

		self.logger.set_debug(self.config.get('debug_mode'))

		self.__connection: Optional[PcrcConnection] = None
		self.__connection_state = ConnectionState.disconnected
		self.__flag_stopping = False
		self.__flag_auto_restart: bool = False
		self.mc_protocol: Optional[int] = None
		self.mc_version: Optional[str] = None
		self.player_name: Optional[str] = None
		self.__start_lock = Lock()

	def init(self):
		self.authenticator.init()

	def __del__(self):
		try:
			self.discard()
		except AttributeError:
			pass

	def tr(self, key: str, *args, **kwargs) -> str:
		return self.translation.translate(key, self.config.get('language')).format(*args, **kwargs)

	def set_config_entry(self, option, value, forced=False):
		if not forced and option not in SettableOptions:
			self.chat(self.tr('chat.illegal_option_name', option, self.config.get('command_prefix')))
			return
		self.chat(self.tr('chat.option_set', option, value))
		self.config.set_value(option, value)
		self.logger.info('Option <{}> set to <{}>'.format(option, value))

	def reload_config(self) -> bool:
		self.logger.info('Reloading config')
		try:
			self.config.reload()
		except:
			self.logger.exception('Fail to reload config')
			return False
		else:
			self.__on_config_reload()
			return True

	def __on_config_reload(self):
		# authenticate_type doesn't support hot-reload
		self.retry_counter.set_max_retries(self.config.get('auto_relogin_attempts'))
		self.logger.set_debug(self.config.get('debug_mode'))

	# ===================
	#    State Getters
	# ===================

	def is_online(self):
		return self.__connection_state == ConnectionState.connected

	def is_disconnected(self) -> bool:
		return self.__connection_state == ConnectionState.disconnected

	def has_started_disconnecting(self) -> bool:
		return self.__connection_state in (ConnectionState.disconnecting, ConnectionState.disconnected)

	def is_stopping(self) -> bool:
		return self.__flag_stopping

	def is_fully_stopped(self) -> bool:
		"""
		Disconnected and file saved
		"""
		return self.is_disconnected() and self.recorder.is_stopped() and not self.__flag_auto_restart

	def is_running(self) -> bool:
		return not self.is_fully_stopped()

	def has_authenticated(self) -> bool:
		return self.authenticator.has_authenticated()

	# ===================
	#     Connection
	# ===================

	def connect(self) -> bool:
		success = self.__connect()
		if not success:
			self.__connection_state = ConnectionState.disconnected
		return success

	def __connect(self) -> bool:
		self.__on_connecting()

		if not self.has_authenticated():
			if not self.authenticate():
				return False
		self.player_name = self.authenticator.player_name

		if self.is_online():
			self.logger.warning('Cannot connect when connected')
			return False

		self.__connection = PcrcConnection(
			pcrc=self,
			address=self.config.get('address'),
			port=self.config.get('port'),
			username=self.config.get('username'),
			auth_token=self.authenticator.generate_pycraft_token(),
			initial_version=self.config.get('initial_version'),
			allowed_versions=protocol.SUPPORTED_MINECRAFT_VERSIONS,
			handle_exception=self.on_connection_exception
		)
		try:
			self.__connection_state = ConnectionState.connecting
			self.__connection.connect()
			self.__on_connected()
			return True
		except socket.gaierror:
			self.logger.error('Fail to analyze server address {}'.format(self.config.get('address')))
		except:
			self.logger.error('Fail to connect to {}:{}'.format(self.config.get('address'), self.config.get('port')))
		return False

	def authenticate(self) -> bool:
		auth_type: str = self.config.get('authenticate_type')
		try:
			self.authenticator.authenticate()
		except Exception as e:
			self.logger.error(self.tr('login.failed', auth_type.capitalize(), e))
			return False
		else:
			self.logger.info('Logged in as {} ({})'.format(self.authenticator.player_name, auth_type))
			return True

	def disconnect(self):
		if self.is_online():
			self.chat(self.tr('chat.disconnect'), priority=ChatPriority.High)
			self.chat_manager.flush_chats(ChatPriority.High)
			time.sleep(0.2)  # sleep for a while to make sure the chat packets are sent
		self.__connection_state = ConnectionState.disconnecting
		try:
			self.logger.debug('Disconnecting')
			self.__connection.disconnect()
		except:
			self.logger.error('Failed to disconnect')
			try:
				self.logger.debug('Disconnecting (immediate=True)')
				self.__connection.disconnect(immediate=True)
			except:
				self.logger.error('Failed to immediate disconnect')
		self.__connection_state = ConnectionState.disconnected

	def start(self) -> bool:
		"""
		Starting PCRC by user
		Resets retry counter
		"""
		self.retry_counter.reset_counter()
		return self.__start()

	def __start(self) -> bool:
		"""
		Starting PCRC by itself or by user
		:return:
		"""
		with self.__start_lock:
			self.logger.info('Starting PCRC')
			if self.is_disconnected():
				return self.connect()
			else:
				self.logger.info('Cannot start PCRC before it disconnects')
				return False

	def __stop(self, by_user: bool, *, auto_restart: bool = False, callback: Callable[[], Any]) -> bool:
		"""
		:param auto_restart: If PCRC should try to auto restart (auto_relogin_attempts option will be considered)
		:param callback: The optional callback method to be called after fully stopped
		"""
		if self.__flag_stopping:
			self.logger.warning('PCRC is already stopping')
			traceback.print_stack()
			return False
		self.logger.info('Stopping PCRC, auto restart = {}, by_user = {}'.format(auto_restart, by_user))
		self.chat(self.tr('chat.stopping'))
		self.__flag_stopping = True
		if auto_restart:
			if self.retry_counter.can_retry():
				self.retry_counter.consume_retry_attempt()
				self.__flag_auto_restart = True
			else:
				self.logger.warning('Stopped auto relogin due to maximum retry amount {} reached'.format(self.retry_counter.max_retries))
		self.recorder.stop_recording(callback)
		return True

	def stop(self, callback: Optional[Callable[[], Any]] = None, block: bool = False) -> bool:
		"""
		Stop PCRC by user
		"""
		event = Event()
		callback = misc_util.chain_callback(callback, lambda: event.set())
		executed = self.__stop(by_user=True, callback=callback)
		if executed and block:
			event.wait()
		return executed

	def __stop_by_external_force(self):
		self.__stop(by_user=False, auto_restart=self.config.get('auto_relogin'), callback=lambda: 0)

	def restart(self):
		self.stop(callback=self.__start)

	def interrupt_auto_restart(self):
		self.__flag_auto_restart = False

	def discard(self):
		self.authenticator.interrupt_refresh()

	# =======================
	#        Callbacks
	# =======================

	def on_connection_exception(self, exception: Exception, exc_info):
		log = self.logger.debug if self.has_started_disconnecting() else self.logger.exception
		log('Exception in network thread: {} ({})'.format(exception, getattr(type(exception), '__name__')))
		self.__connection_state = ConnectionState.disconnected
		if not self.has_started_disconnecting():
			self.__stop_by_external_force()

	# called when there's only 1 protocol version in allowed_proto_versions in pycraft connection
	def on_protocol_version_decided(self, protocol_version):
		self.mc_protocol = protocol_version
		self.mc_version = protocol.get_mc_version(protocol_version)
		self.logger.info('Connecting using protocol version {}, mc version = {}'.format(self.mc_protocol, self.mc_version))

	def on_switched_to_playing_reactor(self):
		self.recorder.start_recording()

	def __on_connecting(self):
		self.__connection_state = ConnectionState.logging_in
		self.__flag_stopping = False
		self.__flag_auto_restart = False

	def __on_connected(self):
		self.__connection.register_packet_listener(self.on_packet_received, Packet)
		self.__connection.register_packet_listener(self.on_packet_sent, Packet, outgoing=True)
		self.__connection.register_packet_listener(self.on_game_joined_packet, JoinGamePacket)
		self.__connection.register_packet_listener(self.on_disconnect_packet, DisconnectPacket)
		self.__connection.register_packet_listener(self.on_chat_message_packet, ChatMessagePacket)
		self.__connection.register_packet_listener(lambda p: self.chat_manager.on_received_TimeUpdatePacket(), TimeUpdatePacket)
		self.chat_manager.start()

	def on_fully_stopped(self):
		if self.is_online():
			self.disconnect()

		self.chat_manager.stop()
		while self.__connection.has_running_thread():
			time.sleep(0.001)
		self.__connection = None
		self.mc_version = None
		self.mc_protocol = None
		self.logger.info('PCRC stopped')
		self.logger.info('---------------------------------------')

		if self.__flag_auto_restart:
			for i in range(3):
				self.logger.info('PCRC restarting in {}s'.format(3 - i))
				time.sleep(1)
			if self.__flag_auto_restart:
				self.__start()
			else:
				self.logger.warning('PCRC auto-restart interrupted by user')

	def on_replay_file_saved(self):
		if self.is_online():
			self.logger.info('File operations finished, disconnect now')
			try:
				self.disconnect()
			except Exception as e:
				self.logger.warning('Fail to disconnect: {}'.format(e))
		self.on_fully_stopped()

	# =======================
	#     Packet Listeners
	# =======================

	def on_packet_sent(self, packet: Packet):
		if hasattr(packet, 'raw_data'):
			self.logger.debug('<- {}'.format(packet.raw_data))

	def on_packet_received(self, packet):
		if hasattr(packet, 'raw_data'):
			# self.logger.debug('-> {}'.format(packet.raw_data))
			pass
		self.recorder.on_packet(packet)

	def on_game_joined_packet(self, packet):
		self.logger.info('PCRC bot joined the server')
		self.__connection_state = ConnectionState.connected
		self.retry_counter.reset_counter()
		commands = self.config.get('on_joined_commands')
		if commands is not None and len(commands) > 0:
			for cmd in commands:
				self.chat(cmd)
		self.chat(self.tr('chat.game_join'))

	def on_disconnect_packet(self, packet):
		self.logger.info('PCRC disconnected from the server, reason = {}'.format(packet.json_data))
		self.__connection_state = ConnectionState.disconnected
		self.__stop_by_external_force()

	def on_chat_message_packet(self, packet):
		js = json.loads(packet.json_data)
		self.logger.debug('Message json data = {}'.format(packet.json_data))
		try:
			translate = js['translate']
			msg = js['with'][-1]
			if type(msg) is dict:
				msg = msg['text']  # 1.15.2 server
			message = '({}) '.format(packet.field_string('position'))
			try:
				name = js['with'][0]['insertion']
			except:
				name = None
			if translate == 'chat.type.announcement':  # from server
				message += '[Server] {}'.format(msg)
				self.recorder.on_command(msg, None, None)
			elif translate == 'chat.type.text':  # chat
				message += '<{}> {}'.format(name, msg)
				try:
					uuid = js['with'][0]['hoverEvent']['contents']['id']  # 1.16 server
				except:
					try:
						text = js['with'][0]['hoverEvent']['value']['text']
					except TypeError:  # 1.15.2 server
						text = js['with'][0]['hoverEvent']['value'][0]['text']
					uuid = text[text.find(',id:"'):].split('"')[1]
				self.recorder.on_command(msg, name, uuid)
			elif translate == 'commands.message.display.incoming':  # /tell
				message += '<{}>(tell) {}'.format(name, msg['text'])
			elif translate in ['multiplayer.player.joined', 'multiplayer.player.left']:  # login in/out game
				message += '{} {} the game'.format(name, translate.split('.')[2])
			elif translate == 'chat.type.emote':  # /me
				message += '* {} {}'.format(name, msg)
			else:
				message = packet.json_data
			self.logger.info(message)
		except:
			self.logger.debug('Cannot resolve chat json data: {}'.format(packet.json_data))
			self.logger.debug(traceback.format_exc())
			pass

	def chat(self, message: str, priority: Optional[int] = None):
		if self.is_online():
			for line in message.splitlines():
				if priority is not None:
					self.chat_manager.add_chat(line, priority=priority)
				else:
					self.chat_manager.add_chat(line)
		else:
			self.logger.debug('Trying to send chat message "{}" when being offline'.format(message))

	def send_packet(self, packet: Packet):
		if self.is_online():
			self.__connection.write_packet(packet)
		else:
			self.logger.warning('Trying to send packet {} when being offline'.format(packet))
