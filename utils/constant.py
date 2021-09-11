# coding: utf8
import os
from . import pycraft

Version = '0.11.2-alpha'
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
ALLOWED_VERSIONS = ['1.12', '1.12.2', '1.14.4', '1.15.2', '1.16.1', '1.16.2', '1.16.3', '1.16.4', '1.17.1']
Map_VersionToProtocol = pycraft.SUPPORTED_MINECRAFT_VERSIONS
Map_ProtocolToVersion = {}
for item in Map_VersionToProtocol.items():
	Map_ProtocolToVersion[item[1]] = item[0]

EntityTypeItem = {
	'1.12': 2,
	'1.12.2': 2,
	'1.14.4': 34,
	'1.15.2': 35,
	'1.16.1': 35,
	'1.16.2': 35,
	'1.16.3': 35,
	'1.16.4': 35,
	'1.17.1': 41,
}
EntityTypeBat = {
	'1.12': 65,
	'1.12.2': 65,
	'1.14.4': 3,
	'1.15.2': 3,
	'1.16.1': 3,
	'1.16.2': 3,
	'1.16.3': 3,
	'1.16.4': 3,
	'1.17.1': 4,
}
EntityTypePhantom = {
	'1.12': -1,
	'1.12.2': -1,
	'1.14.4': 97,
	'1.15.2': 98,
	'1.16.1': 58,
	'1.16.2': 58,
	'1.16.3': 58,
	'1.16.4': 58,
	'1.17.1': 63,
}

FILE_FORMAT_VERSION_DICT = {
	'1.12': '6',
	'1.12.2': '9',
	'1.14.4': '14',
	'1.15.2': '14',
	'1.16.1': '14',
	'1.16.2': '14',
	'1.16.3': '14',
	'1.16.4': '14',
	'1.17.1': '14',
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
	'Sculk Vibration Signal',
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
	# Chat Message is useful sometime, and it doens't take that much spaces
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

