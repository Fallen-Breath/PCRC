import datetime
import os
from logging import Logger
from threading import Thread
from typing import TYPE_CHECKING, Any, Optional, Callable

from minecraft.networking.packets import Packet
from minecraft.networking.packets.serverbound.play import ClientStatusPacket
from minecraft.networking.types import PositionAndLook
from pcrc import constant
from pcrc.config import SettableOptions
from pcrc.packets.c2s import SpectatePacket
from pcrc.recording.chat import ChatPriority
from pcrc.recording.packet_processor import PacketProcessor
from pcrc.recording.replay_recording import ReplayRecording
from pcrc.states import RecordingState
from pcrc.utils import packet_util, misc_util

if TYPE_CHECKING:
	from pcrc.pcrc_client import PcrcClient


class Recorder:
	def __init__(self, pcrc: 'PcrcClient'):
		self.pcrc = pcrc
		self.logger: Logger = pcrc.logger
		self.packet_processor = PacketProcessor(self)
		self.__recording_state = RecordingState.stopped

		# recording information
		self.start_time: int = -1
		self.last_player_movement: int = 0
		self.afk_duration: int = 0
		self.last_packet_time: int = 0
		self.last_no_player_movement: Optional[bool] = None
		self.player_uuids = []
		self.file_buffer = bytearray()
		self.last_showinfo_time: int = 0
		self.packet_counter: int = 0
		self.last_showinfo_packet_counter: int = 0
		self.file_name: Optional[str] = None
		self.file_thread: Optional[Thread] = None
		self.replay_file: Optional[ReplayRecording] = None
		self.pos: Optional[PositionAndLook] = None

	@property
	def mc_version(self) -> str:
		return self.pcrc.mc_version

	def chat(self, message: str):
		self.pcrc.chat(message)

	def send_packet(self, packet: Packet):
		return self.pcrc.send_packet(packet)
	
	def get_config(self, key: str) -> Any:
		return self.pcrc.config.get(key)

	def tr(self, key: str, *args, **kwargs) -> str:
		return self.pcrc.tr(key, *args, **kwargs)

	# ===================
	#    Info Getters
	# ===================

	def is_stopped(self):
		return self.__recording_state == RecordingState.stopped

	def is_recording(self):
		return self.__recording_state == RecordingState.recording

	def refresh_player_movement(self, current_time: Optional[int] = None):
		if current_time is None:
			current_time = misc_util.get_milli_time()
		self.last_player_movement = current_time

	def has_no_player_movement(self, current_time: Optional[int] = None):
		if current_time is None:
			current_time = misc_util.get_milli_time()
		return current_time - self.last_player_movement >= self.get_config('delay_before_afk_second') * 1000

	def is_afking(self):
		return self.has_no_player_movement() and self.get_config('with_player_only')

	def get_time_passed(self, current_time: Optional[int] = None):
		if self.start_time < 0:
			return 0
		if current_time is None:
			current_time = misc_util.get_milli_time()
		return current_time - self.start_time

	def get_time_recorded(self, t=None):
		return self.get_time_passed(t) - self.afk_duration

	def get_file_size_limit(self) -> int:
		return self.get_config('file_size_limit_mb') * constant.BYTE_PER_MB

	def get_file_buffer_size(self) -> int:
		return self.get_config('file_buffer_size_mb') * constant.BYTE_PER_MB

	def get_time_recorded_limit(self) -> int:
		return self.get_config('time_recorded_limit_hour') * constant.MILLI_SECOND_PER_HOUR

	# ==========

	def flush(self):
		if len(self.file_buffer) == 0:
			return
		self.replay_file.write_recording_content(self.file_buffer)
		self.logger.info('Flushing {} bytes, uncompressed file size = {}MB now'.format(len(self.file_buffer), misc_util.B2MB(self.replay_file.size)))
		self.file_buffer.clear()

	def write(self, data: bytes):
		self.file_buffer += data
		if len(self.file_buffer) > self.get_file_buffer_size():
			self.flush()

	def start_recording(self):
		if self.pcrc.mc_version is None or self.pcrc.mc_protocol is None:
			raise RuntimeError('Server version information should be gathered when recording starts')
		self.on_recording_start()

	def stop_recording(self, callback: Callable[[], Any]):
		"""
		The returned Event indicates if the replay recording saving operation is done
		"""
		self.logger.info('Stop recording')
		self.__recording_state = RecordingState.saving
		if self.file_thread is None:
			self.file_thread = Thread(name='ReplaySaver', target=self.__create_replay_file, args=(callback, ))
			self.file_thread.setDaemon(True)
			self.file_thread.start()
		else:
			raise RuntimeError('Stop recording twice')

	def on_recording_start(self):
		self.__recording_state = RecordingState.recording
		self.start_time = misc_util.get_milli_time()
		self.last_player_movement = self.start_time
		self.afk_duration = 0
		self.last_packet_time = self.start_time
		self.last_no_player_movement = None
		self.player_uuids.clear()
		self.file_buffer.clear()
		self.last_showinfo_time = 0
		self.packet_counter = 0
		self.last_showinfo_packet_counter = 0
		self.file_thread = None
		self.replay_file = ReplayRecording(temp_file_dir=self.get_config('recording_temp_file_directory'))
		self.pos = None
		self.packet_processor.reset()

	def on_replay_file_saved(self):
		self.__recording_state = RecordingState.stopped
		self.start_time = -1
		self.file_thread = None
		self.replay_file = None
		self.pcrc.on_replay_file_saved()

	def __create_replay_file(self, callback: Callable):
		try:
			self.flush()

			if self.pcrc.mc_version is None or self.pcrc.mc_protocol is None:
				self.logger.warning('Not connected to the server yet, abort creating replay recording file')
				return

			if self.replay_file is None:
				self.logger.warning('Recording has not started yet, abort creating replay recording file')
				return

			if self.replay_file.size < constant.MINIMUM_LEGAL_FILE_SIZE:
				self.logger.warning('Size of "recording.tmcpr" too small ({}KB < {}KB), abort creating replay file'.format(
					misc_util.B2KB(self.replay_file.size), misc_util.B2KB(constant.MINIMUM_LEGAL_FILE_SIZE)
				))
				return

			# Creating .mcpr zipfile based on timestamp
			self.logger.info('Time recorded/passed: {}/{}'.format(misc_util.format_milli(self.get_time_recorded()), misc_util.format_milli(self.get_time_passed())))

			# Deciding file name
			file_name_raw = self.file_name or datetime.datetime.today().strftime('PCRC_%Y_%m_%d_%H_%M_%S')
			file_name = file_name_raw + '.mcpr'
			counter = 2
			while True:
				file_path = os.path.join(self.get_config('recording_storage_directory'), file_name)
				if not os.path.isfile(file_path):
					break
				file_name = '{}_{}.mcpr'.format(file_name_raw, counter)
				counter += 1
			self.logger.info('Creating "{}"'.format(file_path))
			self.pcrc.chat(self.tr('chat.creating_recording_file'))

			self.replay_file.set_meta_data(
				server_name=self.get_config('server_name'),
				duration=self.get_time_recorded(),
				date=misc_util.get_milli_time(),
				mc_version=self.pcrc.mc_version,
				protocol=self.pcrc.mc_protocol,
				player_uuids=self.player_uuids
			)
			self.replay_file.create_replay_recording(file_path)

			self.logger.info('Size of replay file "{}": {}MB'.format(file_path, misc_util.B2MB(os.path.getsize(file_path))))
			self.pcrc.chat(self.tr('chat.created_recording_file', file_name), priority=ChatPriority.High)
		finally:
			self.on_replay_file_saved()
			callback()

	def on_packet(self, packet: Packet):
		if not self.is_recording():
			return
		content: bytes = getattr(packet, 'raw_data')
		if content is None:
			return
		if content[0] == 0x00:
			content = content[1:]

		packet_name = type(packet).__name__
		current_time = misc_util.get_milli_time()

		should_record_this, processed_content = self.packet_processor.process(packet, current_time)
		if processed_content is not None:
			content = processed_content
			self.logger.debug('Modified packet {}'.format(packet_name))

		# Increase afk timer when recording stopped, afk timer prevents afk time in replays
		if self.get_config('with_player_only'):
			no_player_movement: bool = self.has_no_player_movement(current_time)
			if no_player_movement:
				self.afk_duration += current_time - self.last_packet_time
			if self.last_no_player_movement != no_player_movement:
				self.pcrc.chat(self.tr('chat.pause_recording') if no_player_movement else self.tr('chat.continue_recording'))
			self.last_no_player_movement = no_player_movement
		self.last_packet_time = current_time

		# Recording
		if should_record_this:
			if not self.is_afking() or packet_util.is_important(packet) or self.get_config('record_packets_when_afk'):
				data = self.get_time_recorded().to_bytes(4, byteorder='big', signed=True)
				data += len(content).to_bytes(4, byteorder='big', signed=True)
				data += content
				self.write(data)
				self.packet_counter += 1
				if self.is_afking() and packet_util.is_important(packet):
					self.logger.debug('PCRC is afking but {} is an important packet so PCRC recorded it'.format(packet_name))
				else:
					if self.get_config('debug_packet'):
						self.logger.debug('{} recorded'.format(packet_name))
			else:
				self.logger.debug('{} ignore due to being afk'.format(packet_name))

		if self.replay_file.size > self.get_file_size_limit():
			self.logger.info('tmcpr file size limit {}MB reached! Restarting'.format(misc_util.B2MB(self.get_file_size_limit())))
			self.pcrc.chat(self.tr('chat.reached_file_size_limit', misc_util.B2MB(self.get_file_size_limit())))
			self.pcrc.restart()

		if self.get_time_recorded(current_time) > self.get_time_recorded_limit():
			self.logger.info('{} actual recording time reached!'.format(misc_util.format_milli(self.get_time_recorded_limit())))
			self.pcrc.chat(self.tr('chat.reached_time_limit', misc_util.format_milli(self.get_time_recorded_limit())))
			self.pcrc.restart()

		def get_showinfo_time():
			return int(self.get_time_passed(current_time) / (5 * 60 * 1000))

		# Log information in console
		if get_showinfo_time() != self.last_showinfo_time or self.packet_counter - self.last_showinfo_packet_counter >= 100000:
			self.last_showinfo_time = get_showinfo_time()
			self.last_showinfo_packet_counter = self.packet_counter
			self.logger.info('Recorded/Passed: {}/{}; Packet count: {}'.format(
				misc_util.format_milli(self.get_time_recorded(current_time)), misc_util.format_milli(self.get_time_passed(current_time)), self.packet_counter)
			)

	def get_status(self) -> str:
		"""
		Will be a multi-line string
		"""
		return self.tr(
			'chat.command.status',
			self.is_recording(), self.is_recording() and not self.is_afking(),
			misc_util.format_milli(self.get_time_recorded()), misc_util.format_milli(self.get_time_passed()),
			self.packet_counter, misc_util.B2MB(len(self.file_buffer)), misc_util.B2MB(self.replay_file.size) if self.replay_file is not None else '-1',
			self.file_name
		)

	def on_command(self, command: str, player_name: Optional[str], player_uuid: Optional[str]):
		if player_name == self.pcrc.player_name:
			return
		try:
			whitelist = self.get_config('whitelist')
			wl_isenabled = self.get_config('enabled')
			args = command.split(' ')  # !!PCRC <> <> <> <>
			self.logger.info('Processing Command {} from {} {}'.format(args, player_name, player_uuid))
			if len(args) == 0 or args[0] != self.get_config('command_prefix'):
				return
			elif wl_isenabled and player_name is not None and player_name not in whitelist:
				self.chat(self.tr('chat.command.permission_denied'))
				return
			elif len(args) == 1:
				self.chat(self.tr('chat.command.help', self.get_config('command_prefix')))
			elif len(args) == 2 and args[1] == 'status':
				self.chat(self.get_status())
			elif len(args) == 2 and args[1] in ['spectate', 'spec'] and player_name is not None and player_uuid is not None:
				self.chat(self.tr('chat.command.spectate', player_name, player_uuid))
				self.spectate(player_uuid)
			elif len(args) == 2 and args[1] == 'here':
				self.chat('!!here')
			elif len(args) == 2 and args[1] in ['where', 'location', 'loc', 'position', 'pos']:
				if self.pos is not None:
					self.chat(self.tr('chat.command.position', misc_util.format_pos(self.pos)))
				else:
					self.chat(self.tr('chat.command.position.unknown'))
			elif len(args) == 2 and args[1] in ['stop']:
				self.pcrc.stop()
			elif len(args) == 2 and args[1] == 'restart':
				self.pcrc.restart()
			elif len(args) == 4 and args[1] == 'set':
				self.pcrc.set_config_entry(args[2], args[3])
			elif len(args) == 2 and args[1] == 'set':
				self.chat(self.tr('chat.command.set.title'))
				self.chat(', '.join(SettableOptions))
			elif (len(args) == 2 and args[1] == 'marker') or (len(args) == 3 and args[1] == 'marker' and args[2] == 'list'):
				self.print_markers()
			elif 3 <= len(args) <= 4 and args[1] == 'marker' and args[2] == 'add':
				self.add_marker(None if len(args) == 3 else args[3])
			elif len(args) == 4 and args[1] == 'marker' and args[2] in ['del', 'delete']:
				try:
					index = int(args[3])
				except ValueError:
					self.chat(self.tr('chat.command.wrong_argument'))
				else:
					if 1 <= index <= len(self.replay_file.markers):
						self.delete_marker(index)
					else:
						self.chat(self.tr('chat.command.wrong_argument'))
			elif len(args) == 3 and args[1] == 'name':
				self.set_file_name(args[2])
			elif len(args) == 2 and args[1] == 'respawn':
				self.respawn()
			else:
				self.chat(self.tr('chat.command.unknown', self.get_config('command_prefix')))
		except:
			self.logger.exception('Error when processing command "{}"'.format(command))

	def spectate(self, uuid):
		self.logger.info('Spectating to entity(uuid = {})'.format(uuid))
		packet = SpectatePacket()
		packet.target = uuid
		self.send_packet(packet)

	def respawn(self):
		self.logger.info('Respawning...')
		packet = ClientStatusPacket()
		packet.action_id = ClientStatusPacket.RESPAWN
		self.send_packet(packet)

	def set_file_name(self, new_name):
		old_name = self.file_name
		self.chat(self.tr('chat.command.name', new_name))
		self.file_name = new_name
		self.logger.info('File name is setting from {} to {}'.format(old_name, new_name))

	def print_markers(self):
		if len(self.replay_file.markers) == 0:
			self.pcrc.chat(self.tr('chat.command.marker.no_marker'))
		else:
			self.pcrc.chat(self.tr('chat.command.marker.list_title'))
			for i in range(len(self.replay_file.markers)):
				name = self.replay_file.markers[i]['value']['name'] if 'name' in self.replay_file.markers[i]['value'] else ''
				self.pcrc.chat('{}. {} {}'.format(i + 1, misc_util.format_milli(self.replay_file.markers[i]['realTimestamp']), name))

	def add_marker(self, name=None):
		if self.pos is None:
			self.logger.warning('Fail to add marker, position unknown!')
			return
		time_stamp = self.get_time_recorded()
		marker = self.replay_file.add_marker(self.get_time_recorded(), self.pos, name)
		self.pcrc.chat(self.tr('chat.command.marker.add', misc_util.format_milli(time_stamp)))
		self.logger.info('Marker added: {}, {} markers has been stored'.format(marker, len(self.replay_file.markers)))

	def delete_marker(self, index):
		marker = self.replay_file.pop_marker(index - 1)
		self.pcrc.chat(self.tr('chat.command.marker.delete', misc_util.format_milli(marker['realTimestamp'])))
		self.logger.info('Marker deleted: {}, {} markers has been stored'.format(marker, len(self.replay_file.markers)))
