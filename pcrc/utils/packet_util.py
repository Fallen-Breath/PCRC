import inspect
from typing import Iterable, Any, Set, Type

from minecraft.networking.packets import Packet, PlayerListItemPacket

IMPORTANT_PACKETS = (
	PlayerListItemPacket
)


def is_important(packet: Packet):
	return isinstance(packet, IMPORTANT_PACKETS)


def gather_all_packet_classes(global_values: Iterable[Any]) -> Set[Type[Packet]]:
	return set(filter(lambda o: isinstance(o, type) and o != Packet and issubclass(o, Packet) and not inspect.isabstract(o), global_values))

