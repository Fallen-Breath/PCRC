import json
import socket
import time
import traceback
from threading import Lock
from typing import Optional, Callable, Any
from urllib.parse import urlparse, parse_qs

from minecraft.networking.packets import Packet, JoinGamePacket
from minecraft.networking.packets.clientbound.play import DisconnectPacket, ChatMessagePacket, TimeUpdatePacket
from pcrc import protocol
from pcrc.config import Config, SettableOptions
from pcrc.connection.pcrc_authentication import PcrcAuthenticationToken
from pcrc.connection.pcrc_connection import PcrcConnection
from pcrc.input import InputManager, StdinInputManager
from pcrc.logger import PcrcLogger
from pcrc.recording.chat import ChatManager, ChatPriority
from pcrc.recording.recorder import Recorder
from pcrc.states import ConnectionState
from pcrc.utils.translation import Translation


class PcrcClient:
	def __init__(self, *, input_manager: Optional[InputManager] = None):
		self.logger: PcrcLogger = PcrcLogger()
		self.config = Config()
		self.translation = Translation()
		self.chat_manager = ChatManager(self)
		self.recorder = Recorder(self)
		self.input_manager = input_manager or StdinInputManager()

		self.logger.set_debug(self.config.get('debug_mode'))

		self.__connection: Optional[PcrcConnection] = None
		self.__connection_state = ConnectionState.disconnected
		self.__flag_stopping = False
		self.__flag_stop_by_user = False
		self.__flag_should_restart = False
		self.mc_protocol: Optional[int] = None
		self.mc_version: Optional[str] = None
		self.player_name: Optional[str] = None
		self.__token = PcrcAuthenticationToken(self.logger)
		self.__start_lock = Lock()

	def tr(self, key: str, *args, **kwargs) -> str:
		return self.translation.translate(key, self.config.get('language')).format(*args, **kwargs)

	def set_config(self, option, value, forced=False):
		if not forced and option not in SettableOptions:
			self.chat(self.tr('chat.illegal_toption_name', option, self.config.get('command_prefix')))
			return
		self.chat(self.tr('chat.option_set', option, value))
		self.config.set_value(option, value)
		self.logger.info('Option <{}> set to <{}>'.format(option, value))

	# ===================
	#    State Getters
	# ===================

	def is_online(self):
		return self.__connection_state in {ConnectionState.connected}

	def connect(self) -> bool:
		success = self.__connect()
		if not success:
			self.__connection_state = ConnectionState.disconnected
		return success

	def __connect(self) -> bool:
		self.__on_connecting()

		token = self.__token
		authenticate_type: str = self.config.get('authenticate_type')
		if authenticate_type == 'offline':
			token = None
			player_name = self.config.get('username')
		elif authenticate_type == 'mojang':
			try:
				token.mojang_authenticate(self.config.get('username'), self.config.get('password'))
			except Exception as e:
				self.logger.error(self.tr('login.mojang.failed', e))
				return False
			player_name = token.profile.name
		elif authenticate_type == 'microsoft':
			if not token.microsoft_refresh_authenticate():
				self.logger.info(self.tr('login.microsoft.url_hint.0'))
				self.logger.info(token.MS_AUTH_URL)
				self.logger.info(self.tr('login.microsoft.url_hint.1'))
				while True:
					user_input = self.input_manager.input(self.tr('login.microsoft.input'))
					queries = parse_qs(urlparse(user_input).query)
					auth_codes = queries.get('code', [])
					if len(auth_codes) != 1:
						self.logger.info(self.tr('login.microsoft.input.invalid'))
					else:
						auth_code = auth_codes[0]
						break
				try:
					token.microsoft_authenticate(auth_code)
				except Exception as e:
					self.logger.error(self.tr('login.microsoft.failed', e))
					return False
			player_name = token.username
		else:
			raise ValueError('Unrecognized authenticate type {}'.format(authenticate_type))

		self.logger.info('Logged in as {} ({})'.format(player_name, authenticate_type))
		self.player_name = player_name

		self.__connection = PcrcConnection(
			pcrc=self,
			address=self.config.get('address'),
			port=self.config.get('port'),
			username=self.config.get('username'),
			auth_token=token,
			initial_version=self.config.get('initial_version'),
			allowed_versions=protocol.SUPPORTED_MINECRAFT_VERSIONS,
			handle_exception=self.on_connection_exception
		)

		if self.is_online():
			self.logger.warning('Cannot connect when connected')
			return False
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
		with self.__start_lock:
			self.logger.info('Starting PCRC')
			if self.is_disconnected():
				return self.connect()
			else:
				self.logger.info('Cannot start PCRC before it disconnects')
				return False

	def stop(self, by_user: bool, *, restart: bool = False, callback: Optional[Callable[[], Any]] = None):
		"""
		:param by_user: If it's stopped by user, connection error due to disconnecting will be suppressed
		:param restart: If PCRC should restart after stopping
		:param callback: The optional callback method to be called after fully stopped
		"""
		if self.__flag_stopping:
			self.logger.warning('PCRC is already stopping')
			return
		self.logger.info('Stopping PCRC, restart = {}, by_user = {}'.format(restart, by_user))
		self.chat(self.tr('chat.stopping'))
		self.__flag_stopping = True
		self.__flag_stop_by_user |= by_user
		self.__flag_should_restart |= restart
		self.recorder.stop_recording(callback or (lambda: ()))

	def restart(self, by_user: bool):
		self.stop(by_user=by_user, restart=True)

	# =======================
	#        Callbacks
	# =======================

	def on_connection_exception(self, exc, exc_info):
		(self.logger.debug if self.has_started_disconnecting() else self.logger.error)('Exception in network thread: {} {}'.format(type(exec), exc))
		if not self.__flag_stop_by_user:
			self.logger.debug(traceback.format_exc())
			self.logger.warning('Stopping the recorder since PCRC has not been stopped by user')
			self.stop(by_user=False, restart=self.config.get('auto_relogin'))

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
		self.__flag_stop_by_user = False
		self.__flag_should_restart = False

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

		if self.__flag_should_restart:
			self.logger.info('---------------------------------------')
			for i in range(3):
				self.logger.info('PCRC restarting in {}s'.format(3 - i))
				time.sleep(1)
			self.start()

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
		self.chat(self.tr('chat.game_join'))

	def on_disconnect_packet(self, packet):
		self.logger.info('PCRC disconnected from the server, reason = {}'.format(packet.json_data))
		self.__connection_state = ConnectionState.disconnected
		self.stop(by_user=False, restart=self.config.get('auto_relogin'))

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
			self.logger.debug('Trying to send chat message ({}) when being offline'.format(message))

	def send_packet(self, packet: Packet):
		if self.is_online():
			self.__connection.write_packet(packet)
		else:
			self.logger.warning('Trying to send packet ({}) when being offline'.format(packet))

	def is_disconnected(self) -> bool:
		return self.__connection_state == ConnectionState.disconnected

	def has_started_disconnecting(self) -> bool:
		return self.__connection_state == ConnectionState.disconnecting or self.is_disconnected()

	def is_fully_stopped(self) -> bool:
		"""
		Disconnected and file saved
		"""
		return self.is_disconnected() and self.recorder.is_stopped() and not self.__flag_should_restart

	def is_running(self) -> bool:
		return not self.is_fully_stopped()
