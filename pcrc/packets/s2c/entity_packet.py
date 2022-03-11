from abc import ABC, abstractmethod

from minecraft.networking.packets import Packet
from minecraft.networking.types import VarInt
from pcrc.utils import packet_util


class AbstractEntityPacket(Packet, ABC):
	entity_id: int

	fields = 'entity_id'

	@classmethod
	@abstractmethod
	def get_id(cls, _context):
		raise NotImplementedError()

	def read(self, file_object):
		self.entity_id = VarInt.read(file_object)
		# The reset of the packet? I don't care


class EntityMovementPacket(AbstractEntityPacket):
	"""
	wiki.vg names:
	- 1.12: "Entity"
	- >1.12 < 1.18: "Entity Movement"
	"""
	@classmethod
	def get_id(cls, context):
		return \
			-1 if context.protocol_later_eq(756) else \
			42 if context.protocol_later_eq(736) else \
			44 if context.protocol_later_eq(578) else \
			43 if context.protocol_later_eq(498) else \
			37 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Movement'


# see pycraft minecraft.networking.packets.clientbound.play.EntityPositionDeltaPacket
#
# class EntityPositionPacket(AbstractEntityPacket):
# 	"""
# 	wiki.vg names:
# 	- 1.12: "Entity Relative Move"
# 	- >1.12: "Entity Position"
# 	"""
# 	@classmethod
# 	def get_id(cls, context):
# 		return \
# 			41 if context.protocol_later_eq(756) else \
# 			39 if context.protocol_later_eq(754) else \
# 			39 if context.protocol_later_eq(736) else \
# 			41 if context.protocol_later_eq(578) else \
# 			40 if context.protocol_later_eq(498) else \
# 			38 if context.protocol_later_eq(335) else \
# 			-1
#
# 	packet_name = 'Entity Position'


class EntityPositionAndRotationPacket(AbstractEntityPacket):
	"""
	wiki.vg names:
	- 1.12: "Entity Look And Relative Move"
	- >1.12: "Entity Position and Rotation"
	"""
	@classmethod
	def get_id(cls, context):
		return \
			42 if context.protocol_later_eq(756) else \
			40 if context.protocol_later_eq(736) else \
			42 if context.protocol_later_eq(578) else \
			41 if context.protocol_later_eq(498) else \
			39 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Position and Rotation'


class EntityRotationPacket(AbstractEntityPacket):
	"""
	wiki.vg names:
	- 1.12: "Entity Look"
	- >1.12: "Entity Rotation"
	"""
	@classmethod
	def get_id(cls, context):
		return \
			43 if context.protocol_later_eq(756) else \
			41 if context.protocol_later_eq(736) else \
			43 if context.protocol_later_eq(578) else \
			42 if context.protocol_later_eq(498) else \
			40 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Rotation'


class EntityTeleportPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			98 if context.protocol_later_eq(757) else \
			97 if context.protocol_later_eq(756) else \
			86 if context.protocol_later_eq(736) else \
			87 if context.protocol_later_eq(578) else \
			86 if context.protocol_later_eq(498) else \
			76 if context.protocol_later_eq(340) else \
			75 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Teleport'


class EntityStatusPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			27 if context.protocol_later_eq(756) else \
			26 if context.protocol_later_eq(736) else \
			28 if context.protocol_later_eq(578) else \
			27 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Status'


class RemoveEntityStatusPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			59 if context.protocol_later_eq(756) else \
			55 if context.protocol_later_eq(736) else \
			57 if context.protocol_later_eq(578) else \
			56 if context.protocol_later_eq(498) else \
			51 if context.protocol_later_eq(340) else \
			50 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Remove Entity Effect'


class EntityHeadLookPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			62 if context.protocol_later_eq(756) else \
			58 if context.protocol_later_eq(736) else \
			60 if context.protocol_later_eq(578) else \
			59 if context.protocol_later_eq(498) else \
			54 if context.protocol_later_eq(340) else \
			53 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Head Look'


class EntityMetadataPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			77 if context.protocol_later_eq(756) else \
			68 if context.protocol_later_eq(578) else \
			67 if context.protocol_later_eq(498) else \
			60 if context.protocol_later_eq(340) else \
			59 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Metadata'


# see pycraft minecraft.networking.packets.clientbound.play.EntityVelocityPacket
#
# class EntityVelocityPacket(AbstractEntityPacket):
# 	@classmethod
# 	def get_id(cls, context):
# 		return \
# 			79 if context.protocol_later_eq(756) else \
# 			70 if context.protocol_later_eq(578) else \
# 			69 if context.protocol_later_eq(498) else \
# 			62 if context.protocol_later_eq(340) else \
# 			61 if context.protocol_later_eq(335) else \
# 			-1
#
# 	packet_name = 'Entity Velocity'


class EntityEquipmentPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			80 if context.protocol_later_eq(756) else \
			71 if context.protocol_later_eq(578) else \
			70 if context.protocol_later_eq(498) else \
			63 if context.protocol_later_eq(340) else \
			62 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Equipment'


class EntityEffectPacket(AbstractEntityPacket):
	@classmethod
	def get_id(cls, context):
		return \
			101 if context.protocol_later_eq(757) else \
			100 if context.protocol_later_eq(756) else \
			89 if context.protocol_later_eq(736) else \
			90 if context.protocol_later_eq(578) else \
			89 if context.protocol_later_eq(498) else \
			79 if context.protocol_later_eq(340) else \
			78 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Effect'


class EntitySoundEffectPacket(AbstractEntityPacket):
	"""
	1.14+
	"""
	@classmethod
	def get_id(cls, context):
		return \
			92 if context.protocol_later_eq(757) else \
			91 if context.protocol_later_eq(756) else \
			80 if context.protocol_later_eq(736) else \
			81 if context.protocol_later_eq(578) else \
			80 if context.protocol_later_eq(498) else \
			-1 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Sound Effect'


class EntityAnimationS2CPacket(AbstractEntityPacket):
	"""
	1.14+
	"""
	@classmethod
	def get_id(cls, context):
		return \
			6 if context.protocol_later_eq(756) else \
			5 if context.protocol_later_eq(736) else \
			6 if context.protocol_later_eq(498) else \
			-1 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Entity Animation (clientbound)'


PACKETS = packet_util.gather_all_packet_classes(globals().values())
