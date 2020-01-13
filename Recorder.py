# coding: utf8
import copy
import os
import time
import json
import traceback
import zipfile
import datetime
import utils
import pycraft
from Logger import Logger
from pycraft import authentication
from pycraft.networking.connection import Connection
from pycraft.networking.packets import Packet as PycraftPacket, clientbound, serverbound
from SARC.packet import Packet as SARCPacket


class Config():
	def __init__(self, fileName):
		with open(fileName) as f:
			js = json.load(f)
		self.offline = js['offline']
		self.username = js['username']
		self.password = js['password']
		self.address = js['address']
		self.port = js['port']
		self.minimal_packets = js['minimal_packets']
		self.daytime = js['daytime']
		self.weather = js['weather']
		self.remove_items = js['remove_items']
		self.remove_bats = js['remove_bats']
		self.with_player_only = js['with_player_only']
		self.debug_mode = js['debug_mode']

class Recorder():
	socket_id = None

	def __init__(self, configFileName):
		self.config = Config(configFileName)
		self.recording = False
		self.online = False
		self.logger = Logger(name='Recorder', file_name='PCRC.log', display_debug=self.config.debug_mode)

		if self.config.offline:
			self.logger.log("Connecting in offline mode...")
			self.connection = Connection(self.config.address, self.config.port, username=self.config.username)
		else:
			auth_token = authentication.AuthenticationToken()
			auth_token.authenticate(self.config.username, self.config.password)
			self.logger.log("Logged in as %s..." % auth_token.username)
			self.connection = Connection(self.config.address, self.config.port, auth_token=auth_token)

		self.connection.register_packet_listener(self.processPacketData, PycraftPacket)
		self.connection.register_packet_listener(self.onGameJoin, clientbound.play.JoinGamePacket)
		self.connection.register_packet_listener(self.onDisconnect, clientbound.play.DisconnectPacket)
		self.connection.register_packet_listener(self.onChatMessage, clientbound.play.ChatMessagePacket)

		self.protocolMap = {}

	def isOnline(self):
		return self.online

	def isRecording(self):
		return self.recording

	def onGameJoin(self, packet):
		self.logger.log('Connected to the server')
		self.online = True

	def onDisconnect(self, packet):
		self.logger.log('Disconnected from the server, reason = {}'.format(packet.json_data))
		self.online = False
		if self.isRecording():
			self.stop()
			for i in range(3):
				self.logger.log('Restart in {}s'.format(3 - i))
				time.sleep(1)
			self.start()

	def onChatMessage(self, packet):
		try:
			js = json.loads(packet.json_data)
			translate = js['translate']
			msg = js['with'][-1]
			message = '({}) '.format(packet.field_string('position'))
			try:
				name = js['with'][0]['insertion']
			except:
				pass
			if translate == 'chat.type.announcement':
				message += '[Server] {}'.format(msg['text'])
			elif translate == 'chat.type.text':
				message += '<{}> {}'.format(name, msg)
			elif translate == 'commands.message.display.incoming':
				message += '<{}>(tell) {}'.format(name, msg['text'])
			elif translate in ['multiplayer.player.joined', 'multiplayer.player.left']:
				message += '{} {} the game'.format(name, translate.split('.')[2])
			elif translate == 'chat.type.emote':
				message += '* {} {}'.format(name, msg)
			else:
				message = packet.json_data
			if message is not None:
				print(message)
				self.logger.log(message, do_print=False)
		except:
			pass

	def connect(self):
		if self.isOnline():
			self.logger.warn('Cannot connect when connected')
			return
		self.connection.connect()

	def disconnect(self):
		if not self.isOnline():
			self.logger.warn('Cannot disconnect when disconnected')
			return
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

	def processPacketData(self, packet_raw):
		if not self.isRecording():
			return
		t = utils.getMilliTime()
		bytes = packet_raw.data
		if bytes[0] == 0x00:
			bytes = bytes[1:]
		packet_length = len(bytes)
		packet = SARCPacket()
		packet.receive(bytes)
		packet_recorded = copy.deepcopy(packet)
		packet_id = packet.read_varint()
		packet_name = self.protocolMap[str(packet_id)] if str(packet_id) in self.protocolMap else 'unknown'

		if packet_recorded is not None and (packet_name in utils.BAD_PACKETS or (self.config.minimal_packets and packet_name in utils.USELESS_PACKETS)):
			packet_recorded = None

		if packet_recorded is not None and packet_name == 'Spawn Mob' and packet_length == 3:
			packet_recorded = None
			self.logger.log('nou wired packet')

		if packet_recorded is not None and 0 <= self.config.daytime < 24000 and packet_name == 'Time Update':
			self.logger.log('Set daytime to: ' + str(self.config.daytime))
			world_age = packet.read_long()
			packet_recorded = SARCPacket()
			packet_recorded.write_varint(packet_id)
			packet_recorded.write_long(world_age)
			packet_recorded.write_long(-self.config.daytime)  # If negative sun will stop moving at the Math.abs of the time
			utils.BAD_PACKETS.append('Time Update')  # Ignore all further updates

		# Remove weather if configured
		if packet_recorded is not None and not self.config.weather and packet_name == 'Change Game State':
			reason = packet.read_ubyte()
			if reason == 1 or reason == 2:
				packet_recorded = None

		if packet_recorded is not None and packet_name == 'Spawn Player':
			entity_id = packet.read_varint()
			uuid = packet.read_uuid()
			if entity_id not in self.player_ids:
				self.player_ids.append(entity_id)
			if uuid not in self.player_uuids:
				self.player_uuids.append(uuid)
				self.logger.log('Player added, uuid = {}'.format(uuid))
			self.updatePlayerMovement()

		# Keep track of spawned items and their ids
		if (packet_recorded is not None and
				(self.config.remove_items or self.config.remove_bats) and
				(packet_name == 'Spawn Object' or packet_name == 'Spawn Mob')):
			entity_id = packet.read_varint()
			entity_uuid = packet.read_uuid()
			entity_type = packet.read_byte()
			entity_name = None
			if self.config.remove_items and packet_name == 'Spawn Object' and entity_type == 34:
				entity_name = 'item'
			if self.config.remove_bats and packet_name == 'Spawn Mob' and entity_type == 3:
				entity_name = 'bat'
			if entity_name is not None:
				self.logger.debug('{} spawned but ignore and added to blocked id list'.format(entity_name))
				self.blocked_entity_ids.append(entity_id)
				packet_recorded = None

		# Removed destroyed blocked entity's id
		if packet_recorded is not None and packet_name == 'Destroy Entities':
			count = packet.read_varint()
			for i in range(count):
				entity_id = packet.read_varint()
				if entity_id in self.blocked_entity_ids:
					self.blocked_entity_ids.remove(entity_id)

		# Remove item pickup animation packet
		if packet_recorded is not None and self.config.remove_items and packet_name == 'Collect Item':
			collected_entity_id = packet.read_varint()
			if collected_entity_id in self.blocked_entity_ids:
				self.blocked_entity_ids.remove(collected_entity_id)
			packet_recorded = None

		# Detecting player activity to continue recording and remove items or bats
		if packet_name in utils.ENTITY_PACKETS:
			entity_id = packet.read_varint()
			if entity_id in self.player_ids:
				self.updatePlayerMovement()
			if entity_id in self.blocked_entity_ids:
				packet_recorded = None

		# Increase afk timer when recording stopped, afk timer prevents afk time in replays
		if self.config.with_player_only and self.noPlayerMovement(t):
			self.afk_time += t - self.last_t
		self.last_t = t

		# Recording
		if self.isRecording() and packet_recorded is not None and not (self.noPlayerMovement() and self.config.with_player_only):
			bytes = packet_recorded.read(packet_recorded.remaining())
			data = int(t - self.start_time).to_bytes(4, byteorder='big', signed=True)
			data += len(bytes).to_bytes(4, byteorder='big', signed=True)
			data += bytes
			self.write(data)

		if self.isRecording() and self.file_size > utils.FileSizeLimit:
			self.logger.log('tmcpr file size limit {}MB reached!'.format(utils.convert_file_size(utils.FileSizeLimit)))
			self.restart()

		time_passed_all = t - self.start_time
		time_passed = time_passed_all - self.afk_time

		if self.isRecording() and time_passed > 1000 * 60 * 60 * 5:
			self.logger.log('5h recording reached!')
			self.restart()

		self.packet_counter += 1
		if int(time_passed_all / (60 * 1000)) != self.last_showinfo_time or self.packet_counter - self.last_showinfo_packetcounter >= 100000:
			self.last_showinfo_time = int(time_passed_all / (60 * 1000))
			self.last_showinfo_packetcounter = self.packet_counter
			self.logger.log('{} passed, {} packets recorded'.format(utils.convert_millis(time_passed_all), self.packet_counter))

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

	def createReplayFile(self):
		self.flush()
		self.file_size = 0

		if not os.path.isfile(utils.RecordingFileName):
			self.logger.warn('"{}" file not found, abort create replay file'.format(utils.RecordingFileName))
			return

		# Creating .mcpr zipfile based on timestamp
		self.logger.log('Time recorded: {}'.format(utils.convert_millis(utils.getMilliTime() - self.start_time)))
		file_name = datetime.datetime.today().strftime('PCRC_%Y_%m_%d_%H_%M_%S') + '.mcpr'
		self.logger.log('Creating "{}"'.format(file_name))
		zipf = zipfile.ZipFile(file_name, 'w', zipfile.ZIP_DEFLATED)

		meta_data = {
			'singleplayer': False,
			'serverName': 'SECRET SERVER',
			'duration': utils.getMilliTime() - self.start_time,
			'date': utils.getMilliTime(),
			'mcversion': '1.14.4',
			'fileFormat': 'MCPR',
			'fileFormatVersion': '14',
			'protocol': 498,
			'generator': 'PCRC',
			'selfId': -1,
			'players': self.player_uuids
		}
		utils.addFile(zipf, 'markers.json', '[]')
		utils.addFile(zipf, 'mods.json', '{"requiredMods":[]}')
		utils.addFile(zipf, 'metaData.json', json.dumps(meta_data))
		utils.addFile(zipf, '{}.crc32'.format(utils.RecordingFileName), str(utils.crc32f(utils.RecordingFileName)))
		utils.addFile(zipf, utils.RecordingFileName)

		self.logger.log('Size of replay file "{}": {}MB'.format(file_name, utils.convert_file_size(os.path.getsize(file_name))))

	def start(self):
		if self.isRecording():
			return
		self.on_recording_start()
		# start the bot
		self.connect()
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
		self.recording = True
		open(utils.RecordingFileName, 'w').close()
		self.start_time = utils.getMilliTime()
		self.last_player_movement = self.start_time
		self.afk_time = 0
		self.last_t = 0
		self.player_ids = []
		self.player_uuids = []
		self.blocked_entity_ids = []
		self.file_buffer = bytearray()
		self.file_size = 0
		self.last_showinfo_time = 0
		self.packet_counter = 0
		self.last_showinfo_packetcounter = 0
		if 'Time Update' in utils.BAD_PACKETS:
			utils.BAD_PACKETS.remove('Time Update')

	def stop(self):
		if not self.isRecording():
			return
		self.recording = False
		self.createReplayFile()
		self.disconnect()
		self.logger.log('Recorder stopped, ignore the BrokenPipeError below XD')

	def restart(self):
		self.logger.log('Restarting recorder')
		self.stop()
		self.logger.log('---------------------------------------')
		time.sleep(1)
		self.start()

	def sendChat(self, text):
		if self.isOnline():
			packet = serverbound.play.ChatPacket()
			packet.message = text
			self.connection.write_packet(packet)
			self.logger.log('sent chat message "{}" to the server'.format(text))
		else:
			self.logger.warn('Cannot send chat when disconnected')

	def sendRespawn(self):
		if self.isOnline():
			packet = serverbound.play.ClientStatusPacket()
			packet.action_id = serverbound.play.ClientStatusPacket.RESPAWN
			self.connection.write_packet(packet)
			self.logger.log('sent respawn packet to the server')
		else:
			self.logger.warn('Cannot send respawn when disconnected')