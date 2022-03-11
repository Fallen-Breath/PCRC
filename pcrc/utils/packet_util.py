import inspect
from typing import Iterable, Any, Set, Type

from minecraft.networking.packets import Packet, PlayerListItemPacket
from minecraft.networking.packets.clientbound.play import EntityPositionDeltaPacket, EntityVelocityPacket

IMPORTANT_PACKETS = (
	PlayerListItemPacket
)


def is_important(packet: Packet):
	return isinstance(packet, IMPORTANT_PACKETS)


def gather_all_packet_classes(global_values: Iterable[Any]) -> Set[Type[Packet]]:
	return set(filter(lambda o: isinstance(o, type) and o != Packet and issubclass(o, Packet) and not inspect.isabstract(o), global_values))


def is_entity_packet(packet: Packet) -> bool:
	from pcrc.packets.s2c.entity_packet import AbstractEntityPacket
	return hasattr(packet, 'entity_id') and isinstance(packet, (
		AbstractEntityPacket,
		EntityPositionDeltaPacket,
		EntityVelocityPacket
	))
