from threading import Lock
from typing import Set

from redbaron import RedBaron, IfelseblockNode, AssignmentNode, WithNode

from pcrc.utils import redbaron_util

__patch_lock = Lock()
__patched = False


def patch_pycraft():
	global __patched
	with __patch_lock:
		if __patched:
			return
		__patched = True

	print('Patching PyCraft...')

	__extends_protocol_version_range()
	__player_position_fix()
	__custom_s2c_packet_registering()
	__network_thread_running_state_hook()
	__default_proto_version_inject()
	__playing_reactor_switch_listener()
	__raw_packet_recording()

	print('Patched PyCraft')


def __extends_protocol_version_range():
	import minecraft
	minecraft.KNOWN_MINECRAFT_VERSION_RECORDS.append(minecraft.Version('1.18.2', 758, True))
	minecraft.initglobals(use_known_records=True)


def __player_position_fix():
	from minecraft.networking.connection import PlayingReactor
	from minecraft.networking.packets import PositionAndLookPacket

	def patched_PlayingReactor_react(self, packet):
		original_react(self, packet)
		if packet.packet_name == "player position and look" and self.connection.context.protocol_later_eq(107):
			position_response = PositionAndLookPacket()
			position_response.x = packet.x
			position_response.feet_y = packet.y
			position_response.z = packet.z
			position_response.yaw = packet.yaw
			position_response.pitch = packet.pitch
			position_response.on_ground = True
			self.connection.write_packet(position_response)

	original_react = PlayingReactor.react
	PlayingReactor.react = patched_PlayingReactor_react


def __custom_s2c_packet_registering():
	from pcrc.packets import s2c
	from minecraft.networking.connection import PlayingReactor
	from minecraft.networking.packets import Packet

	def patched_get_packets(context):
		packets: Set[Packet] = original_get_packets(context)
		packets |= s2c.PACKETS
		return packets

	original_get_packets = PlayingReactor.get_clientbound_packets
	PlayingReactor.get_clientbound_packets = staticmethod(patched_get_packets)


def __network_thread_running_state_hook():
	from minecraft.networking.connection import NetworkingThread
	from pcrc.connection.pcrc_connection import PcrcConnection

	def patched_network_thread_run(self):
		if isinstance(self, PcrcConnection):
			self.add_running_networking_thread_amount(1)
		try:
			original_network_thread_run(self)
		finally:
			if isinstance(self, PcrcConnection):
				self.add_running_networking_thread_amount(-1)

	original_network_thread_run = NetworkingThread.run
	NetworkingThread.run = patched_network_thread_run


def __default_proto_version_inject():
	"""
	modified the value to default_proto_version if there are multiple allow version
	"""
	import minecraft.networking.connection as connection
	from minecraft.networking.connection import Connection

	red, connection_class = redbaron_util.read_class(Connection)
	connect_method = redbaron_util.get_def(connection_class, 'connect')
	main_with = redbaron_util.get_node(connect_method, node_type=WithNode)
	idx = redbaron_util.get_node_index(main_with, node_type=AssignmentNode, predicate=lambda n: str(n.target) == 'self.spawned')
	redbaron_util.insert_nodes(main_with, idx, [
		RedBaron('''self.pcrc.logger.info('Allowed server versions: {}'.format(self.allowed_proto_versions))'''),
		RedBaron('''if len(self.allowed_proto_versions) > 1: self.context.protocol_version = self.default_proto_version''')
	])

	# idk why but this thing prevents IndentationError from method _connect from happening
	connect_method.value.insert(0, 'pass')

	patched_class_source = red.dumps()
	globals_ = dict(connection.__dict__)
	exec(patched_class_source, globals_)
	PatchedConnection = globals_['Connection']
	Connection.connect = PatchedConnection.connect


def __playing_reactor_switch_listener():
	from minecraft.networking.connection import LoginReactor, PlayingReactor
	from pcrc.connection.pcrc_connection import PcrcConnection

	def patched_network_thread_run(self, packet):
		original_login_reactor_react(self, packet)
		if isinstance(self.connection.reactor, PlayingReactor) and isinstance(self.connection, PcrcConnection):
			self.connection.pcrc.on_switched_to_playing_reactor()

	original_login_reactor_react = LoginReactor.react
	LoginReactor.react = patched_network_thread_run


def __raw_packet_recording():
	import minecraft.networking.connection as connection
	from minecraft.networking.connection import PacketReactor

	red, packet_reactor_class = redbaron_util.read_class(PacketReactor)
	packet_reactor_class.name = 'PatchedPacketReactor'
	read_packet_method = redbaron_util.get_def(packet_reactor_class, 'read_packet')
	main_if_else_node = redbaron_util.get_node(read_packet_method, node_type=IfelseblockNode, error_msg='Cannot found if-else block in PacketReactor#read_packet')
	main_if_body_nodes = main_if_else_node.value[0]
	for i, node in enumerate(main_if_body_nodes):
		if isinstance(node, AssignmentNode) and node.target.value == 'packet_id':
			main_if_body_nodes.insert(i, 'packet_raw = copy.deepcopy(packet_data.bytes.getvalue())')
			main_if_body_nodes.insert(i, 'import copy')
			break
	else:
		raise Exception('Cannot found packet_id assignment node in PacketReactor#read_packet')
	main_if_body_nodes.insert(len(main_if_body_nodes) - 1, 'packet.raw_data = packet_raw')

	patched_class_source = red.dumps()
	# print(patched_class_source)

	globals_ = dict(connection.__dict__)
	exec(patched_class_source, globals_)
	PatchedPacketReactor = globals_['PatchedPacketReactor']
	PacketReactor.read_packet = PatchedPacketReactor.read_packet
