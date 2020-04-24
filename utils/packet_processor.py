# coding: utf8

import copy
from . import constant
from .SARC.packet import Packet as SARCPacket
from .pycraft.networking.types import PositionAndLook


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
			if packet_result is not None and (packet_name in constant.BAD_PACKETS or (
					self.recorder.config.get('minimal_packets') and packet_name in constant.USELESS_PACKETS)):
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
				constant.BAD_PACKETS.append('Time Update')  # Ignore all further updates
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
			# Keep track of spawned items and their ids
			if packet_result is None:
				return
			flag_spawn_object = packet_name in ['Spawn Object', 'Spawn Entity']
			flag_spawn_mob = packet_name in ['Spawn Mob', 'Spawn Living Entity']
			if flag_spawn_object or flag_spawn_mob:
				entity_id = packet.read_varint()
				entity_uuid = packet.read_uuid()
				entity_type = packet.read_byte()
				self.logger.debug('{} with id {} and type {}'.format(packet_name, entity_id, entity_type))
				entity_name = None
				if self.recorder.config.get('remove_items') and flag_spawn_object and entity_type == constant.EntityTypeItem[self.recorder.mc_version]:
					entity_name = 'Item'
				if self.recorder.config.get('remove_bats') and flag_spawn_mob and entity_type == constant.EntityTypeBat[self.recorder.mc_version]:
					entity_name = 'Bat'
				if self.recorder.config.get('remove_phantoms') and flag_spawn_mob and entity_type == constant.EntityTypePhantom[self.recorder.mc_version]:
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

		# Detecting player activity to continue recording and remove items or bats
		def processEntityPackets(packet_result):
			if packet_name in constant.ENTITY_PACKETS:
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
		packet_recorded = processEntityPackets(packet_recorded)

		return packet_recorded
