# 随手控 / WatchMouse

**把手机变成 Windows 和 Mac 的无线鼠标与键盘。**

[English](README.md) · [下载最新版](https://github.com/jiangyiyx-star/WatchMouse/releases/latest) · [反馈问题](https://github.com/jiangyiyx-star/WatchMouse/issues)

电脑打开接收器，手机连同一个 Wi-Fi，扫码即可控制当前选中的窗口。无需手机 App、账号或云端中转。

## 2.8 多人独立手柄

Windows 已配置原生手柄支持时，每台手机可以使用独立的 Xbox 360 手柄。最多四个活跃的手机网页自动分配 WatchMouse 的 P1–P4 席位。Xbox / PlayStation 两套按钮布局、中央触控板、横屏全屏以及键鼠功能继续保留。

![手机手柄独立席位](docs/screenshots/phone-gamepad-v28.jpg)

## 界面截图

以下是实际界面的演示截图，使用独立演示数据；截图中的二维码和配对码不能连接真实接收器。

| 手机鼠标 | 手机键盘 | 中文及连接设置 |
| --- | --- | --- |
| <img src="docs/screenshots/phone-mouse-v26.jpg" alt="手机鼠标" width="260"> | <img src="docs/screenshots/phone-keyboard-v26.jpg" alt="手机键盘" width="260"> | <img src="docs/screenshots/phone-chinese-v26.jpg" alt="中文界面" width="260"> |

| Mac 接收器 | Windows 接收器 |
| --- | --- |
| <img src="docs/screenshots/mac-desktop.png" alt="Mac 接收器" width="520"> | <img src="docs/screenshots/windows-desktop.png" alt="Windows 接收器" width="520"> |

## 下载与使用

- Windows：[最新 Windows 发布版](https://github.com/jiangyiyx-star/WatchMouse/releases/latest)。双击启动，首次连接按提示允许专用网络访问。
- Apple 芯片 Mac：[WatchMouse-Mac-2.7-arm64.zip](https://github.com/jiangyiyx-star/WatchMouse/releases/download/v2.7/WatchMouse-Mac-2.7-arm64.zip)。解压后放进“应用程序”，在系统设置中启用 WatchMouse 的辅助功能权限。

安装包自带运行环境，不用安装 Python。Mac 下载包支持 macOS 11 及以上，Intel 包尚未验证。Mac 为自签名构建，尚未经过 Apple 公证；首次启动若被阻止，需在隐私与安全设置中确认来源后选择“仍要打开”。

1. 手机与电脑连同一个 Wi-Fi。
2. 启动电脑接收器，用手机浏览器扫描二维码。
3. 在电脑上选中要操作的窗口。
4. 保持接收器运行，关闭窗口会停止服务。

**只需首次配对：**电脑会保存配对密钥，重启、更新时不会主动重置；手机浏览器也会保存，接收器重新启动后自动重连。建议收藏扫码后的完整链接。清除浏览器数据或重置电脑配置后需要重新配对；电脑局域网 IP 改变时要扫描更新后的地址，密钥本身不用重设。浏览器存储按地址隔离，暂不支持跨 IP 自动发现。

### Windows 原生手柄（可选）

原生模式需要电脑已配置 [ViGEmBus 驱动](https://github.com/nefarius/ViGEmBus/releases)和 [vgamepad 库](https://github.com/yannbouteiller/vgamepad)，配置后重启 WatchMouse 即可；已配置的电脑可以直接复用。EXE 不会自动安装驱动。缺少原生支持时使用键盘映射，键盘映射不能变成多人独立手柄。Mac 接收器继续使用键盘映射，不提供多人原生 Xbox 手柄。

1. 所有手机和 Windows 电脑连同一个 Wi-Fi，各自在浏览器扫描接收器二维码。
2. 每台手机打开**手柄**模式；原生模式会为活跃网页自动分配独立的 P1–P4 席位。
3. 先连接齐玩家，再启动支持本地多人的游戏；游戏要求时，各自按 A 加入，具体加入方式以游戏为准。

退出手柄模式或网页进入后台时会释放控制。活跃网页即使没有操作，也会发送中立心跳保留席位，不会按住任何按钮；断连会话过期后释放席位。P1–P4 是 WatchMouse 席位，不保证等于游戏中的玩家编号。Windows 的 [XInput 总共只有四个控制器槽位](https://learn.microsoft.com/zh-cn/windows/win32/xinput/getting-started-with-xinput)，实体 Xbox 手柄和其他虚拟手柄也占用这些槽位。游戏必须原生支持本地多人及对应人数；Steam 能识别手柄不代表游戏自动支持多人。参见 [Valve 的本地多人说明](https://partner.steamgames.com/doc/features/remoteplay)。

## 功能

- **鼠标**：单指移动、轻点单击、左右键、拖动开关、双指滚动和独立单指滚动带。
- **键鼠**：用手机输入法编辑草稿，确认后发送到电脑，支持中文、emoji、粘贴和输入法语音转文字。
- **视频**：上一个、播放/暂停、下一个大按钮，适用于支持方向键/空格键的应用。
- **手柄**：按真实手柄的位置摆放——肩键在两上角，左摇杆在十字键上方（Xbox）或下方（PlayStation），动作键在右摇杆上方，View/Menu 放中间不挡拇指，屏幕中央的接缝处是触控板（拖动移动、轻点左键、长按右键），游戏里也能随时控制光标。手机横过来点右上角全屏按钮可隐藏浏览器和底部栏、锁定横屏；Xbox / PlayStation 布局一键切换。按住即生效、松手就释放。默认映射为键盘，并以硬件扫描码注入，读原始输入的游戏也能收到；游戏若以管理员身份启动，接收器也要用管理员身份运行；Windows 上配置可选的 ViGEmBus 驱动及匹配的 vgamepad 库后自动切为原生模式，电脑识别为 Xbox 360 手柄。
- **语言**：手机、Mac 和 Windows 界面默认英文，可选择简体中文并保存选择。
- **Mac 快捷键**：协议中的 Ctrl/Win 映射为 Command，Alt 映射为 Option。
- **手表**：提供不用 JavaScript 的 `/watch` 简版，实体 Apple Watch 兼容性尚未实测。

网页不会改变手机输入法的语音识别语言，也不提供手机音频作为系统麦克风的功能。浏览器语音识别仅在受支持的安全上下文出现。游戏、受保护输入框及部分自行处理键码的应用可能拒绝模拟输入。

## 本地连接与安全

项目没有云端账号、中转服务或统计上报。配对链接能控制电脑，请只分享给自己的设备。局域网连接使用**未加密 HTTP**，仅用于可信网络，不要把 53514 端口映射到公网。见 [安全说明](SECURITY.md)。

## 开发

[Windows 开发与构建](Windows/Windows/README.md) · [Mac 开发与构建](Mac/README.md) · [贡献指南](CONTRIBUTING.md)

Windows 构建脚本兼容 PowerShell 5.1，处理中文用户名和路径。GitHub Actions 分别测试并构建两平台。测试拦截最终系统输入，不会操作测试电脑的桌面。

用户已确认真实手机可以连接并控制 Mac；所有目标应用及实体 Apple Watch 的完整兼容性仍需实测。

项目源代码使用 [MIT 协议](LICENSE)，第三方组件保留各自许可，见 [第三方许可说明](THIRD_PARTY_NOTICES.md)。
