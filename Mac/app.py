"""Native Cocoa desktop receiver. Shared phone assets live in Windows/Windows."""
from pathlib import Path
import argparse
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

LANGUAGES = ('en', 'zh-CN')
DEMO_TOKEN = 'PUBLIC-DEMO-NOT-A-PAIRING-KEY'
TEXT = {
    'en': {
        'window_title': 'WatchMouse · Mac Receiver',
        'subtitle': 'Your phone, your Mac keyboard and mouse',
        'instructions': 'Join the same Wi-Fi and scan the QR code. Select the target Mac window first.',
        'language': 'Interface language',
        'copy_link': 'Copy phone link',
        'refresh': 'Refresh addresses',
        'preview': 'Desktop preview',
        'permissions': 'Accessibility Settings',
        'stop': 'Stop service',
        'start': 'Start service',
        'footer': 'Phone Ctrl shortcuts use Command on Mac. Closing this window stops the service.',
        'permission_granted': 'Accessibility is enabled. Your phone can control this Mac.',
        'permission_required': 'Enable WatchMouse in System Settings → Privacy & Security → Accessibility.',
        'running': 'Service running · {count} actions received',
        'no_lan': 'No local network address found. Connect to Wi-Fi and refresh addresses.',
        'stopped': 'Service stopped',
        'failed': 'Could not start: {error}. Close other receivers and try again.',
        'quit': 'Quit WatchMouse',
        'demo': 'Demo',
        'demo_status': 'Demo preview · offline; no input is sent',
        'demo_permission': 'Demo uses an example address and public key. Scan the QR code in your running app to connect.',
    },
    'zh-CN': {
        'window_title': 'WatchMouse · 随手控 Mac',
        'subtitle': '手机就是 Mac 的键盘和鼠标',
        'instructions': '连接同一个 Wi-Fi，扫描二维码；先点选 Mac 上要操作的窗口。',
        'language': '界面语言',
        'copy_link': '复制手机链接',
        'refresh': '刷新网络地址',
        'preview': '电脑预览',
        'permissions': '打开辅助功能设置',
        'stop': '停止服务',
        'start': '启动服务',
        'footer': '手机上的 Ctrl 组合键对应 Mac 的 Command。关闭窗口会停止服务。',
        'permission_granted': '辅助功能已授权，可以控制 Mac。',
        'permission_required': '需要辅助功能授权：在系统设置 → 隐私与安全性 → 辅助功能中启用 WatchMouse。',
        'running': '服务运行中 · 已执行 {count} 次操作',
        'no_lan': '未找到局域网地址。连接 Wi-Fi 后刷新网络地址。',
        'stopped': '服务已停止',
        'failed': '启动失败：{error}。请关闭其他接收器后重试。',
        'quit': '退出 WatchMouse',
        'demo': '演示',
        'demo_status': '演示预览 · 离线，不发送输入',
        'demo_permission': '演示使用示例地址和公开密钥。请扫描实际运行应用中的二维码进行连接。',
    },
}


def normalize_language(language):
    return language if language in LANGUAGES else 'en'


def session_settings(demo=False, language=None):
    """Demo screenshots never read or modify the user's pairing settings."""
    if demo:
        return {'token': DEMO_TOKEN, 'language': normalize_language(language)}
    settings = receiver.load_settings()
    return {'token': settings['token'], 'language': normalize_language(settings.get('language'))}


class ReceiverView(A.NSView):
    def isOpaque(self):
        return True

    def drawRect_(self, rect):
        # Draw the native window background so offscreen demo captures are opaque.
        A.NSColor.windowBackgroundColor().setFill()
        A.NSRectFill(rect)


