from typing import NamedTuple, List

import minecraft
from minecraft import KNOWN_MINECRAFT_VERSIONS
from minecraft.networking.connection import ConnectionContext


class Protocol(NamedTuple):
	mc_version: str
	protocol_number: int

	@classmethod
	def from_mc_version(cls, mc_version: str) -> 'Protocol':
		return Protocol(mc_version=mc_version, protocol_number=KNOWN_MINECRAFT_VERSIONS[mc_version])


MC_1_12   = Protocol.from_mc_version('1.12')
MC_1_12_2 = Protocol.from_mc_version('1.12.2')
MC_1_14_4 = Protocol.from_mc_version('1.14.4')
MC_1_15_2 = Protocol.from_mc_version('1.15.2')
MC_1_16_1 = Protocol.from_mc_version('1.16.1')
MC_1_16_2 = Protocol.from_mc_version('1.16.2')
MC_1_16_3 = Protocol.from_mc_version('1.16.3')
MC_1_16_4 = Protocol.from_mc_version('1.16.4')
MC_1_16_5 = Protocol.from_mc_version('1.16.5')
MC_1_17_1 = Protocol.from_mc_version('1.17.1')
MC_1_18   = Protocol.from_mc_version('1.18')
MC_1_18_1 = Protocol.from_mc_version('1.18.1')
MC_1_18_2 = Protocol.from_mc_version('1.18.2')

ALL_PROTOCOL: List[Protocol] = list(filter(lambda o: isinstance(o, Protocol), globals().values()))
SUPPORTED_MINECRAFT_VERSIONS: List[str] = list(map(lambda p: p.mc_version, ALL_PROTOCOL))
SUPPORTED_PROTOCOL_VERSIONS: List[int] = list(map(lambda p: p.protocol_number, ALL_PROTOCOL))


def get_mc_version(protocol_version: int) -> str:
	for v, p in minecraft.SUPPORTED_MINECRAFT_VERSIONS.items():
		if p == protocol_version:
			return v
	return 'unknown ({})'.format(protocol_version)


class MobTypeIds:
	# https://wiki.vg/Entity_metadata#Mobs

	@staticmethod
	def item(context: ConnectionContext) -> int:
		return \
			41 if context.protocol_later_eq(MC_1_17_1.protocol_number) else \
			35 if context.protocol_later_eq(MC_1_15_2.protocol_number) else \
			34 if context.protocol_later_eq(MC_1_14_4.protocol_number) else \
			2 if context.protocol_later_eq(MC_1_12_2.protocol_number) else \
			-1

	@staticmethod
	def bat(context: ConnectionContext) -> int:
		return \
			4 if context.protocol_later_eq(MC_1_17_1.protocol_number) else \
			3 if context.protocol_later_eq(MC_1_14_4.protocol_number) else \
			65 if context.protocol_later_eq(MC_1_12_2.protocol_number) else \
			-1

	@staticmethod
	def phantom(context: ConnectionContext) -> int:
		return \
			63 if context.protocol_later_eq(MC_1_17_1.protocol_number) else \
			58 if context.protocol_later_eq(MC_1_16_1.protocol_number) else \
			98 if context.protocol_later_eq(MC_1_15_2.protocol_number) else \
			97 if context.protocol_later_eq(MC_1_14_4.protocol_number) else \
			-1
