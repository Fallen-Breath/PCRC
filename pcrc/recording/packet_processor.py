from logging import Logger
from typing import TYPE_CHECKING, List, Callable

from minecraft.networking.packets import Packet, PlayerPositionAndLookPacket
from minecraft.networking.packets.clientbound.play import TimeUpdatePacket, SpawnPlayerPacket, SpawnObjectPacket, RespawnPacket
from minecraft.networking.types import PositionAndLook
from pcrc import constant
from pcrc.packets.s2c import DestroyEntitiesPacket, ChangeGameStatePacket
from pcrc.packets.s2c.entity_packet import AbstractEntityPacket

if TYPE_CHECKING:
	from pcrc.recording.recorder import Recorder


class PacketProcessor:
	def __init__(self, recorder: 'Recorder'):
		self.recorder: 'Recorder' = recorder
		self.logger: Logger = recorder.logger
		self.blocked_entity_ids = set()
		self.player_ids = set()
		self.recorded_time = False

	def init(self):
		self.blocked_entity_ids.clear()
		self.player_ids.clear()
		self.recorded_time = False

	def process(self, packet: Packet) -> bool:
		try:
			return self._process(packet)
		except:
			self.logger.error('Error when processing packet {}'.format(packet))
			self.logger.error('Packet id = {}; Packet name = {}'.format(packet.id, type(packet).__name__))
			raise

	def _process(self, packet: Packet) -> bool:
		def filterBadPacket() -> bool:
			# if packet_name in constant.BAD_PACKETS:
			# 	return False
			return True

		# update PCRC's position
		def processPlayerPositionAndLook() -> bool:
			if isinstance(packet, PlayerPositionAndLookPacket):
				player_x, player_y, player_z = packet.position
				player_yaw, player_pitch = packet.look
				self.recorder.pos = PositionAndLook(x=player_x, y=player_y, z=player_z, yaw=player_yaw, pitch=player_pitch)
				self.logger.info('Set self\'s position to {}'.format(self.recorder.pos))
			return True

		# world time control
		def processTimeUpdate() -> bool:
			if not self.recorded_time:
				self.recorded_time = True
				day_time = self.recorder.get_config('daytime')
				if 0 <= day_time < 24000 and isinstance(packet, TimeUpdatePacket):
					self.logger.info('Set daytime to: ' + str(day_time))
					packet.time_of_day = -day_time  # If negative sun will stop moving at the Math.abs of the time
			return True

		# Weather yeet
		def processChangeGameState() -> bool:
			# Remove weather if configured
			if not self.recorder.get_config('weather') and isinstance(packet, ChangeGameStatePacket):
				if packet.reason in [1, 2, 7, 8]:
					return False
			return True

		# add player id for afk detector and uuid for recording
		def processSpawnPlayer() -> bool:
			if isinstance(packet, SpawnPlayerPacket):
				entity_id = getattr(packet, 'entity_id')
				uuid = getattr(packet, 'player_UUID')
				if entity_id not in self.player_ids:
					self.player_ids.add(entity_id)
					self.logger.debug('Player spawned, added to player id list, id = {}'.format(entity_id))
				if uuid not in self.recorder.player_uuids:
					self.recorder.player_uuids.append(uuid)
					self.logger.info('Player spawned, added to uuid list, uuid = {}'.format(uuid))
				self.recorder.refresh_player_movement()
			return True

		def processSpawnEntity() -> bool:
			# Keep track of spawned items and their ids
			# check if the spawned is in black list

			# flag_spawn_object = packet_name in ['Spawn Object', 'Spawn Entity']
			# flag_spawn_mob = packet_name in ['Spawn Mob', 'Spawn Living Entity']
			if isinstance(packet, SpawnObjectPacket):
				entity_id = packet.entity_id
				entity_type_name = packet.type
				entity_type_id = packet.type_id
				self.logger.debug('{} with id {} and type {}'.format(packet_name, entity_id, entity_type_name))
				entity_name = None
				if self.recorder.get_config('remove_items') and entity_type_id == constant.EntityTypeItem[self.recorder.mc_version]:
					entity_name = 'Item'
				if self.recorder.get_config('remove_bats') and entity_type_id == constant.EntityTypeBat[self.recorder.mc_version]:
					entity_name = 'Bat'
				if self.recorder.get_config('remove_phantoms') and entity_type_id == constant.EntityTypePhantom[self.recorder.mc_version]:
					entity_name = 'Phantom'
				if entity_name is not None:
					self.logger.debug('{} spawned but ignore and added to blocked id list, id = {}'.format(entity_name, entity_id))
					self.blocked_entity_ids.add(entity_id)
					packet_result = None
			return True

		# Removed destroyed blocked entity's id
		def processDestroyEntities():
			if isinstance(packet, DestroyEntitiesPacket):
				for entity_id in packet.entity_ids:
					if entity_id in self.blocked_entity_ids:
						self.blocked_entity_ids.remove(entity_id)
						self.logger.debug('Entity destroyed, removed from blocked entity id list, id = {}'.format(entity_id))
					if entity_id in self.player_ids:
						self.player_ids.remove(entity_id)
						self.logger.debug('Player destroyed, removed from player id list, id = {}'.format(entity_id))
			return True

		# Detecting player activity to continue recording and remove items or bats
		def processEntityPackets():
			if isinstance(packet, AbstractEntityPacket):
				entity_id = packet.entity_id
				if entity_id in self.player_ids:
					self.recorder.refresh_player_movement()
					self.logger.debug('Update player movement time from {}, triggered by entity id {}'.format(packet, entity_id))
				if entity_id in self.blocked_entity_ids:
					return False
			return True

		# Detecting player activity to continue recording and remove items or bats
		def processRespawn():
			if isinstance(packet, RespawnPacket):
				self.logger.debug('Set recorded_time to False due to player respawn / dimension change')
				self.recorded_time = False
			return True

		packet_name = 'www'

		processors: List[Callable[[], bool]] = [
			filterBadPacket,
			processPlayerPositionAndLook,
			processTimeUpdate,
			processChangeGameState,
			processSpawnPlayer,
			processSpawnEntity,
			processDestroyEntities,
			processEntityPackets,
			processRespawn,
		]
		for processor in processors:
			if not processor():
				return False
		return True
