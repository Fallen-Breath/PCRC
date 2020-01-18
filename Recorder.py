# coding: utf8
import copy
import os
import shutil
import socket
import threading
import time
import json
import traceback
import zipfile
import datetime
import subprocess

from Translation import Translation
import utils
import pycraft
from Logger import Logger
from pycraft import authentication
from pycraft.networking.connection import Connection
from pycraft.networking.packets import Packet as PycraftPacket, clientbound, serverbound
from SARC.packet import Packet as SARCPacket
from pycraft.networking.types import PositionAndLook


class Config():
	SettableOptions = ['language', 'minimal_packets', 'daytime', 'weather', 'with_player_only', 'remove_items', 'remove_bats']
	def __init__(self, file_name):
		self.file_name = file_name
		with open(file_name) as f:
			self.data = json.load(f)

	def set_value(self, option, value, forced=False):
		if not forced:
			t = type(self.data[option])
			if t is str:
				value = value
			elif t is bool:
				value = value in ['true', 'True', 'TRUE']
			elif t is int:
				value = int(value)
			elif t is float:
				value = float(value)
		self.data[option] = value

	def write_to_file(self, file_name=None):
		if file_name is None:
			file_name = self.file_name
		with open(file_name, 'w') as f:
			json.dump(self.data, f, indent=4)

	def get(self, option):
		if option in self.data:
			return self.data[option]
		else:
			return None

