import os
import time
import json
import utils
import select
import zipfile
import datetime
from packet import *


def run(config, email, password, debug, address):
    access_token, uuid, user_name = utils.get_token(email, password)
    clientbound, serverbound, protocol_version, mc_version = utils.generate_protocol_table(address)
    connection = utils.login(address, protocol_version, debug, access_token, uuid, user_name)
    print(clientbound)
    start_time = int(time.time() * 1000)
    last_player_movement = start_time
    entity_packets = ['Entity', 'Entity Relative Move', 'Entity Look And Relative Move', 'Entity Look',
                      'Entity Teleport']
    player_uuids = []
    player_ids = []
    blocked_entity_ids = []
    opped_players = []
    write_buffer = bytearray()
    file_size = 0
    afk_time = 0
    last_t = 0
    open('recording.tmcpr', 'w').close()  # Cleans recording file
    time.sleep(0.5)
    utils.request_ops(connection, serverbound)  # Request op list once
    if 'Time Update' in utils.BAD_PACKETS: utils.BAD_PACKETS.remove('Time Update')

    # Main processing loop for incoming data.
    while True:
        ready_to_read = select.select([connection.socket], [], [], 0)[0]
        if ready_to_read:
            t = int(time.time() * 1000)
            packet_in = connection.receive_packet()
            packet_recorded = int(t - start_time - afk_time).to_bytes(4, byteorder='big', signed=True)
            packet_recorded += len(packet_in.received).to_bytes(4, byteorder='big', signed=True)
            packet_recorded += packet_in.received
            packet_id = packet_in.read_varint()
            packet_name = clientbound[str(packet_id)]
            if debug:
                print('P Packet ' + hex(packet_id) + ': ' + packet_name)

            # Answer keep aLive
            if packet_name == 'Keep Alive (clientbound)':
                packet_out = Packet()
                packet_out.write_varint(serverbound['Keep Alive (serverbound)'])
                if protocol_version > 338:  # For some unnecessary reason keepalive changes to long after 1.12.1
                    id = packet_in.read_long()
                    packet_out.write_long(id)
                else:
                    id = packet_in.read_varint()
                    packet_out.write_varint(id)
                connection.send_packet(packet_out)

            # Respawn when dead
            if packet_name == 'Update Health':
                health = packet_in.read_float()
                food = packet_in.read_varint()
                food_sat = packet_in.read_float()
                if health == 0.0:
                    packet_out = Packet()
                    packet_out.write_varint(serverbound['Client Status'])
                    packet_out.write_varint(0)
                    connection.send_packet(packet_out)

            # If configured set daytime once and ignore all further time updates
            if (24000 > config['daytime'] > 0 and packet_name == 'Time Update' and not
            utils.is_bad_packet(packet_name, config['minimal_packets'])):
                print('Set daytime to: ' + str(config['daytime']))
                packet_daytime = Packet()
                packet_daytime.write_varint(
                    int(list(clientbound.keys())[list(clientbound.values()).index('Time Update')]))
                world_age = packet_in.read_long()
                packet_daytime.write_long(world_age)
                packet_daytime.write_long(
                    -config['daytime'])  # If negative sun will stop moving at the Math.abs of the time
                packet_recorded = int(t - start_time).to_bytes(4, byteorder='big', signed=True)
                packet_recorded += len(packet_daytime.received).to_bytes(4, byteorder='big', signed=True)
                packet_recorded += packet_daytime.received
                write_buffer += packet_recorded
                utils.BAD_PACKETS.append('Time Update')  # Ignore all further updates

            # Remove weather if configured
            if not config['weather'] and packet_name == 'Change Game State':
                reason = packet_in.read_ubyte()
                if reason == 1 or reason == 2:
                    packet_recorded = ''

            # Teleport confirm
            if packet_name == 'Player Position And Look (clientbound)':
                x = packet_in.read_double()
                y = packet_in.read_double()
                z = packet_in.read_double()
                yaw = packet_in.read_float()
                pitch = packet_in.read_float()
                flag = packet_in.read_byte()
                teleport_id = packet_in.read_varint()
                packet_out = Packet()
                packet_out.write_varint(serverbound['Teleport Confirm'])
                packet_out.write_varint(teleport_id)
                connection.send_packet(packet_out)

            # Update player list for metadata and player tracking
            if packet_name == 'Spawn Player':
                entity_id = packet_in.read_varint()
                if entity_id not in player_ids:
                    player_ids.append(entity_id)
                uuid = packet_in.read_uuid()
                if uuid not in player_uuids:
                    player_uuids.append(uuid)
                last_player_movement = int(time.time() * 1000)

            # Keep track of spawned items and their ids
            if ((config['remove_items'] or config['remove_bats']) and
                    (packet_name == 'Spawn Object' or packet_name == 'Spawn Mob')):
                entity_id = packet_in.read_varint()
                uuid = packet_in.read_uuid()
                type = packet_in.read_byte()
                if ((packet_name == 'Spawn Object' and type == 2) or
                        (packet_name == 'Spawn Mob' and type == 65)):
                    blocked_entity_ids.append(entity_id)
                    packet_recorded = ''

            # Remove item pickup animation packet
            if config['remove_items'] and packet_name == 'Collect Item':
                packet_recorded = ''

            # Detecting player activity to continue recording and remove items or bats
            if packet_name in entity_packets:
                entity_id = packet_in.read_varint()
                if config['recording'] and entity_id in player_ids:
                    last_player_movement = t
                if entity_id in blocked_entity_ids:
                    recorded_packet = ''

            # Record all "joining" or "leaving" tab updates to properly start recording players
            if packet_name == 'Player List Item':
                action = packet_in.read_varint()
                if config['recording'] and action == 0:  # int(time.time() * 1000) - last_player_movement <= 5000 and
                    write_buffer += packet_recorded
                    player_number = packet_in.read_varint()
                    uuid = packet_in.read_uuid()
                    name = packet_in.read_utf()

            # Handle chat and process ingame commands
            if packet_name == 'Chat Message (clientbound)':
                try:  # For whatever reason there sometimes exists an empty chat packet..
                    chat = packet_in.read_utf()
                    chat = json.loads(chat)
                    if chat['translate'] == 'chat.type.text':
                        name = chat['with'][0]['hoverEvent']['value']['text'].split('"')[1]
                        uuid = chat['with'][0]['hoverEvent']['value']['text'].split('"')[3]
                        message = chat['with'][1]
                        if name in opped_players:
                            print('<' + name + '(OP)> ' + message)
                            if message == '!relog':
                                should_restart = True
                                print('Relogging...')
                                break
                            if message == '!stop':
                                should_restart = False
                                print('Stopping...')
                                break
                            if message == '!ping':
                                utils.send_chat_message(connection, serverbound, 'pong!')
                            if message == '!filesize':
                                utils.send_chat_message(connection, serverbound,
                                                        str(round(file_size / 1000000, 1)) + 'MB')
                            if message == '!time':
                                utils.send_chat_message(connection, serverbound,
                                                        'Recorded time: ' + utils.convert_millis(
                                                            t - start_time - afk_time))
                            if message == '!timeonline':
                                utils.send_chat_message(connection, serverbound,
                                                        'Time client was online: ' + utils.convert_millis(
                                                            t - start_time))
                            if message == '!move':
                                packet_out = Packet()
                                packet_out.write_varint(serverbound['Spectate'])
                                packet_out.write_uuid(uuid)
                                connection.send_packet(packet_out)
                                utils.send_chat_message(connection, serverbound, 'moved to ' + name)
                            if message == '!glow':
                                utils.send_chat_message(connection, serverbound,
                                                        '/effect @p minecraft:glowing 1000000 0 true')
                        else:
                            print('<' + name + '> ' + message)
                except:
                    pass

            # Process the requested list of opped players
            if packet_name == 'Tab-Complete (clientbound)':
                count = packet_in.read_varint()
                matches = []
                for i in range(0, count):
                    matches.append(packet_in.read_utf())
                for match in matches:
                    if match not in opped_players:
                        opped_players.append(match)

            # Actual recording
            if (config['recording'] and t - last_player_movement <= 5000 and not
            utils.is_bad_packet(packet_name, config['minimal_packets'])):
                # To prevent constant writing to the disk a buffer of 8kb is used
                if packet_recorded != '':
                    write_buffer += packet_recorded
                if len(write_buffer) > 8192:
                    with open('recording.tmcpr', 'ab+') as replay_recording:
                        replay_recording.write(write_buffer)
                        if debug:
                            print('Recorded:' + str(write_buffer)[:80] + '...')
                        file_size += len(write_buffer)
                        write_buffer = bytearray()

            # Prevent any kind of size increase due to packets beeing added to the buffer it gets cleared when not needed
            if not config['recording'] and len(write_buffer) > 0:
                write_buffer = bytearray()

            # Increase afk timer when recording stopped, afk timer prevents afk time in replays
            if config['recording'] and t - last_player_movement > 5000:
                afk_time += t - last_t

            last_t = t  # Save last packet timestamp for afk delta

            # Every 150mb the client restarts
            if config['recording'] and file_size > 150000000:
                print('Filesize limit reached!')
                utils.send_chat_message(connection, serverbound, 'Filesize limit reached, restarting...')
                should_restart = True
                time.sleep(1)
                break
                # Every 5h recording the the client restarts
            elif config['recording'] and t - start_time - afk_time > 1000 * 60 * 60 * 5:
                print('5h recording reached!')
                utils.send_chat_message(connection, serverbound, '5h recording reached, restarting...')
                should_restart = True
                time.sleep(1)
                break

        else:
            time.sleep(0.001)  # Release to prevent 100% cpu usage

    # Handling the disconnect
    print('Disconnected')
    if config['recording'] and len(write_buffer) > 0:  # Finish writing if buffer not empty
        with open('recording.tmcpr', 'ab+') as replay_recording:
            replay_recording.write(write_buffer)
            write_buffer = bytearray()
    print('Time client was online: ' + utils.convert_millis(t - start_time))

    if config['recording']:
        print('Recorded time: ' + utils.convert_millis(t - start_time - afk_time))

        # Create metadata file
        with open('metaData.json', 'w') as json_file:
            meta_data = {'singleplayer': 'false', 'serverName': address[0],
                         'duration': int(time.time() * 1000) - start_time - afk_time, 'date': int(time.time() * 1000),
                         'mcversion': mc_version, 'fileFormat': 'MCPR', 'fileFormatVersion': '6', 'generator': 'SARC',
                         'selfId': -1, 'players': player_uuids}
            json.dump(meta_data, json_file)

        # Creating .mcpr zipfile based on timestamp
        print('Creating .mcpr file...')
        date = datetime.datetime.today().strftime('SARC_%Y%m%d_%H_%S')
        zipf = zipfile.ZipFile(date + '.mcpr', 'w', zipfile.ZIP_DEFLATED)
        zipf.write('metaData.json')
        zipf.write('recording.tmcpr')
        os.remove('metaData.json')
        os.remove('recording.tmcpr')
        print('Finished!')
    connection.close()
    return should_restart


config, email, password = utils.load_config()
debug = config['debug_mode']
address = (config['ip'], int(config['port']))
while True:
    #try:
    if not run(config, email, password, debug, address):
        break
    else:
        print('Reconnecting...')
   # except Exception as e:
    #    print('Connection lost: ' + str(e))
    #    if not config['auto_relog']:
    #        break
    #    else:
    #        print('Reconnecting...')
    time.sleep(3)
print('Ending...')
