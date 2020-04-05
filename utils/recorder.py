# coding: utf8
import copy
import heapq
import os
import shutil
import socket
import threading
import time
import json
import traceback
import datetime
import subprocess

from . import config, utils
from .replay_file import ReplayFile
from .translation import Translation
from .logger import Logger
from .pycraft import authentication
from .pycraft.networking.connection import Connection
from .pycraft.networking.packets import Packet as PycraftPacket, clientbound, serverbound
from .SARC.packet import Packet as SARCPacket
from .pycraft.networking.types import PositionAndLook


class Recorder:
	socket_id = None

	def __init__(self, config_file, translation_folder):

		self.config = config.Config(config_file)
		self.translations = Translation(translation_folder)
		self.working = False
		self.online = False
		self.stop_by_user = False  # set to true once PCRC is stopped by user; reset to false when PCRC starts
		self.file_thread = None
		self.chat_thread = None
		self.file_buffer = bytearray()
		self.replay_file = None
		self.file_name = None
		self.file_urls = []
		self.mc_version = None
		self.mc_protocol = None
		self.logger = Logger(name='PCRC-Recorder', display_debug=self.config.get('debug_mode'))
		self.print_config()

		if not self.config.get('online_mode'):
			self.logger.log("Login in offline mode")
			self.connection = Connection(self.config.get('address'), self.config.get('port'), username=self.config.get('username'),
				recorder=self, allowed_versions=utils.ALLOWED_VERSIONS, handle_exception=self.onConnectionException
			)
		else:
			self.logger.log("Login in online mode")
			auth_token = authentication.AuthenticationToken()
			auth_token.authenticate(self.config.get('username'), self.config.get('password'))
			self.logger.log("Logged in as %s" % auth_token.profile.name)
			self.config.set_value('username', auth_token.profile.name)
			self.connection = Connection(self.config.get('address'), self.config.get('port'),
				auth_token=auth_token, recorder=self, allowed_versions=utils.ALLOWED_VERSIONS, handle_exception=self.onConnectionException
			)

		self.connection.register_packet_listener(self.onPacketReceived, PycraftPacket)
		self.connection.register_packet_listener(self.onPacketSent, PycraftPacket, outgoing=True)
		self.connection.register_packet_listener(self.onGameJoin, clientbound.play.JoinGamePacket)
		self.connection.register_packet_listener(self.onDisconnect, clientbound.play.DisconnectPacket)
		self.connection.register_packet_listener(self.onChatMessage, clientbound.play.ChatMessagePacket)
		self.connection.register_packet_listener(self.onPlayerPositionAndLook, clientbound.play.PlayerPositionAndLookPacket)

		self.protocolMap = {}
		self.logger.log('init finish')

	def translation(self, text):
		return self.translations.translate(text, self.config.get('language'))

	def print_config(self):
		messages = self.config.display().splitlines()
		for message in messages:
			self.logger.log(message)

	def is_online(self):
		return self.online

	def is_working(self):
		return self.working

	def onConnectionException(self, exc, exc_info):
		self.logger.error('Exception in network thread: {}'.format(exc))
		self.logger.debug(traceback.format_exc())
		if not self.stop_by_user:
			self.logger.error('Stopping the recorder since PCRC has not been stopped by user')
			self.stop(restart=self.config.get('auto_relogin'))
		else:
			self.logger.log("Don't panic, that's Works As Intended")

	def onPacketSent(self, packet):
		self.logger.debug('<- {}'.format(packet.data))

	def onPacketReceived(self, packet):
	#	self.logger.debug('-> {}'.format(packet.data))
		self.processPacketData(packet)

	def onGameJoin(self, packet):
		self.logger.log('PCRC bot joined the server')
		self.online = True
		self.chat(self.translation('OnGameJoin'))

	def onDisconnect(self, packet):
		self.logger.log('PCRC disconnected from the server, reason = {}'.format(packet.json_data))
		self.online = False
		if self.is_working():
			self.stop(restart=self.config.get('auto_relogin'))
		self.chat_thread.kill()

	def onChatMessage(self, packet):
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
				self.processCommand(msg, None, None)
			elif translate == 'chat.type.text':  # chat
				message += '<{}> {}'.format(name, msg)
				try:
					text = js['with'][0]['hoverEvent']['value']['text']
				except TypeError:  # 1.15.2 server
					text = js['with'][0]['hoverEvent']['value'][0]['text']
				uuid = text[text.find(',id:"'):].split('"')[1]
				self.processCommand(msg, name, uuid)
			elif translate == 'commands.message.display.incoming':  # tell
				message += '<{}>(tell) {}'.format(name, msg['text'])
			elif translate in ['multiplayer.player.joined', 'multiplayer.player.left']:  # login in/out game
				message += '{} {} the game'.format(name, translate.split('.')[2])
			elif translate == 'chat.type.emote':  # me
				message += '* {} {}'.format(name, msg)
			else:
				message = packet.json_data
			self.logger.log(message, do_print=False)
		except:
			self.logger.debug('Cannot resolve chat json data: {}'.format(packet.json_data))
			self.logger.debug(traceback.format_exc())
			pass

	def onPlayerPositionAndLook(self, packet):
		self.updatePlayerMovement()

	def connect(self):
		if self.is_online():
			self.logger.warn('Cannot connect when connected')
			return
		success = False
		try:
			self.connection.connect()
			success = True
		except socket.gaierror:
			self.logger.error('Fail to analyze server address "{}"'.format(self.config.get('address')))
		except ConnectionRefusedError:
			self.logger.error('Fail to connect to "{}:{}"'.format(self.config.get('address'), self.config.get('port')))
		except Exception:
			self.logger.error(traceback.format_exc())

		return success

	def disconnect(self):
		if self.is_online():
			if len(self.file_urls) > 0:
				self.print_urls()
			self.chat(self.translation('OnDisconnect'), priority=ChatThread.Priority.High)
			self.chat_thread.flush_pending_chat(ChatThread.Priority.High)
		self.connection.disconnect()
		self.online = False

	def updatePlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		self.last_player_movement = t

	def noPlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return t - self.last_player_movement >= self.config.get('delay_before_afk_second') * 1000

	def isAFKing(self):
		return self.noPlayerMovement() and self.config.get('with_player_only')

	def timePassed(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return t - self.start_time

	def timeRecorded(self, t=None):
		return self.timePassed(t) - self.afk_time

	def file_size_limit(self):
		return self.config.get('file_size_limit_mb') * utils.BytePerMB

	def file_buffer_size(self):
		return self.config.get('file_buffer_size_mb') * utils.BytePerMB

	def time_recorded_limit(self):
		return self.config.get('time_recorded_limit_hour') * utils.MilliSecondPerHour

	def processPacketData(self, packet_raw):
		if not self.is_working():
			return
		bytes = packet_raw.data
		if bytes[0] == 0x00:
			bytes = bytes[1:]
		t = utils.getMilliTime()
		packet_length = len(bytes)

		packet = SARCPacket()
		packet.receive(bytes)
		packet_id, packet_name = self.packet_processor.analyze(packet)
		packet_recorded = self.packet_processor.process(packet)

		# Increase afk timer when recording stopped, afk timer prevents afk time in replays
		if self.config.get('with_player_only'):
			noPlayerMovement = self.noPlayerMovement(t)
			if noPlayerMovement:
				self.afk_time += t - self.last_t
			if self.last_no_player_movement != noPlayerMovement:
				msg = self.translation('RecordingPause') if self.isAFKing() else self.translation('RecordingContinue')
				self.chat(msg)
			self.last_no_player_movement = noPlayerMovement
		self.last_t = t

		# Recording
		if self.is_working() and packet_recorded is not None:
			if not self.isAFKing() or packet_name in utils.IMPORTANT_PACKETS or self.config.get('record_packets_when_afk'):
				bytes_recorded = packet_recorded.read(packet_recorded.remaining())
				data = self.timeRecorded().to_bytes(4, byteorder='big', signed=True)
				data += len(bytes_recorded).to_bytes(4, byteorder='big', signed=True)
				data += bytes_recorded
				self.write(data)
				self.packet_counter += 1
				if self.isAFKing() and packet_name in utils.IMPORTANT_PACKETS:
					self.logger.debug('PCRC is afking but {} is an important packet so PCRC recorded it'.format(packet_name))
				else:
					self.logger.debug('{} packet recorded'.format(packet_name))
			else:
				self.logger.debug('{} packet ignore due to being afk'.format(packet_name))
		else:
			self.logger.debug('{} packet ignore'.format(packet_name))
			pass

		if self.is_working() and self.replay_file.size() > self.file_size_limit():
			self.logger.log('tmcpr file size limit {}MB reached! Restarting'.format(utils.convert_file_size_MB(self.file_size_limit())))
			self.chat(self.translation('OnReachFileSizeLimit').format(utils.convert_file_size_MB(self.file_size_limit())))
			self.restart()

		if self.is_working() and self.timeRecorded(t) > self.time_recorded_limit():
			self.logger.log('{} actual recording time reached!'.format(utils.convert_millis(self.time_recorded_limit())))
			self.chat(self.translation('OnReachTimeLimit').format(utils.convert_millis(self.time_recorded_limit())))
			self.restart()

		def get_showinfo_time():
			return int(self.timePassed(t) / (5 * 60 * 1000))

		# Log information in console
		if get_showinfo_time()!= self.last_showinfo_time or self.packet_counter - self.last_showinfo_packetcounter >= 100000:
			self.last_showinfo_time = get_showinfo_time()
			self.last_showinfo_packetcounter = self.packet_counter
			self.logger.log('Recorded/Passed: {}/{}; Packet count: {}'.format(
				utils.convert_millis(self.timeRecorded(t)), utils.convert_millis(self.timePassed(t)), self.packet_counter)
			)

	def flush(self):
		if len(self.file_buffer) == 0:
			return
		self.replay_file.write(self.file_buffer)
		self.logger.log('Flushing {} bytes to "recording.tmcpr" file, file size = {}MB now'.format(
			len(self.file_buffer), utils.convert_file_size_MB(self.replay_file.size())
		))
		self.file_buffer = bytearray()

	def write(self, data):
		self.file_buffer += data
		if len(self.file_buffer) > self.file_buffer_size():
			self.flush()

	# Start & Stop stuffs

	def is_stopped(self):
		return not self.is_working() and not self.is_online() and self.file_thread is None and self.connection.running_networking_thread == 0

	def start(self):
		if not self.is_stopped():
			return
		self.logger.log('Starting PCRC')
		self.stop_by_user = False
		success = self.connect()
		if not success:
			self.stop(restart=self.config.get('auto_relogin'))
		return success

	# called when pycraft connection switch to PlayingReactor
	def start_recording(self):
		assert self.mc_protocol is not None and self.mc_version is not None
		self.logger.log('Connected to the server, start recording')
		self.packet_processor = PacketProcessor(self, self.mc_version)
		self.on_recording_start()

	# called when there's only 1 protocol version in allowed_proto_versions in pycraft connection
	def on_protocol_version_decided(self, protocol_version):
		self.mc_protocol = protocol_version
		self.mc_version = utils.Map_ProtocolToVersion[protocol_version]
		self.logger.log('Connecting using protocol version {}, mc version = {}'.format(self.mc_protocol, self.mc_version))
		# as a MCDR plugin
		with open(utils.get_path('protocol.json'), 'r') as f:
			self.protocolMap = json.load(f)[str(protocol_version)]['Clientbound']

	# initializing stuffs
	def on_recording_start(self):
		self.working = True
		self.start_time = utils.getMilliTime()
		self.last_player_movement = self.start_time
		self.afk_time = 0
		self.last_t = 0
		self.last_no_player_movement = False
		self.player_uuids = []
		self.file_buffer = bytearray()
		self.last_showinfo_time = 0
		self.packet_counter = 0
		self.last_showinfo_packetcounter = 0
		self.file_thread = None
		self.replay_file = ReplayFile(path=utils.RecordingFilePath)
		self.pos = None
		if self.chat_thread is not None:
			self.chat_thread.kill()
		self.chat_thread = ChatThread(self)
		self.chat_thread.start()
		if 'Time Update' in utils.BAD_PACKETS:
			utils.BAD_PACKETS.remove('Time Update')

	def stop(self, restart=False, by_user=False):
		self.logger.log('Stopping PCRC, restart = {}, by_user = {}'.format(restart, by_user))
		if self.is_online():
			self.chat(self.translation('OnPCRCStopping'))
		if by_user:
			self.stop_by_user = True
		self.working = False
		self.createReplayFile(restart)
		return True

	def restart(self, by_user=False):
		self.stop(restart=True, by_user=by_user)

	def createReplayFile(self, restart):
		if self.file_thread is not None:
			return
		self.file_thread = threading.Thread(target=self._createReplayFile, args=(restart, ))
		self.file_thread.setDaemon(True)
		self.file_thread.start()

	def _createReplayFile(self, restart):
		logger = copy.deepcopy(self.logger)
		logger.thread = 'File'
		try:
			self.__createReplayFile(logger)
		except AttributeError:
			logger.log('Recorder has not started up, aborted creating replay file')
			logger.debug(traceback.format_exc())
		finally:
			self.on_final_stop(logger, restart)

	def __createReplayFile(self, logger):
		self.flush()

		if self.mc_version is None or self.mc_protocol is None:
			logger.log('Not connected to the server yet, abort creating replay recording file')
			return

		if self.replay_file is None:
			logger.log('Recording has not started yet, abort creating replay recording file')
			return

		if self.replay_file.size() < utils.MinimumLegalFileSize:
			logger.warn('Size of "recording.tmcpr" too small ({}KB < {}KB), abort creating replay file'.format(
				utils.convert_file_size_KB(self.replay_file.size()), utils.convert_file_size_KB(utils.MinimumLegalFileSize)
			))
			return

		# Creating .mcpr zipfile based on timestamp
		logger.log('Time recorded/passed: {}/{}'.format(utils.convert_millis(self.timeRecorded()), utils.convert_millis(self.timePassed())))

		# Deciding file name
		if not os.path.exists(utils.RecordingStorageFolder):
			os.makedirs(utils.RecordingStorageFolder)
		file_name_raw = datetime.datetime.today().strftime('PCRC_%Y_%m_%d_%H_%M_%S')
		if self.file_name is not None:
			file_name_raw = self.file_name
		file_name = file_name_raw + '.mcpr'
		counter = 2
		while os.path.isfile(f'{utils.RecordingStorageFolder}{file_name}'):
			file_name = f'{file_name_raw}_{counter}.mcpr'
			counter += 1
		logger.log('File name is set to "{}"'.format(file_name))

		logger.log('Creating "{}"'.format(file_name))
		if self.is_online():
			self.chat(self.translation('OnCreatingMCPRFile'))

		self.replay_file.set_meta_data(utils.get_meta_data(
			server_name=self.config.get('server_name'),
			duration=self.timeRecorded(),
			date=utils.getMilliTime(),
			mcversion=self.mc_version,
			protocol=self.mc_protocol,
			player_uuids=self.player_uuids
		))
		self.replay_file.create(file_name)

		logger.log('Size of replay file "{}": {}MB'.format(file_name, utils.convert_file_size_MB(os.path.getsize(file_name))))
		file_path = f'{utils.RecordingStorageFolder}{file_name}'
		shutil.move(file_name, file_path)
		if self.is_online():
			self.chat(self.translation('OnCreatedMCPRFile').format(file_name), priority=ChatThread.Priority.High)

		if self.config.get('upload_file'):
			if self.is_online():
				self.chat(self.translation('OnUploadingMCPRFile'))
			logger.log('Uploading "{}" to transfer.sh'.format(file_name))
			try:
				ret, out = subprocess.getstatusoutput(
					'curl --upload-file {} https://transfer.sh/{}'.format(file_path, file_name))
				url = out.splitlines()[-1]
				self.file_urls.append(url)
				if self.is_online():
					self.chat(self.translation('OnUploadedMCPRFile').format(file_name, url), priority=ChatThread.Priority.High)
			except Exception:
				logger.error('Fail to upload "{}" to transfer.sh'.format(file_name))
				logger.error(traceback.format_exc())

	def on_final_stop(self, logger, restart):
		logger.log('File operations finished, disconnect now')
		try:
			self.disconnect()
		except Exception as e:
			logger.warn('Fail to disconnect: {}'.format(e))
			try:
				self.connection.disconnect(immediate=True)
			except Exception as e:
				logger.warn('Fail to immediately disconnect: {}'.format(e))
		self.file_thread = None
		self.mc_version = None
		self.mc_protocol = None
		self.replay_file = None
		if self.chat_thread is not None:
			self.chat_thread.kill()
		logger.log('PCRC stopped')

		if restart:
			logger.log('---------------------------------------')
			for i in range(3):
				logger.log('PCRC restarting in {}s'.format(3 - i))
				time.sleep(1)
			if not self.is_stopped():
				logger.log('Waiting for PCRC to be startable')
				while not self.is_stopped():
					time.sleep(0.1)
			self.start()

	# Commands

	def _chat(self, text, prefix='', priority=None):
		for line in text.splitlines():
			if priority is None:
				self.chat_thread.add_chat(prefix + line)
			else:
				self.chat_thread.add_chat(prefix + line, priority)


	def chat(self, text, priority=None):
		if self.is_online():
			self._chat(text, priority=priority)
		else:
			self.logger.warn('Cannot chat when disconnected')

	def tell(self, name, text):
		if name is None:
			return self.chat(text)
		if self.is_online():
			self._chat(text, prefix='/tell {} '.format(name))
		else:
			self.logger.warn('Cannot /tell when disconnected')

	def _respawn(self):
		packet = serverbound.play.ClientStatusPacket()
		packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
		self.connection.write_packet(packet)
		self.logger.log('sent respawn packet to the server')

	def respawn(self):
		if self.is_online():
			self._respawn()
		else:
			self.logger.warn('Cannot respawn when disconnected')

	def _spectate(self, uuid):
		packet = serverbound.play.SpectatePacket()
		packet.target = uuid
		self.connection.write_packet(packet)
		self.logger.log('try spectate to entity(uuid = {})'.format(uuid))

	def spectate(self, uuid):
		if self.is_online():
			self._spectate(uuid)
		else:
			self.logger.warn('Cannot send respawn when disconnected')

	def format_status(self, text):
		return text.format(
			self.is_working(), self.is_working() and not self.isAFKing(),
			utils.convert_millis(self.timeRecorded()), utils.convert_millis(self.timePassed()),
			self.packet_counter, utils.convert_file_size_MB(len(self.file_buffer)), utils.convert_file_size_MB(self.replay_file.size()),
			self.file_name
		)

	def print_urls(self):
		if len(self.file_urls) == 0:
			self.chat(self.translation('UrlNotFound'))
		else:
			self.chat(self.translation('PrintUrls').format(len(self.file_urls)))
			for url in self.file_urls:
				self.chat(url)

	def set_config(self, option, value, forced=False):
		if not forced and option not in config.SettableOptions:
			self.chat(self.translation('IllegalOptionName').format(option, self.config.get('command_prefix')))
			return
		self.chat(self.translation('OnOptionSet').format(option, value))
		self.config.set_value(option, value)
		self.logger.log('Option <{}> set to <{}>'.format(option, value))

	def print_markers(self):
		if len(self.replay_file.markers) == 0:
			self.chat(self.translation('MarkerNotFound'))
		else:
			self.chat(self.translation('CommandMarkerListTitle'))
			for i in range(len(self.replay_file.markers)):
				name = self.replay_file.markers[i]['value']['name'] if 'name' in self.replay_file.markers[i]['value'] else ''
				self.chat('{}. {} {}'.format(i + 1, utils.convert_millis(self.replay_file.markers[i]['realTimestamp']), name))

	def add_marker(self, name=None):
		if self.pos is None:
			self.logger.warn('Fail to add marker, position unknown!')
			return
		time_stamp = self.timeRecorded()
		marker = self.replay_file.add_marker(self.timeRecorded(), self.pos, name)
		self.chat(self.translation('OnMarkerAdded').format(utils.convert_millis(time_stamp)))
		self.logger.log('Marker added: {}, {} markers has been stored'.format(marker, len(self.replay_file.markers)))

	def delete_marker(self, index):
		marker = self.replay_file.pop_marker(index - 1)
		self.chat(self.translation('OnMarkerDeleted').format(utils.convert_millis(marker['realTimestamp'])))
		self.logger.log('Marker deleted: {}, {} markers has been stored'.format(marker, len(self.replay_file.markers)))

	def set_file_name(self, new_name):
		old_name = self.file_name
		self.chat(self.translation('OnFileNameSet').format(new_name))
		self.file_name = new_name
		self.logger.log('File name is setting from {0} to {1}'.format(old_name, new_name))

	def processCommand(self, command, sender, uuid):
		try:
			args = command.split(' ')  # !!PCRC <> <> <> <>
			if len(args) == 0 or args[0] != self.config.get('command_prefix') or sender == self.config.get('username'):
				return
			self.logger.log('Processing Command {} from {} {}'.format(args, sender, uuid))
			if len(args) == 1:
				self.chat(self.translation('CommandHelp').format(self.config.get('command_prefix')))
			elif len(args) == 2 and args[1] == 'status':
				self.chat(self.format_status(self.translation('CommandStatusResult')))
			elif len(args) == 2 and args[1] in ['spectate', 'spec'] and sender is not None and uuid is not None:
				self.chat(self.translation('CommandSpectateResult').format(sender, uuid))
				self.spectate(uuid)
			elif len(args) == 2 and args[1] == 'here':
				self.chat('!!here')
			elif len(args) == 2 and args[1] in ['where', 'location', 'loc', 'position', 'pos']:
				if self.pos is not None:
					self.chat(self.translation('CommandPositionResult').format(utils.format_vector(self.pos)))
				else:
					self.chat(self.translation('CommandPositionResultUnknown'))
			elif len(args) == 2 and args[1] in ['stop']:
				self.stop(by_user=True)
			elif len(args) == 2 and args[1] == 'restart':
				self.restart(True)
			elif len(args) == 2 and args[1] in ['url', 'urls']:
				self.print_urls()
			elif len(args) == 4 and args[1] == 'set':
				self.set_config(args[2], args[3])
			elif len(args) == 2 and args[1] == 'set':
				self.chat(self.translation('CommandSetListTitle'))
				self.chat(', '.join(config.SettableOptions))
			elif (len(args) == 2 and args[1] == 'marker') or (len(args) == 3 and args[1] == 'marker' and args[2] == 'list'):
				self.print_markers()
			elif 3 <= len(args) <= 4 and args[1] == 'marker' and args[2] == 'add':
				self.add_marker(None if len(args) == 3 else args[3])
			elif len(args) == 4 and args[1] == 'marker' and args[2] in ['del', 'delete']:
				try:
					index = int(args[3])
				except ValueError:
					self.chat(self.translation('WrongArguments'))
				else:
					if 1 <= index <= len(self.replay_file.markers):
						self.delete_marker(index)
					else:
						self.chat(self.translation('WrongArguments'))
			elif len(args) == 3 and args[1] == 'name':
				self.set_file_name(args[2])
			else:
				self.chat(self.translation('UnknownCommand').format(self.config.get('command_prefix')))
		except Exception:
			self.logger.error('Error when processing command "{}"'.format(command))
			self.logger.error(traceback.format_exc())


class ChatThread(threading.Thread):
	class Priority:
		Low = 1
		Normal = 0
		High = -1

	class QueueData:
		id_counter = 0

		def __init__(self, priority, data):
			self.priority = priority
			self.data = data
			self.id = ChatThread.QueueData.id_counter + 1
			ChatThread.QueueData.id_counter += 1

		def __lt__(self, other):
			return self.priority < other.priority or (self.priority == other.priority and self.id < other.id)

	def __init__(self, recorder):
		super().__init__()
		self.setDaemon(True)
		self.recorder = recorder
		self.clear_queue()
		self.logger = copy.deepcopy(recorder.logger)
		self.logger.thread = 'Chat'
		self.interrupt = False
		self.chatSpamThresholdCount = 0

	def add_chat(self, msg, prio=Priority.Normal):
		self.logger.debug('Added chat "{}" with priority {} to queue'.format(msg, prio))
		heapq.heappush(self.message_queue, ChatThread.QueueData(prio, msg))

	def send_chat(self, queue_data):
		msg = queue_data.data
		packet = serverbound.play.ChatPacket()
		packet.message = msg
		self.recorder.connection.write_packet(packet)
		self.logger.log('Sent chat message "{}" to the server'.format(msg))
		self.chatSpamThresholdCount += 20

	def clear_queue(self):
		self.message_queue = []

	def kill(self):
		self.interrupt = True
		self.clear_queue()

	# instant send all chat with priority <= p
	def flush_pending_chat(self, p=Priority.Low):
		while len(self.message_queue) > 0 and self.message_queue[0].priority <= p:
			self.send_chat(heapq.heappop(self.message_queue))

	def on_recieved_TimeUpdatePacket(self):
		self.chatSpamThresholdCount -= 20  # 20 gt passed
		if self.chatSpamThresholdCount < 0:
			self.chatSpamThresholdCount = 0

	def can_chat(self):
		# vanilla threshold is 200 but I set it to 180 for safety
		return not self.recorder.config.get('chat_spam_protect') or self.chatSpamThresholdCount + 20 < 180

	def run(self):
		self.logger.log('Chat thread started')
		while not self.interrupt:
			if self.can_chat():
				if len(self.message_queue) > 0:
					self.send_chat(heapq.heappop(self.message_queue))
			time.sleep(0.001)
		self.logger.log('Chat thread stopped')


class PacketProcessor:
	def __init__(self, recorder, version):
		self.recorder = recorder
		self.version = version
		self.blocked_entity_ids = []
		self.player_ids = []

	@property
	def logger(self):
		return self.recorder.logger

	def analyze(self, packet, modification=False):
		if not modification:
			packet = copy.deepcopy(packet)
		packet_id = packet.read_varint()
		packet_name = self.recorder.protocolMap[str(packet_id)] if str(packet_id) in self.recorder.protocolMap else 'unknown'
		return packet_id, packet_name

	def process(self, packet):
		try:
			return self._process(packet)
		except:
			self.logger.error('Error when processing packet')
			try:
				packet_id, packet_name = self.analyze(packet)
			except:
				self.logger.error('Fail to analyze packet information')
			else:
				self.logger.error('Packet id = {}; Packet name = {}'.format(packet_id, packet_name))
			raise

	def _process(self, packet):
		def filterBadPacket(packet_result):
			if packet_result is not None and (packet_name in utils.BAD_PACKETS or (
					self.recorder.config.get('minimal_packets') and packet_name in utils.USELESS_PACKETS)):
				packet_result = None
			return packet_result

		# update PCRC's position
		def processPlayerPositionAndLook(packet_result):
			if packet_name == 'Player Position And Look (clientbound)':
				player_x = packet.read_double()
				player_y = packet.read_double()
				player_z = packet.read_double()
				player_yaw = packet.read_float()
				player_pitch = packet.read_float()
				flags = packet.read_byte()
				if flags == 0:
					self.recorder.pos = PositionAndLook(x=player_x, y=player_y, z=player_z, yaw=player_yaw, pitch=player_pitch)
					self.logger.log('Set self\'s position to {}'.format(self.recorder.pos))
			return packet_result

		# world time control
		def processTimeUpdate(packet_result):
			if packet_result is not None and 0 <= self.recorder.config.get('daytime') < 24000 and packet_name == 'Time Update':
				self.logger.log('Set daytime to: ' + str(self.recorder.config.get('daytime')))
				world_age = packet.read_long()
				packet_result = SARCPacket()
				packet_result.write_varint(packet_id)
				packet_result.write_long(world_age)
				packet_result.write_long(-self.recorder.config.get(
					'daytime'))  # If negative sun will stop moving at the Math.abs of the time
				packet_result.receive(packet_result.flush())
				utils.BAD_PACKETS.append('Time Update')  # Ignore all further updates
			return packet_result

		# Weather yeet
		def processChangeGameState(packet_result):
			# Remove weather if configured
			if packet_result is not None and not self.recorder.config.get('weather') and packet_name == 'Change Game State':
				reason = packet.read_ubyte()
				if reason in [1, 2, 7, 8]:
					packet_result = None
			return packet_result

		# add player id for afk detector and uuid for recording
		def processSpawnPlayer(packet_result):
			if packet_result is not None and packet_name == 'Spawn Player':
				entity_id = packet.read_varint()
				uuid = packet.read_uuid()
				if entity_id not in self.player_ids:
					self.player_ids.append(entity_id)
					self.logger.debug('Player spawned, added to player id list, id = {}'.format(entity_id))
				if uuid not in self.recorder.player_uuids:
					self.recorder.player_uuids.append(uuid)
					self.logger.log('Player spawned, added to uuid list, uuid = {}'.format(uuid))
				self.recorder.updatePlayerMovement()
			return packet_result

		# check if the spawned is in black list
		def processSpawnEntity(packet_result):
			EntityTypeItem = {
				'1.12': 2,
				'1.12.2': 2,
				'1.14.4': 34
			}
			EntityTypeBat = {
				'1.12': 65,
				'1.12.2': 65,
				'1.14.4': 3
			}
			EntityTypePhantom = {
				'1.12': -1,
				'1.12.2': -1,
				'1.14.4': 97
			}
			# Keep track of spawned items and their ids
			if packet_result is not None and (packet_name == 'Spawn Object' or packet_name == 'Spawn Mob'):
				entity_id = packet.read_varint()
				entity_uuid = packet.read_uuid()
				entity_type = packet.read_byte()
				self.logger.debug('{} with id {} and type {}'.format(packet_name, entity_id, entity_type))
				entity_name = None
				if self.recorder.config.get('remove_items') and packet_name == 'Spawn Object' and entity_type == EntityTypeItem[self.recorder.mc_version]:
					entity_name = 'Item'
				if self.recorder.config.get('remove_bats') and packet_name == 'Spawn Mob' and entity_type == EntityTypeBat[self.recorder.mc_version]:
					entity_name = 'Bat'
				if self.recorder.config.get('remove_phantoms') and packet_name == 'Spawn Mob' and entity_type == EntityTypePhantom[self.recorder.mc_version]:
					entity_name = 'Phantom'
				if entity_name is not None:
					self.logger.debug('{} spawned but ignore and added to blocked id list, id = {}'.format(entity_name, entity_id))
					self.blocked_entity_ids.append(entity_id)
					packet_result = None
			return packet_result

		# Removed destroyed blocked entity's id
		def processDestroyEntities(packet_result):
			if packet_result is not None and packet_name == 'Destroy Entities':
				count = packet.read_varint()
				for i in range(count):
					entity_id = packet.read_varint()
					if entity_id in self.blocked_entity_ids:
						self.blocked_entity_ids.remove(entity_id)
						self.logger.debug(
							'Entity destroyed, removed from blocked entity id list, id = {}'.format(entity_id))
					if entity_id in self.player_ids:
						self.player_ids.remove(entity_id)
						self.logger.debug('Player destroyed, removed from player id list, id = {}'.format(entity_id))
			return packet_result

		# Remove item pickup animation packet
		def processCollectItem(packet_result):
			if packet_result is not None and self.recorder.config.get(
					'remove_items') and packet_name == 'Collect Item':
				collected_entity_id = packet.read_varint()
				if collected_entity_id in self.blocked_entity_ids:
					self.blocked_entity_ids.remove(collected_entity_id)
					self.logger.debug('Entity item collected, removed from blocked entity id list, id = {}'.format(
						collected_entity_id))
				packet_result = None
			return packet_result

		# Detecting player activity to continue recording and remove items or bats
		def processEntityPackets(packet_result):
			if packet_name in utils.ENTITY_PACKETS:
				entity_id = packet.read_varint()
				if entity_id in self.player_ids:
					self.recorder.updatePlayerMovement()
					self.logger.debug('Update player movement time, triggered by entity id {}'.format(entity_id))
				if entity_id in self.blocked_entity_ids:
					packet_result = None
			return packet_result

		packet = copy.deepcopy(packet)
		packet_recorded = copy.deepcopy(packet)
		packet_id, packet_name = self.analyze(packet, modification=True)

		# update chatSpamThresholdCount in chat thread
		if packet_name == 'Time Update':
			self.recorder.chat_thread.on_recieved_TimeUpdatePacket()

		# process packet
		packet_recorded = filterBadPacket(packet_recorded)
		packet_recorded = processPlayerPositionAndLook(packet_recorded)
		packet_recorded = processTimeUpdate(packet_recorded)
		packet_recorded = processChangeGameState(packet_recorded)
		packet_recorded = processSpawnPlayer(packet_recorded)
		packet_recorded = processSpawnEntity(packet_recorded)
		packet_recorded = processDestroyEntities(packet_recorded)
		packet_recorded = processCollectItem(packet_recorded)
		packet_recorded = processEntityPackets(packet_recorded)

		return packet_recorded