class QRCodeView(A.NSView):
    def isOpaque(self):
        return True

    def setImage_(self, image):
        self.image = image
        self.setNeedsDisplay_(True)

    def drawRect_(self, rect):
        if getattr(self, 'image', None):
            self.image.drawInRect_(self.bounds())


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, notification):
        self.server = None
        self.server_error = None
        self.demo = getattr(self, 'demo', False)
        settings = session_settings(self.demo, getattr(self, 'initial_language', None))
        self.token, self.language = settings['token'], settings['language']
        self.addresses = []
        self.window = A.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            ((0,0),(720,520)), A.NSWindowStyleMaskTitled | A.NSWindowStyleMaskClosable |
            A.NSWindowStyleMaskMiniaturizable, A.NSBackingStoreBuffered, False)
        self.window.setContentView_(ReceiverView.alloc().initWithFrame_(((0,0),(720,520))))
        self.window.setReleasedWhenClosed_(False)
        self.window.center()
        self.label('WatchMouse', 28, 462, 460, 34, 28)
        self.language_selector = A.NSPopUpButton.alloc().initWithFrame_pullsDown_(((538,464),(154,30)), False)
        self.language_selector.addItemsWithTitles_(['English', '简体中文'])
        self.language_selector.setTarget_(self); self.language_selector.setAction_('languageChanged:')
        self.window.contentView().addSubview_(self.language_selector)
        self.subtitle = self.label('', 28, 426, 660, 27, 20)
        self.instructions = self.label('',28,391,660,24)
        self.address = A.NSPopUpButton.alloc().initWithFrame_pullsDown_(((28,342),(420,30)), False)
        self.address.setTarget_(self); self.address.setAction_('addressChanged:')
        self.window.contentView().addSubview_(self.address)
        self.link = self.label('',28,280,420,52)
        self.link.setSelectable_(True)
        self.image = QRCodeView.alloc().initWithFrame_(((476,174),(216,216)))
        self.window.contentView().addSubview_(self.image)
        self.copy_button = self.button('',28,235,135,'copyLink:')
        self.refresh_button = self.button('',174,235,140,'refresh:')
        self.preview_button = self.button('',320,235,130,'preview:')
        self.status = self.label('',28,177,430,45)
        self.permission = self.label('',28,124,660,44)
        self.permission_button = self.button('',28,78,190,'permissions:')
        self.toggle = self.button('',232,78,130,'toggleService:')
        self.footer = self.label('',28,26,660,30)
        self.applyLanguage()
        self.refresh_(None)
        if self.demo:
            for button in (self.copy_button, self.preview_button, self.permission_button, self.toggle):
                button.setEnabled_(False)
        else:
            self.startService()
        self.timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1, self, 'tick:', None, True)
        self.window.makeKeyAndOrderFront_(None)
        A.NSApp.activateIgnoringOtherApps_(True)
        self.tick_(None)
        if getattr(self, 'screenshot_path', None):
            self.screenshot_timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.5, self, 'captureScreenshot:', None, False)

    def captureScreenshot_(self, timer):
        """Capture only the demo's rendered native view, never the desktop."""
        try:
            view = self.window.contentView()
            self.window.displayIfNeeded()
            bitmap = view.bitmapImageRepForCachingDisplayInRect_(view.bounds())
            view.cacheDisplayInRect_toBitmapImageRep_(view.bounds(), bitmap)
            data = bitmap.representationUsingType_properties_(A.NSBitmapImageFileTypePNG, {})
            path = Path(self.screenshot_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes(data))
        except Exception as error:
            self.screenshot_error = str(error)
            logging.exception('Demo screenshot failed')
        finally:
            A.NSApp.terminate_(None)

    @objc.python_method
    def text(self, key, **values):
        return TEXT[self.language][key].format(**values)

    @objc.python_method
    def applyLanguage(self):
        title = self.text('window_title')
        self.window.setTitle_(f"{title} · {self.text('demo')}" if self.demo else title)
        self.language_selector.selectItemAtIndex_(LANGUAGES.index(self.language))
        self.language_selector.setToolTip_(self.text('language'))
        for view, key in ((self.subtitle, 'subtitle'), (self.instructions, 'instructions'), (self.footer, 'footer')):
            view.setStringValue_(self.text(key))
        for view, key in ((self.copy_button, 'copy_link'), (self.refresh_button, 'refresh'),
                          (self.preview_button, 'preview'), (self.permission_button, 'permissions')):
            view.setTitle_(self.text(key))
        if getattr(self, 'quit_menu_item', None):
            self.quit_menu_item.setTitle_(self.text('quit'))
        self.tick_(None)

    def languageChanged_(self, sender):
        self.language = LANGUAGES[self.language_selector.indexOfSelectedItem()]
        if not self.demo:
            # Merge the current config so language changes keep pairing and other preferences.
            settings = receiver.load_settings()
            settings['language'] = self.language
            receiver.save_settings(settings)
        self.applyLanguage()

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
        self.addresses = ['192.0.2.10'] if self.demo else receiver.lan_addresses() or ['127.0.0.1']
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
        if self.demo:
            return
        self.server_error = None
        try:
            self.server = receiver.create_server(controller=InputController(),token=self.token)
            self.worker = threading.Thread(target=self.server.serve_forever,
                                           kwargs={'poll_interval':0.1},daemon=True)
            self.worker.start()
        except OSError as error:
            self.server = None
            self.server_error = str(error)
        self.tick_(None)

    @objc.python_method
    def stopService(self):
        if self.server:
            self.server.shutdown()
            try:
                self.server.server_close()
            except OSError:
                logging.exception('Input release failed')
            self.server = None
        self.server_error = None
        self.tick_(None)

    def toggleService_(self, sender):
        if self.server: self.stopService()
        else: self.startService()

    def tick_(self, timer):
        self.toggle.setTitle_(self.text('stop' if self.server else 'start'))
        if self.demo:
            self.status.setStringValue_(self.text('demo_status'))
            self.permission.setStringValue_(self.text('demo_permission'))
            return
        trusted = AX.AXIsProcessTrusted()
        self.permission.setStringValue_(self.text('permission_granted' if trusted else 'permission_required'))
        if self.server:
            address = self.address.titleOfSelectedItem()
            self.status.setStringValue_(self.text('running', count=self.server.command_count) if address != '127.0.0.1'
                else self.text('no_lan'))
        elif self.server_error is not None:
            self.status.setStringValue_(self.text('failed', error=self.server_error))
        else:
            self.status.setStringValue_(self.text('stopped'))

    def applicationShouldTerminateAfterLastWindowClosed_(self, app):
        return True

    def applicationWillTerminate_(self, notification):
        self.stopService()


