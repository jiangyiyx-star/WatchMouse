"""Native Cocoa desktop receiver. Shared phone assets live in Windows/Windows."""
from pathlib import Path
import io
import logging
import sys
import threading
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Windows' / 'Windows'))
import receiver
from mac_input_control import InputController
import objc
import AppKit as A
from Foundation import NSObject, NSTimer, NSData, NSURL
import ApplicationServices as AX
import qrcode

class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.server = None
        self.token = receiver.load_settings()['token']
        self.addresses = []
        self.window = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0,0),(720,520)), A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable |
            A.NSWindowStyleMaskMiniaturizable, A.NSBackingStoreBuffered, False)
        self.window.setTitle_('WatchMouse · 随手控 Mac')
        self.window.setReleasedWhenClosed_(False)
        self.window.center()
        self.label('WatchMouse', 28, 462, 660, 34, 28)
        self.label('手机就是 Mac 的键盘和鼠标', 28, 426, 660, 27, 20)
        self.label('连接同一个 Wi-Fi，扫描二维码；先点选 Mac 上要操作的窗口。',28,391,660,24)
        self.address = A.NSPopUpButton.alloc().initWithFrame_pullsDown_(((28,342),(420,30)), False)
        self.address.setTarget_(self); self.address.setAction_('addressChanged:')
        self.window.contentView().addSubview_(self.address)
        self.link = self.label('',28,280,420,52)
        self.link.setSelectable_(True)
        self.image = A.NSImageView.alloc().initWithFrame_(((476,174),(216,216)))
        self.window.contentView().addSubview_(self.image)
        self.button('复制手机链接',28,235,135,'copyLink:')
        self.button('刷新网络地址',174,235,135,'refresh:')
        self.button('电脑预览',320,235,125,'preview:')
        self.status = self.label('',28,177,430,45)
        self.permission = self.label('',28,124,660,44)
        self.button('打开辅助功能设置',28,78,190,'permissions:')
        self.toggle = self.button('停止服务',232,78,130,'toggleService:')
        self.label('手机上的 Ctrl 组合键对应 Mac 的 Command。关闭窗口会停止服务。',28,26,660,30)
        self.refresh_(None)
        self.startService()
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1, self, 'tick:', None, True)
        self.window.makeKeyAndOrderFront_(None)
        A.NSApp.activateIgnoringOtherApps_(True)
        self.tick_(None)

    @objc.python_method
    def label(self, text, x, y, w, h, size=14):
        view = A.NSTextField.alloc().initWithFrame_(((x,y),(w,h)))
        view.setStringValue_(text); view.setBezeled_(False); view.setDrawsBackground_(False)
        view.setEditable_(False); view.setFont_(A.NSFont.systemFontOfSize_(size))
        self.window.contentView().addSubview_(view)
        return view

    @objc.python_method
    def button(self, text, x, y, w, action):
        button = A.NSButton.alloc().initWithFrame_(((x,y),(w,34)))
        button.setTitle_(text); button.setBezelStyle_(A.NSBezelStyleRounded)
        button.setTarget_(self); button.setAction_(action)
        self.window.contentView().addSubview_(button)
        return button

    def refresh_(self, sender):
        previous = self.address.titleOfSelectedItem()
        self.addresses = receiver.lan_addresses() or ['127.0.0.1']
        self.address.removeAllItems(); self.address.addItemsWithTitles_(self.addresses)
        if previous in self.addresses:
            self.address.selectItemWithTitle_(previous)
        self.addressChanged_(None)

    def addressChanged_(self, sender):
        self.url = f'http://{self.address.titleOfSelectedItem()}:{receiver.PORT}/?token={quote(self.token)}'
        self.link.setStringValue_(self.url)
        stream = io.BytesIO()
        qrcode.make(self.url, border=3).save(stream, format='PNG')
        data = stream.getvalue()
        image = A.NSImage.alloc().initWithData_(NSData.dataWithBytes_length_(data, len(data)))
        self.image.setImage_(image)

    def copyLink_(self, sender):
        board = A.NSPasteboard.generalPasteboard()
        board.clearContents(); board.setString_forType_(self.url,A.NSPasteboardTypeString)

    def preview_(self, sender):
        A.NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(
            f'http://127.0.0.1:{receiver.PORT}/?token={quote(self.token)}'))

    def permissions_(self, sender):
        AX.AXIsProcessTrustedWithOptions({AX.kAXTrustedCheckOptionPrompt: True})
        A.NSWorkspace.sharedWorkspace().openURL_(NSURL.URLWithString_(
            'x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility'))

    @objc.python_method
    def startService(self):
        try:
            self.server = receiver.create_server(controller=InputController(),token=self.token)
            self.worker = threading.Thread(target=self.server.serve_forever,
                                           kwargs={'poll_interval':0.1},daemon=True)
            self.worker.start()
            self.toggle.setTitle_('停止服务')
        except OSError as error:
            self.server = None
            self.status.setStringValue_(f'启动失败：{error}。请关闭其他接收器后重试。')
            self.toggle.setTitle_('启动服务')

    @objc.python_method
    def stopService(self):
        if self.server:
            self.server.shutdown()
            try:
                self.server.server_close()
            except OSError:
                logging.exception('Input release failed')
            self.server = None
        self.toggle.setTitle_('启动服务')
        self.status.setStringValue_('服务已停止')

    def toggleService_(self, sender):
        if self.server: self.stopService()
        else: self.startService()

    def tick_(self, timer):
        trusted = AX.AXIsProcessTrusted()
        self.permission.setStringValue_('辅助功能已授权，可以控制 Mac。' if trusted else
            '需要辅助功能授权：在系统设置中启用 WatchMouse，授权后即可控制。')
        if self.server:
            address = self.address.titleOfSelectedItem()
            self.status.setStringValue_(f'服务运行中 · 已执行 {self.server.command_count} 次操作' if address != '127.0.0.1'
                else '未找到局域网地址。连接 Wi-Fi 后刷新网络地址。')

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def applicationWillTerminate_(self, notification):
        self.stopService()


def main():
    log = receiver.settings_path().parent / 'desktop.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(filename=log,level=logging.INFO,encoding='utf-8')
    application = A.NSApplication.sharedApplication()
    application.setActivationPolicy_(A.NSApplicationActivationPolicyRegular)
    menu = A.NSMenu.alloc().init()
    item = A.NSMenuItem.alloc().init()
    menu.addItem_(item)
    submenu = A.NSMenu.alloc().initWithTitle_('WatchMouse')
    submenu.addItemWithTitle_action_keyEquivalent_('退出 WatchMouse','terminate:','q')
    item.setSubmenu_(submenu); application.setMainMenu_(menu)
    delegate = AppDelegate.alloc().init()
    application.setDelegate_(delegate)
    application.run()

if __name__ == '__main__': main()
