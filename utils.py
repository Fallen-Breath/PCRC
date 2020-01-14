import binascii
import os
import time

RecordingFileName = 'recording.tmcpr'
LoggingFileName = 'PCRC.log'
FileBufferSize = 10 * 1024 * 1024
FileSizeLimit = 500 * 1014 * 1024
CommandHelpMessage = '''----- Command List -----
!!PCRC: show help
!!PCRC status: show status
!!PCRC here: emit a "!!here" command
!!PCRC pos: show position, might not be 100% accurate
!!PCRC sepc: spectator teleport to the player
!!PCRC stop: stop PCRC
!!PCRC url: print all urls of recorded files
'''


def addFile(zip, fileName, str=None):
	if str != None:
		with open(fileName, 'w') as f:
			f.write(str)
	zip.write(fileName)
	os.remove(fileName)

def crc32(v):
	return binascii.crc32(v) & 0xffffffff

def crc32f(fn):
	with open(fn, 'rb') as f:
		return crc32(f.read())

# convert file size to MB
def convert_file_size(file_size):
	return format(file_size / 1024 / 1024, '.2f')

def getMilliTime():
	return int(time.time() * 1000)

def format_vector(vec, f='.2f'):
	return '({}, {}, {})'.format(format(vec.x, f), format(vec.y, f), format(vec.z, f))


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
	'Chat Message (clientbound)',
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