def main(argv=None):
    parser = argparse.ArgumentParser(description='WatchMouse Mac receiver')
    parser.add_argument('--demo', action='store_true', help='Offline public screenshot preview; no input or saved pairing')
    parser.add_argument('--language', choices=LANGUAGES, help='Demo interface language (normal use remembers the UI selection)')
    parser.add_argument('--screenshot', type=Path, help='Save a rendered native PNG and exit (requires --demo)')
    options = parser.parse_args(argv)
    if options.screenshot and not options.demo:
        parser.error('--screenshot requires --demo so screenshots cannot expose pairing credentials')
    if options.demo:
        logging.basicConfig(level=logging.INFO)
    else:
        log = receiver.settings_path().parent / 'desktop.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(filename=log,level=logging.INFO,encoding='utf-8')
    application = A.NSApplication.sharedApplication()
    application.setActivationPolicy_(A.NSApplicationActivationPolicyRegular)
    menu = A.NSMenu.alloc().init()
    item = A.NSMenuItem.alloc().init()
    menu.addItem_(item)
    submenu = A.NSMenu.alloc().initWithTitle_('WatchMouse')
    quit_menu_item = submenu.addItemWithTitle_action_keyEquivalent_('Quit WatchMouse','terminate:','q')
    item.setSubmenu_(submenu); application.setMainMenu_(menu)
    delegate = AppDelegate.alloc().init()
    delegate.quit_menu_item = quit_menu_item
    delegate.demo, delegate.initial_language = options.demo, options.language
    delegate.screenshot_path, delegate.screenshot_error = options.screenshot, None
    application.setDelegate_(delegate)
    application.run()
    if delegate.screenshot_error:
        raise RuntimeError(delegate.screenshot_error)

if __name__ == '__main__': main()
