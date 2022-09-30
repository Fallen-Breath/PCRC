PCRC
--------

[English](readme.md) | **中文**

> 基于 PyCraft 的 Replay 客户端

这是一个 Minecraft 客户端，它可以录制出能被 [Replay Mod](https://www.replaymod.com/) 识别的录像文件（*.mcpr）

非常感谢 [SARC](https://github.com/Robitobi01/SARC) 提供了 replay 相关的逻辑处理部分与 [pyCraft](https://github.com/ammaraskar/pyCraft) 提供了 Minecraft 客户端相关的东西

## 环境要求

Python 的版本需要 python3，至少它在 Python 3.6 与 Python 3.8 中能运行

### Python 模块

- cryptography
- requests
- pynbt
- redbaron
- colorlog
- ruamel.yaml

所需的模块也已储存在 `requirements.txt` 中

### Minecraft 服务器

PCRC 目前支持连接官服原版 Minecraft 服务端，支持以下版本：

- 1.12 / 1.12.2
- 1.14.4
- 1.15.2
- 1.16.1 ~ 1.16.5
- 1.17.1
- 1.18 ~ 1.18.2

## 优势

- 可以在托管在服务端上 24/7 录制
- 资源占用远小于普通 Minecraft 客户端
- 可以设置为仅在玩家在附近时进行录制
- 有多个选项可以设置以满足多种录制需求
- 在原始录像文件大于 2048MB 后或者录制时长大于 5 小时后自动重启以防止录像文件过长
- 由于录制所用虚拟玩家（机器人）不会进行移动，录像文件中将不会包含无用的区块加载相关数据包从而能有效减小录像文件大小

## 使用方法

### 直接启动

1. 在 [Release](https://github.com/Fallen-Breath/PCRC/releases) 页面中下载最新的 PCRC
2. 执行 `python PCRC.pyz` 或 `PCRC.exe`
  - 首次启动时，PCRC 将生成默认配置文件并退出。按需填写配置文件，再启动
3. 在控制台中输入指令 `start` 以启动 PCRC
4. （**推荐**）将 PCRC 机器人切换为旁观者模式
5. 使用控制台或游戏内聊天来控制 PCRC

### 作为 MCDR 插件

需要 [MCDReforged](https://github.com/Fallen-Breath/MCDReforged) >= 2.0

将 [Release](https://github.com/Fallen-Breath/PCRC/releases) 中下载的 `PCRC.pyz` 文件放入 MCDR 的插件文件夹中即可

注意：卸载插件将导致 PCRC 停止录制并退出游戏

## 配置文件

配置文件为 `config.json`，所有设置均可在其中更改。其中名为如 `__1__` 的为分隔符，无需修改

当作为 MCDR 的插件时，配置文件的路径将为 `config/pcrc/config.json`，同时 `config/pcrc/mcdr_config.json` 将储存着与 MCDR 相关的配置

### 基本设置

`language`: PCRC 机器人使用的语言。语言文件需放置于 `lang/`

`recording_temp_file_directory`: 用于存放 PCRC 录制用临时文件的路径

`recording_storage_directory`: 用于存放完成的录制文件的路径

`debug_mode`: 是否输出调试信息

### 账号与服务器

`authenticate_type`: 账号登录的方式。它可为 `offline`、`mojang` 或 `microsoft`，分别对应盗版账号、Mojang 账号登录以及微软账号登录

  若使用微软账号登录，启动后首次连接至服务器时，需要按照控制台输出进行微软账号的登录

`username`: 用于盗版登录的玩家id，或者是用于 Mojang 账号登录的邮箱

`password`: 用于 Mojang 账号登录的密码

`store_token`: 当设为 true 且 `authenticate_type` 为 `microsoft` 时，微软账号登录所获取的令牌将被储存于文件 `token.json` 中。在启动 PCRC 时，该文件中的令牌将被使用，只要它还没过期。注意，令牌将以明文储存

帐户相关配置条目的例子：

```json5
// 使用盗版账号登录
{
    "authenticate_type": "offline",
    "username": "MyPlayerName",  // 你想指定的玩家名
    "password": "",  // 该条目的值不会被使用，将被忽略
}
```

```json5
// 使用 Mojang 账号登录
{
    "authenticate_type": "mojang",
    "username": "MyEmail@mail.com",  // 你的 Mojang 账号的邮箱
    "password": "mypassword",  // 你的 Mojang 账号的密码
}
```

```json5
// 使用微软账号登录
{
    "authenticate_type": "microsoft",
    "username": "",  // 该条目的值不会被使用，将被忽略
    "password": "",  // 该条目的值不会被使用，将被忽略
}
```

`address`: Minecraft 服务器的 IP 地址

`port`: Minecraft 服务器的端口

`server_name`: replay 回放中心内显示的服务器名称

`initial_version`: 首选的用于连接至类似 Bungeecord 的 Minecraft 版本

### PCRC 设置

`file_size_limit_mb`: `.tmcpr` 文件的大小限制。每当达到这个限制时 PCRC 将会重启，单位: MB。默认值: `2048`

`file_buffer_size_mb`: 文件缓冲区的大小限制。每当达到这个限制时 PCRC 将会将缓冲区的内容输出至 `.tmcpr` 文件，单位: MB。默认值: `8`
    
`time_recorded_limit_hour`: 录制时长的限制。每当达到这个限制时 PCRC 将会重启，单位: 小时。默认值: `12`
    
`delay_before_afk_second`:  所有人都离开与暂停录制间的延迟，单位: 秒。默认值: `15`

`afk_ignore_spectator`: 若设为 `true`，PCRC 在判断是否所有玩家均已离开以决定是否暂停录制时，将会忽略来自旁观者模式的数据包。默认值: `true`

`record_packets_when_afk`: 若设为 `false`，PCRC 将会在暂停录制时忽略几乎所有到来的数据包（SARC 的行为）。这将显著减小录制文件体积，但是如果玩家离开后世界里仍有事件在发生的话，这可能会造成实体/方块不同步。默认值: `true`

`auto_relogin`: 当 PCRC 客户端掉线时是否自动重连。若为 `true`，PCRC 会在掉线后尝试重连

`auto_relogin_attempts`: 在成功连接至服务器前，自动重连的最大尝试次数。默认值: `5`

`chat_spam_protect`: 是否在必要时自动延迟发送聊天消息，以防止被因滥发消息而踢出游戏

`command_prefix`: 任何以 `command_prefix` 开头的聊天信息将会被认为是控制 PCRC 的指令。默认值: `!!PCRC`

### PCRC 特性

`daytime`: 将游戏时间设置为一个固定值并忽略之后所有的时间变化。将其设为 `-1` 以录制正常的昼夜循环

`weather`: 是否录制天气

`with_player_only`: 是否只当玩家在附近时才进行录制

`remove_items`: 是否不录制掉落物

`remove_bats`: 是否不录制蝙蝠

`remove_phantoms`: 是否不录制幻翼

`on_joined_commands`: 一个字符串列表，储存着 PCRC 机器人加入游戏后将依次输入的指令。如果你的服务器有登录插件等，你可能需要这个

```json5
// on_joined_commands 例子
{
    "on_joined_commands": [
        "/login myPassword",
        "/server myServer"
    ],
}
```

## 指令

指令前缀 `!!PCRC` 可在配置文件中自定义

### 控制台指令

仅在独立运行时有效

`help`: Show the list of console command

`start`: 开启 PCRC 并开始录制

`stop`: 停止 PCRC 并关闭录制

`restart`: 重启 PCRC

`exit`: 退出程序

`reload`: 重新加载配置文件。注意并非所有的配置文件项均支持热重载，如 `authenticate_type` 是不支持热重载的

`auth`: 再次尝试 Minecraft 登录验证。在登录失败时使用

`say <信息>`: 将文字 `<信息>` 作为聊天信息发送至服务器

`set <选项> <值>` 将 PCRC 与配置文件中的 <选项> 设置为 <值>

`whitelist [on|off]` 开关白名单

`whitelist [add|del] <玩家名>` 向白名单增/删玩家

`whitelist status` 查看白名单列表及其开启状态

`status`: 查看 PCRC 的状态

`list`: 在连接至服务器后显示玩家列表

### MCDR 插件指令

仅在作为 MCDR 插件时有效

`!!PCRC start`: 开启 PCRC 并开始录制

`!!PCRC stop`: 停止 PCRC 并关闭录制。仅对控制台输入有效

`!!PCRC reload`: 重载 PCRC 的配置文件和与 MCDR 相关的配置文件。注意并非所有的 PCRC 配置文件项均支持热重载

`!!PCRC set_redirect_url <url>`: 输入用于微软账号登录时的页面链接

需要权限等级 1 以执行这些指令。最低所需的权限等级可在与 MCDR 相关的配置文件中设置

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

`!!PCRC respawn`: 让 PCRC 机器人尝试复活

## 注意事项

- PCRC 内无处理游戏内容相关代码，因此在移动 PCRC 机器人时仅可使用诸如 `!!PCRC spec` 或 `/tp` 等传送类指令，不可使用活塞等方式移动机器人。否则可能出现机器人隐身等 bug
- PCRC 录制时显示的文件大小为 `.tmcpr` 文件，即未压缩的原始数据包文件的大小，并非最终文件 `.mcpr` 的大小。视情况不同最终文件大小大约为原始数据包文件大小的 10% ~ 40%
