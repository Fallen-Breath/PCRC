from threading import Lock
from typing import TYPE_CHECKING, Set

from redbaron import RedBaron, IfelseblockNode, AssignmentNode, WithNode

from minecraft.networking.connection import Connection, LoginReactor, PlayingReactor, PacketReactor, NetworkingThread
from minecraft.networking.packets import Packet, PositionAndLookPacket
from pcrc.utils import redbaron_util

if TYPE_CHECKING:
	from pcrc.pcrc_impl import PcrcImpl


class PcrcConnection(Connection):
	def __init__(self, *args, pcrc: 'PcrcImpl', **kwargs):
		super().__init__(*args, **kwargs)
		self.pcrc: 'PcrcImpl' = pcrc
		self.running_networking_thread = 0
		self.__running_networking_thread_lock = Lock()

	def add_running_networking_thread_amount(self, delta: int):
		with self.__running_networking_thread_lock:
			self.running_networking_thread += delta

	def connect(self):
		super().connect()
		if isinstance(self.reactor, LoginReactor):
			self.pcrc.on_protocol_version_decided(self.allowed_proto_versions.copy().pop())
	@staticmethod
	def patch():
		def player_position_fix():
			def patched_PlayingReactor_react(self, packet):
				original_react(self, packet)
				if packet.packet_name == "player position and look" and not self.connection.context.protocol_later_eq(107):
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

		def custom_s2c_packet_registering():
			from pcrc.packets import s2c

			def patched_get_packets(context):
				packets: Set[Packet] = original_get_packets(context)
				packets |= s2c.PACKETS
				return packets

			original_get_packets = PlayingReactor.get_clientbound_packets
			PlayingReactor.get_clientbound_packets = staticmethod(patched_get_packets)

		def network_thread_running_state_hook():
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

		def default_proto_version_inject():
			"""
			modified the value to default_proto_version if there are multiple allow version
			"""
			red, connection_class = redbaron_util.read_class(Connection)
			connect_method = redbaron_util.get_def(connection_class, 'connect')
			main_with = redbaron_util.get_node(connect_method, node_type=WithNode)
			idx = redbaron_util.get_node_index(main_with, node_type=AssignmentNode, predicate=lambda n: str(n.target) == 'self.spawned')
			redbaron_util.insert_nodes(main_with, idx, [
				RedBaron('''self.recorder.logger.info('Allow versions of the server: {}'.format(self.allowed_proto_versions))'''),
				RedBaron('''if len(self.allowed_proto_versions) > 1: self.context.protocol_version = self.default_proto_version''')
			])

			patched_class_source = connect_method.dumps()

			import minecraft.networking.connection as connection
			globals_ = dict(connection.__dict__)
			exec(patched_class_source, globals_)
			PatchedConnection = globals_['Connection']
			Connection.connect = PatchedConnection.connect

		def playing_reactor_switch_listener():
			def patched_network_thread_run(self, packet):
				original_login_reactor_react(self, packet)
				if isinstance(self.connection.reactor, PlayingReactor) and isinstance(self.connection, PcrcConnection):
					self.connection.pcrc.on_switched_to_playing_reactor()

			original_login_reactor_react = LoginReactor.react
			LoginReactor.react = patched_network_thread_run

		def raw_packet_recording():
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

			import minecraft.networking.connection as connection
			globals_ = dict(connection.__dict__)
			exec(patched_class_source, globals_)
			PatchedPacketReactor = globals_['PatchedPacketReactor']
			PacketReactor.read_packet = PatchedPacketReactor.read_packet

		player_position_fix()
		custom_s2c_packet_registering()
		network_thread_running_state_hook()
		default_proto_version_inject()
		playing_reactor_switch_listener()
		raw_packet_recording()


PcrcConnection.patch()
