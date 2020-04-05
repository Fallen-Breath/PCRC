import os
import time
import zlib

from . import pycraft

Version = '0.9.0-alpha'
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
ALLOWED_VERSIONS = ['1.12', '1.12.2', '1.14.4']
Map_VersionToProtocol = pycraft.SUPPORTED_MINECRAFT_VERSIONS
Map_ProtocolToVersion = {}
for item in Map_VersionToProtocol.items():
	Map_ProtocolToVersion[item[1]] = item[0]


def get_path(file):
	for path in ROOT_PATH:
		p = os.path.join(path, file)
		if os.path.isdir(p) or os.path.isfile(p):
			return p


def crc32_file(fn):
	BUFFER_SIZE = BytePerMB
	crc = 0
	with open(fn, 'rb') as f:
		while True:
			buffer = f.read(BUFFER_SIZE)
			if len(buffer) == 0:
				break
			crc = zlib.crc32(buffer, crc)
	return crc & 0xffffffff


def get_meta_data(server_name, duration, date, mcversion, protocol, player_uuids):
	map_fileFormatVersion = {
		'1.12': '6',
		'1.12.2': '9',
		'1.14.4': '14'
	}
	if player_uuids is None:
		player_uuids = []
	fileFormatVersion = map_fileFormatVersion[mcversion]
	meta_data = {
		'singleplayer': False,
		'serverName': server_name,
		'duration': duration,
		'date': date,
		'mcversion': mcversion,
		'fileFormat': 'MCPR',
		'fileFormatVersion': fileFormatVersion,
		'protocol': protocol,
		'generator': 'PCRC',
		'selfId': -1,
		'players': player_uuids
	}
	return meta_data


# convert file size to MB
def convert_file_size_MB(file_size):
	return format(file_size / 1024 / 1024, '.2f')


# convert file size to KB
def convert_file_size_KB(file_size):
	return format(file_size / 1024, '.2f')


def getMilliTime():
	return int(time.time() * 1000)


def format_vector(vec, f='.2f'):
	return '({}, {}, {})'.format(format(vec.x, f), format(vec.y, f), format(vec.z, f))


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
	'Entity',
	'Entity Relative Move',
	'Entity Look And Relative Move',
	'Entity Look',
	'Entity Teleport'
]


# Returns a string like h:m for given millis
def convert_millis(millis):
	seconds = int(millis / 1000) % 60
	minutes = int(millis / (1000 * 60)) % 60
	hours = int(millis / (1000 * 60 * 60))
	if seconds < 10:
		seconds = '0' + str(seconds)
	if minutes < 10:
		minutes = '0' + str(minutes)
	if hours < 10:
		hours = '0' + str(hours)
	return str(hours) + ':' + str(minutes) + ':' + str(seconds)