class Recorder():
	socket_id = None

	def __init__(self, config_file, translation_folder):
		self.config = Config(config_file)
		self.translations = Translation(translation_folder)
		self.working = False
		self.online = False
		self.file_thread = None
		self.file_urls = []
		self.logger = Logger(name='Recorder', file_name='PCRC.log', display_debug=self.config.get('debug_mode'))
		self.printConfig()

		if not self.config.get('online_mode'):
			self.logger.log("Login in offline mode")
			self.connection = Connection(self.config.get('address'), self.config.get('port'), username=self.config.get('username'), recorder=self)
		else:
			self.logger.log("Login in online mode")
			auth_token = authentication.AuthenticationToken()
			auth_token.authenticate(self.config.get('username'), self.config.get('password'))
			self.logger.log("Logged in as %s" % auth_token.profile.name)
			self.config.set_value('username', auth_token.profile.name)
			self.connection = Connection(self.config.get('address'), self.config.get('port'), auth_token=auth_token, recorder=self)

		self.connection.register_packet_listener(self.onPacketReceived, PycraftPacket)
		self.connection.register_packet_listener(self.onPacketSent, PycraftPacket, outgoing=True)
		self.connection.register_packet_listener(self.onGameJoin, clientbound.play.JoinGamePacket)
		self.connection.register_packet_listener(self.onDisconnect, clientbound.play.DisconnectPacket)
		self.connection.register_packet_listener(self.onChatMessage, clientbound.play.ChatMessagePacket)
		self.connection.register_packet_listener(self.onPlayerPositionAndLook, clientbound.play.PlayerPositionAndLookPacket)

		self.protocolMap = {}
		self.logger.log('init finish')

	def __del__(self):
		self.stop()

	def translation(self, text):
		return self.translations.translate(text, self.config.get('language'))

	def printConfig(self):
		message = '------- Config --------\n'
		message += f"Language = {self.config.get('language')}\n"
		message += f"Online mode = {self.config.get('online_mode')}\n"
		message += f"User name = {self.config.get('username')}\n"
		message += f"Password = ******\n"
		message += f"Server address = {self.config.get('address')}\n"
		message += f"Server port = {self.config.get('port')}\n"
		message += f"Minimal packets mode = {self.config.get('minimal_packets')}\n"
		message += f"Daytime set to = {self.config.get('daytime')}\n"
		message += f"Weather switch = {self.config.get('weather')}\n"
		message += f"Record with player only = {self.config.get('with_player_only')}\n"
		message += f"Remove items = {self.config.get('remove_items')}\n"
		message += f"Remove bats = {self.config.get('remove_bats')}\n"
		message += f"Upload file to transfer.sh = {self.config.get('upload_file')}\n"
		message += f"Auto relogin = {self.config.get('auto_relogin')}\n"
		message += f"Debug mode = {self.config.get('debug_mode')}\n"
		message += '----------------------'
		for line in message.splitlines():
			self.logger.log(line)

	def isOnline(self):
		return self.online

	def isWorking(self):
		return self.working

	def onPacketSent(self, packet):
		self.logger.debug('<- {}'.format(packet.data))
		pass

	def onPacketReceived(self, packet):
	#	self.logger.debug('-> {}'.format(packet.data))
		self.processPacketData(packet)

	def onGameJoin(self, packet):
		self.logger.log('Connected to the server')
		self.online = True
		self.chat(self.translation('OnGameJoin'))

	def onDisconnect(self, packet):
		self.logger.log('Disconnected from the server, reason = {}'.format(packet.json_data))
		self.online = False
		if self.isWorking():
			self.stop(self.config.get('auto_relogin'))

	def onChatMessage(self, packet):
		js = json.loads(packet.json_data)
		try:
			translate = js['translate']
			msg = js['with'][-1]
			message = '({}) '.format(packet.field_string('position'))
			try:
				name = js['with'][0]['insertion']
			except:
				name = None
			if translate == 'chat.type.announcement':  # from server
				message += '[Server] {}'.format(msg['text'])
				self.processCommand(msg['text'], None, None)
			elif translate == 'chat.type.text':  # chat
				message += '<{}> {}'.format(name, msg)
				uuid = js['with'][0]['hoverEvent']['value']['text'].split('"')[7]
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
			self.logger.debug(traceback.format_exc())
			self.logger.debug('json data = {}'.format(js))
			pass

	def onPlayerPositionAndLook(self, packet):
		self.updatePlayerMovement()

	def connect(self):
		if self.isOnline():
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

		if not success:
			self.stop()
		return success

	def disconnect(self):
		if not self.isOnline():
			self.logger.warn('Cannot disconnect when disconnected')
			return
		if len(self.file_urls) > 0:
			self.print_urls()
		self.chat(self.translation('OnDisconnect'))
		self.connection.disconnect()
		self.online = False

	def updatePlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		self.last_player_movement = t

	def noPlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return t - self.last_player_movement >= 10 * 1000

	def isAFKing(self):
		return self.noPlayerMovement() and self.config.get('with_player_only')

	def timePassed(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return t - self.start_time

	def timeRecorded(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return self.timePassed(t) - self.afk_time

	def processPacketData(self, packet_raw):
		if not self.isWorking():
			return
		bytes = packet_raw.data
		if bytes[0] == 0x00:
			bytes = bytes[1:]
		t = utils.getMilliTime()
		packet_length = len(bytes)
		packet = SARCPacket()
		packet.receive(bytes)
		packet_recorded = copy.deepcopy(packet)
		packet_id = packet.read_varint()
		packet_name = self.protocolMap[str(packet_id)] if str(packet_id) in self.protocolMap else 'unknown'

		if packet_name == 'Player Position And Look (clientbound)':
			player_x = packet.read_double()
			player_y = packet.read_double()
			player_z = packet.read_double()
			player_yaw = packet.read_float()
			player_pitch = packet.read_float()
			flags = packet.read_byte()
			if flags == 0:
				self.pos = PositionAndLook(x=player_x, y=player_y, z=player_z, yaw=player_yaw, pitch=player_pitch)
				self.logger.log('Set self\'s position to {}'.format(self.pos))

		if packet_recorded is not None and (packet_name in utils.BAD_PACKETS or (self.config.get('minimal_packets') and packet_name in utils.USELESS_PACKETS)):
			packet_recorded = None

		if packet_recorded is not None and packet_name == 'Spawn Mob' and packet_length == 3:
			packet_recorded = None
			self.logger.log('nou wired packet')


		if packet_recorded is not None and 0 <= self.config.get('daytime') < 24000 and packet_name == 'Time Update':
			self.logger.log('Set daytime to: ' + str(self.config.get('daytime')))
			world_age = packet.read_long()
			packet_recorded = SARCPacket()
			packet_recorded.write_varint(packet_id)
			packet_recorded.write_long(world_age)
			packet_recorded.write_long(-self.config.get('daytime'))  # If negative sun will stop moving at the Math.abs of the time
			utils.BAD_PACKETS.append('Time Update')  # Ignore all further updates

		# Remove weather if configured
		if packet_recorded is not None and not self.config.get('weather') and packet_name == 'Change Game State':
			reason = packet.read_ubyte()
			if reason == 1 or reason == 2:
				packet_recorded = None

		if packet_recorded is not None and packet_name == 'Spawn Player':
			entity_id = packet.read_varint()
			uuid = packet.read_uuid()
			if entity_id not in self.player_ids:
				self.player_ids.append(entity_id)
				self.logger.debug('Player spawned, added to player id list, id = {}'.format(entity_id))
			if uuid not in self.player_uuids:
				self.player_uuids.append(uuid)
				self.logger.log('Player spawned, added to uuid list, uuid = {}'.format(uuid))
			self.updatePlayerMovement()

		# Keep track of spawned items and their ids
		if (packet_recorded is not None and
				(self.config.get('remove_items') or self.config.get('remove_bats')) and
				(packet_name == 'Spawn Object' or packet_name == 'Spawn Mob')):
			entity_id = packet.read_varint()
			entity_uuid = packet.read_uuid()
			entity_type = packet.read_byte()
			entity_name = None
			if self.config.get('remove_items') and packet_name == 'Spawn Object' and entity_type == 34:
				entity_name = 'item'
			if self.config.get('remove_bats') and packet_name == 'Spawn Mob' and entity_type == 3:
				entity_name = 'bat'
			if entity_name is not None:
				self.logger.debug('{} spawned but ignore and added to blocked id list, id = {}'.format(entity_name, entity_id))
				self.blocked_entity_ids.append(entity_id)
				packet_recorded = None

		# Removed destroyed blocked entity's id
		if packet_recorded is not None and packet_name == 'Destroy Entities':
			count = packet.read_varint()
			for i in range(count):
				entity_id = packet.read_varint()
				if entity_id in self.blocked_entity_ids:
					self.blocked_entity_ids.remove(entity_id)
					self.logger.debug('Entity destroyed, removed from blocked entity id list, id = {}'.format(entity_id))
				if entity_id in self.player_ids:
					self.player_ids.remove(entity_id)
					self.logger.debug('Player destroyed, removed from player id list, id = {}'.format(entity_id))

		# Remove item pickup animation packet
		if packet_recorded is not None and self.config.get('remove_items') and packet_name == 'Collect Item':
			collected_entity_id = packet.read_varint()
			if collected_entity_id in self.blocked_entity_ids:
				self.blocked_entity_ids.remove(collected_entity_id)
				self.logger.debug('Entity item collected, removed from blocked entity id list, id = {}'.format(collected_entity_id))
			packet_recorded = None

		# Detecting player activity to continue recording and remove items or bats
		if packet_name in utils.ENTITY_PACKETS:
			entity_id = packet.read_varint()
			if entity_id in self.player_ids:
				self.updatePlayerMovement()
				self.logger.debug('Update player movement time, triggered by entity id {}'.format(entity_id))
			if entity_id in self.blocked_entity_ids:
				packet_recorded = None

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
		if self.isWorking() and packet_recorded is not None and not self.isAFKing():
			bytes = packet_recorded.read(packet_recorded.remaining())
			data = int(t - self.start_time).to_bytes(4, byteorder='big', signed=True)
			data += len(bytes).to_bytes(4, byteorder='big', signed=True)
			data += bytes
			self.write(data)
			self.logger.debug('{} packet recorded'.format(packet_name))
			self.packet_counter += 1
		else:
			self.logger.debug('{} packet ignore'.format(packet_name))

		if self.isWorking() and self.file_size > utils.FileSizeLimit:
			self.logger.log('tmcpr file size limit {}MB reached! Restarting'.format(utils.convert_file_size(utils.FileSizeLimit)))
			self.chat(self.translation('OnReachFileSizeLimit').format(utils.convert_file_size(utils.FileSizeLimit)))
			self.restart()

		if self.isWorking() and self.timeRecorded(t) > utils.TimeLengthLimit:
			self.logger.log('{} actual recording time reached!'.format(utils.convert_millis(utils.TimeLengthLimit)))
			self.chat(self.translation('OnReachTimeLimit').format(utils.convert_millis(utils.TimeLengthLimit)))
			self.restart()

		if int(self.timePassed(t) / (60 * 1000)) != self.last_showinfo_time or self.packet_counter - self.last_showinfo_packetcounter >= 100000:
			self.last_showinfo_time = int(self.timePassed(t) / (60 * 1000))
			self.last_showinfo_packetcounter = self.packet_counter
			self.logger.log('Passed: {}; Recorded: {}, {} packets '.format(
				utils.convert_millis(self.timePassed(t)), utils.convert_millis(self.timeRecorded(t)), self.packet_counter)
			)

	def flush(self):
		if len(self.file_buffer) == 0:
			return
		with open(utils.RecordingFileName, 'ab+') as replay_recording:
			replay_recording.write(self.file_buffer)
		self.file_size += len(self.file_buffer)
		self.logger.log('Flushing {} bytes to "{}" file, file size = {}MB now'.format(
			len(self.file_buffer), utils.RecordingFileName, utils.convert_file_size(self.file_size)
		))
		self.file_buffer = bytearray()

	def write(self, data):
		self.file_buffer += data
		if len(self.file_buffer) > utils.FileBufferSize:
			self.flush()

	def createReplayFile(self, restart):
		if self.file_thread is not None:
			return
		self.file_thread = threading.Thread(target = self._createReplayFile, args=(restart, ))
		self.file_thread.setDaemon(True)
		self.flush()
		self.file_thread.start()
		self.file_thread.isAlive()

	def _createReplayFile(self, restart):
		logger = copy.deepcopy(self.logger)
		logger.thread = 'File'
		try:
			self.__createReplayFile(logger, restart)
		finally:
			logger.log('File operations finished, disconnect now')
			if self.isOnline():
				self.disconnect()
			self.file_thread = None
			logger.log('PCRC stopped')

			if restart:
				logger.log('---------------------------------------')
				logger.log('PCRC restarting')
				while not self.canStart():
					time.sleep(1)
				self.start()

	def __createReplayFile(self, logger, restart):
		self.flush()

		if self.file_size < utils.MinimumLegalFileSize:
			logger.log('Size of "{}" too small ({}MB < {}MB), abort creating replay file'.format(
				utils.RecordingFileName, utils.convert_file_size(self.file_size), utils.convert_file_size(utils.MinimumLegalFileSize)
			))
			return

		if not os.path.isfile(utils.RecordingFileName):
			logger.warn('"{}" file not found, abort creating replay file'.format(utils.RecordingFileName))
			return

		# Creating .mcpr zipfile based on timestamp
		logger.log('Time recorded/passed: {}/{}'.format(utils.convert_millis(self.timeRecorded()), utils.convert_millis(self.timePassed())))
		file_name = datetime.datetime.today().strftime('PCRC_%Y_%m_%d_%H_%M_%S') + '.mcpr'
		logger.log('Creating "{}"'.format(file_name))
		if self.isOnline():
			self.chat(self.translation('OnCreatingMCPRFile'))
		zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)

		meta_data = {
			'singleplayer': False,
			'serverName': 'SECRET SERVER',
			'duration': self.timeRecorded(),
			'date': utils.getMilliTime(),
			'mcversion': '1.14.4',
			'fileFormat': 'MCPR',
			'fileFormatVersion': '14',
			'protocol': 498,
			'generator': 'PCRC',
			'selfId': -1,
			'players': self.player_uuids
		}
		utils.addFile(zipf, 'markers.json', json.dumps(self.markers))
		utils.addFile(zipf, 'mods.json', '{"requiredMods":[]}')
		utils.addFile(zipf, 'metaData.json', json.dumps(meta_data))
		utils.addFile(zipf, '{}.crc32'.format(utils.RecordingFileName), str(utils.crc32f(utils.RecordingFileName)))
		utils.addFile(zipf, utils.RecordingFileName)
		zipf.close()

		logger.log('Size of replay file "{}": {}MB'.format(file_name, utils.convert_file_size(os.path.getsize(file_name))))
		folder = 'PCRC_recordings'
		if not os.path.exists(folder):
			os.makedirs(folder)
		file_path = '{}/{}'.format(folder, file_name)
		shutil.move(file_name, file_path)

		if self.config.get('upload_file'):
			if self.isOnline():
				self.chat(self.translation('OnUploadingMCPRFile'))
			logger.log('Uploading "{}" to transfer.sh'.format(utils.RecordingFileName))
			try:
				ret, out = subprocess.getstatusoutput(
					'curl --upload-file {} https://transfer.sh/{}'.format(file_path, file_name))
				url = out.splitlines()[-1]
				self.file_urls.append(url)
				if self.isOnline():
					self.chat(self.translation('OnUploadedMCPRFile').format(file_name, url))
			except Exception as e:
				logger.error('Fail to upload "{}" to transfer.sh'.format(utils.RecordingFileName))
				logger.error(traceback.format_exc())

	def canStart(self):
		return not self.isWorking() and not self.isOnline() and self.file_thread is None

	def finishedStopping(self):
		return self.canStart()

	def start(self):
		if not self.canStart():
			return
		self.logger.log('Starting PCRC')
		self.on_recording_start()
		# start the bot
		success = self.connect()
		if not success:
			return False
		# version check
		versionMap = {}
		for i in pycraft.SUPPORTED_MINECRAFT_VERSIONS.items():
			versionMap[i[1]] = i[0]
		protocol_version = self.connection.context.protocol_version
		self.logger.log('protocol = {}, mc version = {}'.format(protocol_version, versionMap[protocol_version]))
		if protocol_version != 498:
			self.logger.log('protocol version not support! should be 498 (MC version 1.14.4)')
			return False
		with open('protocol.json', 'r') as f:
			self.protocolMap = json.load(f)[str(protocol_version)]['Clientbound']
		return True

	# initializing stuffs
	def on_recording_start(self):
		self.working = True
		open(utils.RecordingFileName, 'w').close()
		self.start_time = utils.getMilliTime()
		self.last_player_movement = self.start_time
		self.afk_time = 0
		self.last_t = 0
		self.last_no_player_movement = False
		self.player_ids = []
		self.player_uuids = []
		self.blocked_entity_ids = []
		self.file_buffer = bytearray()
		self.file_size = 0
		self.last_showinfo_time = 0
		self.packet_counter = 0
		self.last_showinfo_packetcounter = 0
		self.file_thread = None
		self.markers = []
		self.pos = None
		if 'Time Update' in utils.BAD_PACKETS:
			utils.BAD_PACKETS.remove('Time Update')

	def stop(self, restart=False):
		if not self.isWorking():
			return
		self.logger.log('Stopping PCRC, restart = {}'.format(restart))
		if self.isOnline():
			self.chat(self.translation('OnPCRCStopping'))
		self.working = False
		self.createReplayFile(restart)

	def restart(self):
		self.stop(True)

	def _chat(self, text, prefix=''):
		for line in text.splitlines():
			packet = serverbound.play.ChatPacket()
			packet.message = prefix + line
			self.connection.write_packet(packet)
			self.logger.log('sent chat message "{}" to the server'.format(line))

	def chat(self, text):
		if self.isOnline():
			self._chat(text)
		else:
			self.logger.warn('Cannot chat when disconnected')

	def tell(self, name, text):
		if name is None:
			return self.chat(text)
		if self.isOnline():
			self._chat(text, '/tell {} '.format(name))
		else:
			self.logger.warn('Cannot /tell when disconnected')

	def _respawn(self):
		packet = serverbound.play.ClientStatusPacket()
		packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
		self.connection.write_packet(packet)
		self.logger.log('sent respawn packet to the server')

	def respawn(self):
		if self.isOnline():
			self._respawn()
		else:
			self.logger.warn('Cannot respawn when disconnected')

	def _spectate(self, uuid):
		packet = serverbound.play.SpectatePacket()
		packet.target = uuid
		self.connection.write_packet(packet)
		self.logger.log('try spectate to entity(uuid = {})'.format(uuid))

	def spectate(self, uuid):
		if self.isOnline():
			self._spectate(uuid)
		else:
			self.logger.warn('Cannot send respawn when disconnected')

	def format_status(self, text):
		return text.format(
			self.isWorking(), self.isWorking() and not self.isAFKing(),
			utils.convert_millis(self.timeRecorded()), utils.convert_millis(self.timePassed()),
			self.packet_counter, utils.convert_file_size(len(self.file_buffer)), utils.convert_file_size(self.file_size)
		)

	def print_urls(self):
		if len(self.file_urls) == 0:
			self.chat(self.translation('UrlNotFound'))
		else:
			self.chat(self.translation('PrintUrls').format(len(self.file_urls)))
			for url in self.file_urls:
				self.chat(url)

	def set_config(self, option, value):
		if option not in Config.SettableOptions:
			self.chat(self.translation('IllegalOptionName').format(option))
			return
		self.chat(self.translation('OnOptionSet').format(option, value))
		self.config.set_value(option, value)
		self.logger.log('Option <{}> set to <{}>'.format(option, value))

	def print_markers(self):
		if len(self.markers) == 0:
			self.chat(self.translation('MarkerNotFound'))
		else:
			self.chat(self.translation('CommandMarkerListTitle'))
			for i in range(len(self.markers)):
				name = self.markers[i]['value']['name'] if 'name' in self.markers[i]['value'] else ''
				self.chat('{}. {} {}'.format(i + 1, utils.convert_millis(self.markers[i]['realTimestamp']), name))

	def add_marker(self, name=None):
		if self.pos is None:
			self.logger.warn('Fail to add marker, position unknown!')
			return
		time_stamp = self.timeRecorded()
		marker = {
			'realTimestamp': time_stamp,
			'value': {
				'position': {
					'x': self.pos.x,
					'y': self.pos.y,
					'z': self.pos.z,
					# seems that replay mod switches these two values, idk y
					'yaw': self.pos.pitch,
					'pitch': self.pos.yaw,
					'roll': 0.0
				}
			}
		}
		if name is not None:
			marker['value']['name'] = name
		self.markers.append(marker)
		self.chat(self.translation('OnMarkerAdded').format(utils.convert_millis(time_stamp)))
		self.logger.log('Marker added: {}, {} markers has been stored'.format(marker, len(self.markers)))

	def delete_marker(self, index):
		index -= 1
		marker = self.markers.pop(index)
		self.chat(self.translation('OnMarkerDeleted').format(utils.convert_millis(marker['realTimestamp'])))
		self.logger.log('Marker deleted: {}, {} markers has been stored'.format(marker, len(self.markers)))

	def processCommand(self, command, sender, uuid):
		try:
			args = command.split(' ')  # !!PCRC <> <> <> <>
			if len(args) == 0 or args[0] != '!!PCRC' or sender == self.config.get('username'):
				return
			if len(args) == 1:
				self.chat(self.translation('CommandHelp'))
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
			elif len(args) == 2 and args[1] in ['stop', 'exit']:
				self.stop()
			elif len(args) == 2 and args[1] == 'restart':
				self.restart()
			elif len(args) == 2 and args[1] in ['url', 'urls']:
				self.print_urls()
			elif len(args) == 4 and args[1] == 'set':
				self.set_config(args[2], args[3])
			elif len(args) == 2 and args[1] == 'set':
				self.chat(self.translation('CommandSetListTitle'))
				self.chat(', '.join(Config.SettableOptions))
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
					if 1 <= index <= len(self.markers):
						self.delete_marker(index)
					else:
						self.chat(self.translation('WrongArguments'))
			else:
				self.chat(self.translation('UnknownCommand'))
		except Exception:
			self.logger.error('Error when processing command "{}"'.format(command))
			self.logger.error(traceback.format_exc())
