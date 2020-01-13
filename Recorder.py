# coding: utf8
import copy
import os
import time
import json
import zipfile
import datetime
import utils
import pycraft
from Logger import Logger
from pycraft import authentication
from pycraft.networking.connection import Connection
from pycraft.networking.packets import Packet as PycraftPacket, clientbound
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
		self.started = False
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
		self.connection.register_packet_listener(self.on_gamejoin, clientbound.play.JoinGamePacket)
		self.connection.register_packet_listener(self.on_disconnect, clientbound.play.DisconnectPacket)

		self.protocolMap = {}

	def on_gamejoin(self, packet):
		self.logger.log('Joined the game as {}'.format(self.config.username))

	def on_disconnect(self, packet):
		self.logger.log('Disconnected form server, reason = {}'.format(packet.json_data))
		self.stop_recording()

	def connect(self):
		self.start_recording()
		# start the bot
		self.connection.connect()

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

	def updatePlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		self.last_player_movement = t

	def noPlayerMovement(self, t=None):
		if t is None:
			t = utils.getMilliTime()
		return t - self.last_player_movement >= 10 * 1000

	def processPacketData(self, packet_raw):
		if not self.started or self.stopping:
			return False
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
		if t - self.last_player_movement > 5000:
			self.afk_time += t - self.last_t
		self.last_t = t

		# Recording
		if not self.stopping and packet_recorded is not None and not (self.noPlayerMovement() and self.config.with_player_only):
			bytes = packet_recorded.read(packet_recorded.remaining())
			data = int(t - self.start_time).to_bytes(4, byteorder='big', signed=True)
			data += len(bytes).to_bytes(4, byteorder='big', signed=True)
			data += bytes
			self.write(data)

		if not self.stopping and self.file_size > utils.FileSizeLimit:
			self.logger.log('tmcpr file size limit {}MB reached!'.format(utils.convert_file_size(utils.FileSizeLimit)))
			self.restart_recording()

		time_passed_all = t - self.start_time
		time_passed = time_passed_all - self.afk_time

		if not self.stopping and time_passed > 1000 * 60 * 60 * 5:
			self.logger.log('5h recording reached!')
			self.restart_recording()

		self.packet_counter += 1
		if int(time_passed_all / (60 * 1000)) != self.last_showinfo_time or self.packet_counter - self.last_showinfo_packetcounter >= 100000:
			self.last_showinfo_time = int(time_passed_all / (60 * 1000))
			self.last_showinfo_packetcounter = self.packet_counter
			self.logger.log('{} passed, {} packets recorded'.format(utils.convert_millis(time_passed_all), self.packet_counter))

	def flush(self):
		if len(self.file_buffer) == 0:
			return
		with open('recording.tmcpr', 'ab+') as replay_recording:
			replay_recording.write(self.file_buffer)
		self.file_size += len(self.file_buffer)
		self.logger.log('Flushing {} bytes to tmcpr file, file size = {}MB now'.format(len(self.file_buffer), utils.convert_file_size(self.file_size)))
		self.file_buffer = bytearray()

	def write(self, data):
		self.file_buffer += data
		if len(self.file_buffer) > utils.FileBufferSize:
			self.flush()

	def createReplayFile(self):
		self.flush()
		self.file_size = 0

		# Creating .mcpr zipfile based on timestamp
		self.logger.log('Time recorded: {}'.format(utils.convert_millis(utils.getMilliTime() - self.start_time)))
		self.logger.log('Creating .mcpr file...')
		file_name = datetime.datetime.today().strftime('PCRC_%Y_%m_%d_%H_%M_%S') + '.mcpr'
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
		utils.addFile(zipf, 'recording.tmcpr.crc32', str(utils.crc32f('recording.tmcpr')))
		utils.addFile(zipf, 'recording.tmcpr')

		self.logger.log('Size of replay file {}: {}MB'.format(file_name, utils.convert_file_size(os.path.getsize(file_name))))

	def start_recording(self):
		open('recording.tmcpr', 'w').close()
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
		self.started = True
		self.stopping = False
		self.logger.log('Recorder started')

	def stop_recording(self):  # Create metadata file
		self.stopping = True
		self.createReplayFile()
		self.connection.disconnect()
		self.started = False
		self.logger.log('Recorder stopped')

	def restart_recording(self):  # Create metadata file
		self.logger.log('Restarting bot')
		self.stop_recording()
		self.connection.disconnect()
		self.logger.log('{} disconnected'.format(self.config.username))
		self.logger.log('---------------------------------------')
		time.sleep(1)
		self.connection.connect()
		self.start_recording()
