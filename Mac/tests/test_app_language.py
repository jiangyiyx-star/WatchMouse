"""Language persistence and screenshot isolation without posting native input."""
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app


class View:
    def __init__(self, value='', index=0):
        self.value, self.index = value, index

    def setTitle_(self, value):
        self.value = value

    def setStringValue_(self, value):
        self.value = value

    def setToolTip_(self, value):
        self.tooltip = value

    def selectItemAtIndex_(self, index):
        self.index = index

    def indexOfSelectedItem(self):
        return self.index

    def titleOfSelectedItem(self):
        return self.value


class AppLanguageTests(unittest.TestCase):
    def delegate(self, language='en', demo=False):
        delegate = app.AppDelegate.alloc().init()
        delegate.language, delegate.demo = language, demo
        delegate.server, delegate.server_error = None, None
        for name in ('window', 'language_selector', 'subtitle', 'instructions', 'footer',
                     'copy_button', 'refresh_button', 'preview_button', 'permission_button',
                     'quit_menu_item', 'toggle', 'status', 'permission'):
            setattr(delegate, name, View())
        delegate.address = View('192.168.1.20')
        return delegate

    def test_default_and_saved_language_keep_pairing_key(self):
        for saved, expected in ((None, 'en'), ('invalid', 'en'), ('zh-CN', 'zh-CN')):
            config = {'token': 'existing-pairing-key', 'language': saved}
            with patch.object(app.receiver, 'load_settings', return_value=config), \
                    patch.object(app.receiver, 'save_settings') as save:
                self.assertEqual({'token': 'existing-pairing-key', 'language': expected}, app.session_settings())
                save.assert_not_called()

    def test_switch_is_immediate_and_preserves_other_preferences(self):
        delegate = self.delegate()
        delegate.server = SimpleNamespace(command_count=12)
        original_server = delegate.server
        config = {'token': 'existing-pairing-key', 'futurePreference': True}
        delegate.language_selector.index = 1
        with patch.object(app.receiver, 'load_settings', return_value=config.copy()), \
                patch.object(app.receiver, 'save_settings') as save, \
                patch.object(app.AX, 'AXIsProcessTrusted', return_value=True):
            delegate.languageChanged_(None)
            save.assert_called_once_with({**config, 'language': 'zh-CN'})
        self.assertIs(original_server, delegate.server)
        self.assertEqual('复制手机链接', delegate.copy_button.value)
        self.assertEqual('停止服务', delegate.toggle.value)
        self.assertEqual('退出 WatchMouse', delegate.quit_menu_item.value)
        self.assertEqual('服务运行中 · 已执行 12 次操作', delegate.status.value)
        self.assertIn('已授权', delegate.permission.value)

    def test_stopped_error_and_permissions_use_current_language(self):
        delegate = self.delegate()
        with patch.object(app.AX, 'AXIsProcessTrusted', return_value=False):
            delegate.applyLanguage()
            self.assertEqual('Start service', delegate.toggle.value)
            self.assertEqual('Service stopped', delegate.status.value)
            self.assertIn('Accessibility', delegate.permission.value)
            delegate.server_error = 'Address already in use'
            delegate.tick_(None)
            self.assertIn('Could not start:', delegate.status.value)
            delegate.language = 'zh-CN'
            delegate.applyLanguage()
            self.assertIn('启动失败：', delegate.status.value)
            self.assertEqual('启动服务', delegate.toggle.value)
            self.assertIn('辅助功能', delegate.permission.value)

    def test_demo_does_not_read_settings_or_create_native_controller(self):
        with patch.object(app.receiver, 'load_settings') as load, \
                patch.object(app.receiver, 'save_settings') as save:
            self.assertEqual({'token': app.DEMO_TOKEN, 'language': 'en'}, app.session_settings(True))
            self.assertEqual('zh-CN', app.session_settings(True, 'zh-CN')['language'])
            load.assert_not_called()
            save.assert_not_called()
        delegate = self.delegate(demo=True)
        with patch.object(app, 'InputController') as controller, \
                patch.object(app.receiver, 'create_server') as server, \
                patch.object(app.AX, 'AXIsProcessTrusted') as trusted, \
                patch.object(app.receiver, 'load_settings') as load, \
                patch.object(app.receiver, 'save_settings') as save:
            delegate.startService()
            delegate.language_selector.index = 1
            delegate.languageChanged_(None)
            for call in (controller, server, trusted, load, save):
                call.assert_not_called()
        self.assertIn('演示', delegate.window.value)
        self.assertIn('不发送输入', delegate.status.value)

    def test_screenshot_requires_offline_demo(self):
        with patch.object(app.receiver, 'load_settings') as load, \
                patch.object(app.receiver, 'settings_path') as path, \
                patch('sys.stderr'):
            with self.assertRaises(SystemExit) as exit:
                app.main(['--screenshot', '/tmp/unused-watchmouse.png'])
            self.assertEqual(2, exit.exception.code)
            load.assert_not_called()
            path.assert_not_called()


if __name__ == '__main__':
    unittest.main()
