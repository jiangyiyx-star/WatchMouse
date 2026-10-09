# WatchMouse · 随手控 Mac

手机通过同一 Wi-Fi 控制 Mac，复用 Windows 2.3 的手机网页、配对校验和手表简版入口。

## 下载使用

从 [Mac 下载页](https://github.com/jiangyiyx-star/WatchMouse/releases/tag/v2.3-mac.2) 下载 `WatchMouse-Mac-2.3.1-arm64.zip`。当前下载包面向 Apple 芯片 Mac，最低 macOS 11；Intel Mac 可在 Intel 机器上从源码构建，尚未验证 Intel 下载包。

1. 解压，将 `WatchMouse.app` 拖到“应用程序”，以后从 `/Applications/WatchMouse.app` 启动。
2. 这是自签名构建，尚未经过 Apple 公证。如果 macOS 阻止首次启动，可在系统设置 → 隐私与安全性中确认来源后选择“仍要打开”。
3. 点“打开辅助功能设置”，在系统设置 → 隐私与安全性 → 辅助功能中添加并启用 `WatchMouse.app`。应用会自动刷新授权状态。手机页面若提示辅助功能权限未开启，开启后回到手机点击“连接”；无需更换配对码。
4. 手机与 Mac 使用同一 Wi-Fi，扫描窗口二维码。先在 Mac 上点选要控制的窗口。
5. 使用时保持应用窗口打开。关闭窗口或按 Command+Q 会停止接收服务；窗口内也可暂停或重新启动服务。

支持触控板移动、左/右键、拖动、单指滚动带、双指滚动、方向键、播放/暂停和中文/emoji 输入。手机协议中的 `ctrl` / `win` 在 Mac 上映射为 Command；`alt` 为 Option，`shift` 为 Shift。开发者可用 `control` 发送真正的 Control。

键码按 ANSI 位置映射，文字使用 Quartz Unicode 事件而不改动剪贴板。个别游戏或应用自行处理键码，可能忽略 Unicode 文字；受保护输入框也可能拒绝模拟输入。[Apple 的 Unicode 事件说明](https://developer.apple.com/documentation/coregraphics/cgevent/keyboardsetunicodestring%28stringlength%3Aunicodestring%3A%29?language=objc)

连接失败时检查同一局域网、Wi-Fi 是否隔离客户端、macOS 防火墙是否允许本应用接收入站连接，以及窗口所选地址是否为手机可访问的地址。端口为 TCP `53514`。链接包含配对密钥，只分享给自己的设备。

配置和日志位于 `~/Library/Application Support/WatchMouse/`。Mac 不调用 Windows 防火墙和 PowerShell 脚本。

## 源码运行

在仓库根目录执行（需要 Python 3.12 或更新版本）：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r Mac/requirements.txt
.venv/bin/python Mac/app.py
```

源码运行时，辅助功能授权对象可能是 Python 或启动它的终端；发布包的授权对象是 WatchMouse。

## 构建

```bash
bash Mac/build.sh
```

脚本会建立独立环境，生成 `Mac/dist/WatchMouse.app` 和按当前机器架构命名的 ZIP。可设置 `WATCHMOUSE_PYTHON=/path/to/python3`。支持带空格和中文的源码路径。`WatchMouse.spec` 明确打包共享网页资源，不依赖用户机器上另装 Python。自签名只用于本地发布，正式公证需另行配置 Apple Developer 身份。

## 验证

```bash
.venv/bin/python -m unittest discover -s Windows/Windows/tests
.venv/bin/python -m unittest discover -s Mac/tests -v
node Windows/Windows/tests/frontend-smoke.cjs
```

Mac 测试创建真实 Quartz 事件并拦截最终发送，检查中文/emoji、Command 组合键、拖动超时释放、滚动方向、授权拒绝和 HTTP 接收。它们不会操作桌面。已在 Apple 芯片 Mac 上构建并检查发布包启动、原生窗口、二维码和服务。用户已确认辅助功能授权后，真实手机可以连接并控制 Mac；此反馈未覆盖所有手机功能，实体 Apple Watch 尚未实测。

## 文件结构

- `app.py`：Cocoa 原生窗口、二维码、权限提示与服务启停。
- `mac_input_control.py`：Quartz 输入事件；复用共享指令校验、串行执行和拖动看门狗。
- `../Windows/Windows/receiver.py`：两平台共用 HTTP 协议；按平台选取配置路径和网络接口。
- `../Windows/Windows/remote.*`：两平台共用手机界面，继续保留在原目录以避免破坏 Windows 打包。
