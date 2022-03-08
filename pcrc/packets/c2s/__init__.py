from minecraft.networking.packets import Packet
from minecraft.networking.types import UUID
from pcrc.utils import packet_util


class SpectatePacket(Packet):
	@classmethod
	def get_id(cls, context):
		return \
			0x2D if context.protocol_later_eq(751) else \
			0x2C if context.protocol_later_eq(736) else \
			0x2B if context.protocol_later_eq(578) else \
			0x1E

	packet_name = 'Spectate'

	@classmethod
	def get_definition(cls, _context):
		return [{'target': UUID}]


PACKETS = packet_util.gather_all_packet_classes(globals().values())
