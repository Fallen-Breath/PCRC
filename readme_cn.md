PCRC
--------

[English](https://github.com/Fallen-Breath/PCRC/blob/master/readme.md)

> 基于 PyCraft 的 Replay 客户端

~~SARC在 1.13 后跑不起来了，所以我搓了个这个东西~~

这是一个 Minecraft 客户端，它可以录制出能被 [Replay Mod](https://www.replaymod.com/) 识别的录像文件（*.mcpr）

非常感谢 [SARC](https://github.com/Robitobi01/SARC) 提供了 replay 相关的逻辑处理部分与 [pyCraft](https://github.com/ammaraskar/pyCraft) 提供了 Minecraft 客户端相关的东西

## 环境要求

Python 的版本需要 python3，至少它在 Python 3.6 与 Python 3.8 中能运行

### Python 模块

- cryptography
- requests
- future
- PyYAML

所需的模块也已储存在 `requirements.txt` 中

### Minecraft 服务器

PCRC 目前支持连接官服原版 Minecraft 服务端，支持以下版本：

- 1.12
- 1.12.2
- 1.14.4
- 1.15.2

## 优势

- 可以在托管在服务端上 24/7 录制
- 资源占用远小于普通 Minecraft 客户端
- 可以设置为仅在玩家在附近时进行录制
- 有多个选项可以设置以满足多种录制需求
- 在原始录像文件大于 2048MB 后或者录制时长大于 5 小时后自动重启以防止录像文件过长
- 由于录制所用虚拟玩家（机器人）不会进行移动，录像文件中将不会包含无用的区块加载相关数据包从而能有效减小录像文件大小

## 使用方法

1. 在 [Release](https://github.com/Fallen-Breath/PCRC/releases) 页面中下载最新的 PCRC 并解压
2. 按需求填写配置文件 `config.json`
3. 运行 `PCRC.py` 或 `PCRC.exe`
4. 在控制台中输入指令 `start` 以启动 PCRC
5. （**推荐**）将 PCRC 机器人切换为旁观者模式
6. 使用控制台或游戏内聊天来控制 PCRC
## 配置文件

配置文件为 `config.json`，所有设置均可在其中更改。其中名为如 `__1__` 的为分隔符，无需修改

### 基本设置

`language`: PCRC 机器人使用的语言。语言文件需放置于 `lang/`

`debug_mode`: 是否输出调试信息

### 账号与服务器

`online_mode`: 是否使用正版登录

`username`: 用于盗版登录的玩家id，或者是用于正版登录的 Minecraft 账号的邮箱

`password`: 用于正版登录时的 Minecraft 账号的密码

`address`: Minecraft 服务器的 IP 地址

`port`: Minecraft 服务器的端口

`server_name`: replay 回放中心内显示的服务器名称

`initial_version`: 首选的用于连接至类似 Bungeecord 的 Minecraft 版本

### PCRC 设置

`file_size_limit_mb`: `.tmcpr` 文件的大小限制。每当达到这个限制时 PCRC 将会重启，单位: MB。默认值: `2048`

`file_buffer_size_mb`: 文件缓冲区的大小限制。每当达到这个限制时 PCRC 将会将缓冲区的内容输出至 `.tmcpr` 文件，单位: MB。默认值: `8`
    
`time_recorded_limit_hour`: 录制时长的限制。每当达到这个限制时 PCRC 将会重启，单位: 小时。默认值: `12`
    
`delay_before_afk_second`:  所有人都离开与暂停录制间的延迟，单位: 秒。默认值: `15`

`record_packets_when_afk`: 若设为 `false`，PCRC 将会在暂停录制时忽略几乎所有到来的数据包（SARC 的行为）

`auto_relogin`: 当客户端掉线时是否自动重连。若为 `true`，PCRC 会在掉线后尝试重连

`chat_spam_protect`: 是否在必要时自动延迟发送聊天消息，以防止被因滥发消息而踢出游戏

`command_prefix`: 任何以 `command_prefix` 开头的聊天信息将会被认为是控制 PCRC 的指令。默认值: `!!PCRC`

### PCRC 特性

`minimal_packets`: 在这个选项设为 `true` 时 PCRC会仅录制能能维持录制的最小数量的数据包。 可用于在录制超长时间延迟摄影时减小文件大小

`daytime`: 将游戏时间设置为一个固定值并忽略之后所有的时间变化。将其设为 `-1` 以录制正常的昼夜循环

`weather`: 是否录制天气

`with_player_only`: 是否只当玩家在附近时才进行录制

`remove_items`: 是否不录制掉落物

`remove_bats`: 是否不录制蝙蝠

`remove_phantoms`: 是否不录制幻翼

## 指令

指令前缀 `!!PCRC` 可在配置文件中自定义

### 控制台指令

`start`: 开启PCRC 并开始录制

`stop`: 停止 PCRC 并关闭录制

`restart`: 重启 PCRC

`exit`: 退出程序

`say <信息>`: 将文字 `<信息>` 作为聊天信息发送至服务器

`set <选项> <值>` 将 PCRC 与配置文件中的 <选项> 设置为 <值>

`!!PCRC <命令> [<命令的参数>]` 同使用游戏中指令一样的效果

### 游戏内指令

使用游戏内的聊天来触发命令

`!!PCRC`: 显示帮助信息	

`!!PCRC status`: 显示状态

`!!PCRC here`: 发送一个“!!here”指令

`!!PCRC pos`: 显示所处位置，不一定 100% 准确

`!!PCRC spec`: 使用旁观者模式的传送能力来传送至发送指令的玩家

`!!PCRC stop`: 关闭 PCRC

`!!PCRC restart`: 重启 PCRC

`!!PCRC set`: 输出所有可设置的选项

`!!PCRC set` <选项> <值>: 将<选项>设置为<值>，不会写入配置文件

## 注意事项

- PCRC 内无处理游戏内容相关代码，因此在移动 PCRC 机器人时仅可使用诸如 `!!PCRC spec` 或 `/tp` 等传送类指令，不可使用活塞等方式移动机器人。否则可能出现机器人隐身等 bug
- PCRC 录制时显示的文件大小为 `.tmcpr` 文件，即未压缩的原始数据包文件的大小，并非最终文件 `.mcpr` 的大小。视情况不同最终文件大小大约为原始数据包文件大小的 10% ~ 40%
