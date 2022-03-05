from typing import List

from minecraft.networking.packets import Packet
from minecraft.networking.types import VarInt, Byte, Float
from pcrc.packets.s2c import entity_packet
from pcrc.utils import packet_util


class DestroyEntitiesPacket(Packet):
	@classmethod
	def get_id(cls, context):
		return \
			58 if context.protocol_later_eq(756) else \
			54 if context.protocol_later_eq(736) else \
			56 if context.protocol_later_eq(578) else \
			55 if context.protocol_later_eq(498) else \
			50 if context.protocol_later_eq(340) else \
			49 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Destroy Entities'
	fields = 'entity_amount', 'entity_ids'

	entity_amount: int
	entity_ids: List[int]

	def read(self, file_object):
		self.entity_amount = VarInt.read(file_object)
		self.entity_ids = []
		for i in range(self.entity_amount):
			self.entity_ids.append(VarInt.read(file_object))

	def write_fields(self, packet_buffer):
		VarInt.send(self.entity_amount, packet_buffer)
		for entity_id in self.entity_ids:
			VarInt.send(entity_id, packet_buffer)


class ChangeGameStatePacket(Packet):
	@classmethod
	def get_id(cls, context):
		return \
			30 if context.protocol_later_eq(756) else \
			29 if context.protocol_later_eq(736) else \
			31 if context.protocol_later_eq(578) else \
			30 if context.protocol_later_eq(335) else \
			-1

	packet_name = 'Change Game State'

	reason: int
	value: float

	definition = [
		{'reason': Byte},
		{'value': Float}
	]


PACKETS = packet_util.gather_all_packet_classes(globals().values())
PACKETS |= entity_packet.PACKETS
if entity_packet.AbstractEntityPacket in PACKETS:
	raise RuntimeError()

