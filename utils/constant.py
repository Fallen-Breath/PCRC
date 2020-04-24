# coding: utf8
import os
from . import pycraft

Version = '0.10.0-alpha'
ROOT_PATH = [
	os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', ''),  # I'm in ./utils/ folder so ../ might be the path
	'./',
]
MilliSecondPerHour = 60 * 60 * 1000
BytePerKB = 1024
BytePerMB = BytePerKB * 1024
MinimumLegalFileSize = 10 * BytePerKB
RecordingFilePath = 'temp_recording/'
RecordingStorageFolder = 'PCRC_recordings/'
ALLOWED_VERSIONS = ['1.12', '1.12.2', '1.14.4', '1.15.2']
Map_VersionToProtocol = pycraft.SUPPORTED_MINECRAFT_VERSIONS
Map_ProtocolToVersion = {}
for item in Map_VersionToProtocol.items():
	Map_ProtocolToVersion[item[1]] = item[0]

EntityTypeItem = {
	'1.12': 2,
	'1.12.2': 2,
	'1.14.4': 34,
	'1.15.2': 35
}
EntityTypeBat = {
	'1.12': 65,
	'1.12.2': 65,
	'1.14.4': 3,
	'1.15.2': 3,
}
EntityTypePhantom = {
	'1.12': -1,
	'1.12.2': -1,
	'1.14.4': 97,
	'1.15.2': 98,
}


IMPORTANT_PACKETS = [
	'Player Info'
]

# from SARC

# Useless Packet Handling
# Packets that are ignored by ReplayMod dont get recorded to reduce filesize
# https://github.com/ReplayMod/ReplayMod/blob/8314803cda88a81ee16969e5ab89dabbd131c52e/src/main/java/com/replaymod/replay/ReplaySender.java#L79
BAD_PACKETS = [
	'Unlock Recipes',
	'Advancements',
	'Select Advancement Tab',
	'Update Health',
	'Open Window',
	'Close Window (clientbound)',
	'Set Slot',
	'Window Items',
	'Open Sign Editor',
	'Statistics',
	'Set Experience',
	'Camera',
	'Player Abilities (clientbound)',
	'Title',
	'unknown'
]

# List of packets that are not neccesary for a normal replay but still get recorded
# by ReplayMod. These packets get ignored with enabling "minimal_packets"
# wich is the preffered option for timelapses to reduced file size even further.
USELESS_PACKETS = [
	'Keep Alive (clientbound)',
	'Statistics',
	'Server Difficulty',
	'Tab-Complete (clientbound)',
	# it's useful sometime, and it doens't take that much spaces
	# 'Chat Message (clientbound)',
	'Confirm Transaction (clientbound)',
	'Window Property',
	'Set Cooldown',
	'Named Sound Effect',
	'Map',
	'Resource Pack Send',
	'Display Scoreboard',
	'Scoreboard Objective',
	'Teams',
	'Update Score',
	'Sound Effect'
]

ENTITY_PACKETS = [
	# 1.12+
	'Entity',
	'Entity Relative Move',
	'Entity Look And Relative Move',
	'Entity Look',
	'Entity Teleport'
	'Entity Status',
	'Remove Entity Effect',
	'Entity Head Look',
	'Entity Metadata',
	'Entity Velocity',
	'Entity Equipment',
	'Entity Teleport',
	'Entity Properties',
	'Entity Effect',

	# 1.14+
	'Entity Sound Effect',
	'Entity Movement',
	'Entity Rotation',
	'Entity Position and Rotation',
	'Entity Position',
	'Entity Animation (clientbound)',
]

