PCRC
--------

[中文](https://github.com/Fallen-Breath/PCRC/blob/master/readme_cn.md)

> PyCraft based Replay Client

~~SARC doesn't work in 1.13+ version so I made this crap~~

A Minecraft client that can record a replay file (*.mcpr) which can be recognized by [Replay Mod](https://www.replaymod.com/)

Great thanks to [SARC](https://github.com/Robitobi01/SARC) for the replay logic stuffs and [pyCraft](https://github.com/ammaraskar/pyCraft) for the minecraft client stuffs

## Environment

Python version should be python3 and at least it works on Python 3.6 and Python 3.8

### Python modules

- cryptography
- requests
- future
- PyYAML

The requirements are also stored in `requirements.txt`

### Minecraft server

PCRC currently supports connecting to vanilla Minecraft server. Supports versions:

- 1.12
- 1.12.2
- 1.14.4
- 1.15.2

## Advantage

- Can be hosted server side for 24/7 recording
- It can be set to record only when the player is nearby
- Multiple options can be set for custom recording
- Restart after raw file size reaches 2048MB or recording time reaches 5 hours to prevent oversize recording
- Since the virtual player (bot) doesn't move, the recording file will not include unnecessary packets related to chunk loading, which can significantly reduce recording file size

## Usage

1. Download and unzip the latest PCRC in [Release](https://github.com/Fallen-Breath/PCRC/releases) page
2. Fill in the `config.json` file on demand
3. Run `PCRC.py` or `PCRC.exe`
4. Input `start` in the console to start PCRC
5. (**Recommand**) Set the gamemode of the PCRC bot to spectator
6. Use console or chat in game to control PCRC

## Config

The config file is `config.json`. All settings can be changed in it. Those which are similar to ABC inside it are just comments, don't need to modify them

### Base

`language`: The language that the PCRC bot will speak in the game. Language file should be in folder `lang/`

`debug_mode`: Whether outputs debug info or not

### Account and Server

`online_mode`: Use online mode to login or offline mode instead

`username`: Username for offline mode or email for the used Minecraft account

`password`: Password for the used Minecraft account if login in in online mode

`address`: IP Address of the Minecraft server

`port`: Port of the Minecraft server

`server_name`: The server name showed in replay viewer

`initial_version`: The preferred Minecraft version that used to connect to bungeecord like server

### PCRC Control

`file_size_limit_mb`: The limit of size of the `.tmcpr` file. Every time it is reached, PCRC will restart. Default: `2048`

`file_buffer_size_mb`: The limit of size of file buffer. Every time it is reached, PCRC will flush all content in the buffer into `.tmcpr` file. Default: `8`
    
`time_recorded_limit_hour`: The limit of actual recording time. Every time it is reached, PCRC will restart. Default: `12`
    
`delay_before_afk_second`: The time delay between every player leaving and PCRC pausing recording. Default: `15`

`record_packets_when_afk`: If set to false, PCRC will ignore almost every incoming packets when PCRC pauses recording (SARC's behavior)

`auto_relogin`: If this option is enabled and the client gets disconnected, it will automatically try to reconnect

`chat_spam_protect`: Automatically delay between sending chat messages if necessary to prevent being kicked for spamming

`command_prefix`: Any chat message starts with `command_prefix` will be recognize as a command to control PCRC. Default: `!!PCRC`

### PCRC Features

`minimal_packets`: PCRC will only record the minimum needed packets for a proper recording when this option is turned on. This should be used to decrease the filesize of recordings while recording long term projects (timelapse)

`daytime`: Sets the daytime once to the defined time in the recording and ignores all further changes from the server. If set to `-1` the normal day/night cycle is recorded

`weather`: Turns weather in the recording on or off

`with_player_only`: If set to true, PCRC only record packets if there are players nearby

`remove_items`: If set to true, all dropped items wont be recorded

`remove_bats`: If set to true, bats won't be recorded

`remove_phantoms`: If set to true, phantoms won't be recorded

### PCRC Whitelist

`enabled`: Whether to enable whitelist

`whitelist`: Whitelist player list

## Command

Command prefix `!!PCRC` can be customized in the config file

### Console Command

`start`: start PCRC and start recording

`stop`: stop PCRC and stop recording

`restart`: restart PCRC

`exit`: exit the program

`say <text>`: send text `<text>` to the server as a chat message

`set <option> <value>` set option to value of PCRC and in the config file

`whitelist <on|off>` Switch the whitelist switch

`whitelist <add|del> [<player>]` Add or delete a player to(from) the whitelist

`whitelist <status>` To view the status of the whitelist and the whitelisted player(s)

`!!PCRC <command> [<arguments>]` the same function as using in-game command

### In Game Command

Using normal in game chatting to trigger

`!!PCRC`: show help

`!!PCRC status`: show status

`!!PCRC here`: emit a "!!here" command

`!!PCRC pos`: show position, might not be 100% accurate

`!!PCRC spec`: use the teleport ability in spectator mode to teleport to the player who sent this command

`!!PCRC stop`: stop PCRC

`!!PCRC restart`: restart PCRC

`!!PCRC set`: print all settable option

`!!PCRC set <option> <value>`: set the value of `<option>` to `<value>` which won't write to config file

`!!PCRC name <filename>`: set recording file name to `<filename>`

## Notes

- There's not any code for processing game content in PCRC so if you want to move the PCRC bot you can only use teleport command like `!!PCRC spec` or `/tp`. You can not use stuffs like piston to move the bot otherwise some wired behaviors like the bot become invisible may occur
- The file size that PCRC shows when recording is the size of `.tmcpr` file, the uncompressed raw packet file size. It's not the size of the final recording file `.mcpr`. The final file size is about 10% to 40% of the original packet file size, depending on the situation
