"""Desktop language persistence and safe documentation demo, without native input."""
from __future__ import annotations

import importlib.util
import ctypes
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class FakeVariable:
    def __init__(self, master=None, value="", **_options):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


class FakeWidget:
    def __init__(self, *args, **options):
        self.options = options
        self.scheduled = []
        self.window_title = ""

    def configure(self, *args, **options):
        self.options.update(options)

    def __setitem__(self, key, value):
        self.options[key] = value

    def __getitem__(self, key):
        return self.options[key]

    def title(self, value):
        self.window_title = value

    def after(self, delay, callback):
        self.scheduled.append((delay, callback))

    def __getattr__(self, _name):
        return lambda *args, **kwargs: None


# CI has real Tk; this suite always uses the same headless fake to avoid opening
# windows or injecting input. The CI screenshot step separately renders real Tk.
tk_mock = types.ModuleType("tkinter")
tk_mock.StringVar = FakeVariable
tk_mock.Label = FakeWidget
tk_mock.Entry = FakeWidget
tk_mock.Tk = FakeWidget
tk_mock.TclError = RuntimeError
tk_mock.messagebox = types.ModuleType("tkinter.messagebox")
tk_mock.messagebox.showerror = Mock()
tk_mock.ttk = types.ModuleType("tkinter.ttk")
for widget_name in ("Style", "Frame", "Label", "Button", "Combobox"):
    setattr(tk_mock.ttk, widget_name, FakeWidget)
spec = importlib.util.spec_from_file_location("windows_desktop_test_subject", ROOT / "app.py")
desktop = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = desktop
with patch.dict(sys.modules, {"tkinter": tk_mock, "tkinter.ttk": tk_mock.ttk, "tkinter.messagebox": tk_mock.messagebox}):
    spec.loader.exec_module(desktop)


def fake_link(app):
    app.link_var.set(f"http://{app.ip_var.get()}:{app.port}/?token={app.token}")


class DesktopLanguageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        # Exercise Unicode directories like Chinese Windows user profiles.
        self.settings_path = Path(self.temp.name) / "中文用户" / "WatchMouse" / "config.json"
        self.patches = [
            patch.object(desktop.receiver, "settings_path", return_value=self.settings_path),
            patch.object(desktop.receiver, "lan_addresses", return_value=["192.168.1.10"]),
            patch.object(desktop.WatchMouseApp, "check_network_profile"),
            patch.object(desktop.WatchMouseApp, "update_link", fake_link),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def app(self, **options):
        return desktop.WatchMouseApp(FakeWidget(), **options)

    def test_first_launch_defaults_to_english(self):
        app = self.app()
        self.assertEqual("en", app.language)
        self.assertEqual(desktop.APP_TITLE, app.root.window_title)
        self.assertEqual("Starting…", app.status.get())
        self.assertEqual("Start", app.start_button["text"])

    def test_language_choice_is_saved_and_restored_without_changing_pairing(self):
        app = self.app()
        original_token = app.token
        # A separate settings update must also survive this GUI preference write.
        settings = desktop.receiver.load_settings()
        settings["port"] = 53515
        settings["other"] = "保留"
        desktop.receiver.save_settings(settings)
        app.language_var.set("中文")
        app.change_language()
        saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        self.assertEqual("zh-CN", saved["language"])
        self.assertEqual(original_token, saved["token"])
        self.assertEqual(53515, saved["port"])
        self.assertEqual("保留", saved["other"])
        self.assertEqual("启动服务", app.start_button["text"])
        restored = self.app()
        self.assertEqual("zh-CN", restored.language)
        self.assertEqual(original_token, restored.token)
        self.assertEqual("中文", restored.language_var.get())

    def test_status_and_formatted_details_change_immediately(self):
        app = self.app()
        app.status.set("服务运行中")
        app.detail_var.set(desktop.LocalizedText("端口 {port} · 本机运行", {"port": 53514}))
        self.assertEqual("Receiver running", app.status.get())
        self.assertEqual("Port 53514 · Runs locally", app.detail_var.get())
        app.language_var.set("中文")
        app.change_language()
        self.assertEqual("服务运行中", app.status.get())
        self.assertEqual("端口 53514 · 本机运行", app.detail_var.get())
        app.language_var.set("English")
        app.change_language()
        self.assertEqual("Receiver running", app.status.get())

    def test_failed_save_keeps_existing_language_and_pairing(self):
        app = self.app()
        original_token = app.token
        app.language_var.set("中文")
        with patch.object(desktop.receiver, "save_settings", side_effect=OSError("disk full")):
            app.change_language()
        self.assertEqual("en", app.language)
        self.assertEqual("English", app.language_var.get())
        self.assertEqual(original_token, app.token)
        self.assertIn("Could not save", app.notice.get())

    def test_invalid_preference_falls_back_to_english(self):
        self.assertEqual("en", desktop.normalize_language(None))
        self.assertEqual("en", desktop.normalize_language("untrusted"))
        self.assertEqual("zh-CN", desktop.normalize_language("zh-CN"))

    def test_localized_errors_keep_parameters_for_language_switch(self):
        error = desktop.LocalizedError("端口 {port} 已被其他服务使用。请关闭原接收器后重试。", port=53514)
        self.assertIn("Port 53514", desktop.translate(error.localized_text, "en"))
        self.assertIn("端口 53514", desktop.translate(error.localized_text, "zh-CN"))

    def test_demo_never_reads_or_writes_settings_or_starts_network(self):
        with patch.object(desktop.receiver, "load_settings") as load, patch.object(desktop.receiver, "save_settings") as save, patch.object(desktop.receiver, "lan_addresses") as addresses, patch.object(desktop.receiver, "create_server") as server, patch.object(desktop, "configure_firewall") as firewall:
            app = self.app(demo=True, screenshot="windows-desktop.png")
            app.language_var.set("中文")
            app.change_language()
            app.start()
            app.allow_firewall()
            for operation in (load, save, addresses, server, firewall):
                operation.assert_not_called()
        self.assertEqual("PUBLIC-DEMO-NOT-A-PAIRING-KEY", app.token)
        self.assertIn("192.0.2.10", app.link_var.get())
        self.assertEqual("演示", app.status.get())
        self.assertEqual("disabled", app.start_button["state"])
        self.assertEqual(1, len(app.root.scheduled))
        self.assertFalse(self.settings_path.exists())

    def test_firewall_powershell_handles_unicode_paths_and_output(self):
        result = types.SimpleNamespace(returncode=1, stderr="中文错误")
        with patch.object(desktop, "is_admin", return_value=True), patch.object(desktop.sys, "executable", "C:\\用户\\O'Brien\\WatchMouse.exe"), patch.object(desktop.subprocess, "run", return_value=result) as run:
            with self.assertRaisesRegex(RuntimeError, "中文错误"):
                desktop.configure_firewall(53514)
        script = run.call_args.args[0][-1]
        self.assertIn("UTF8Encoding", script)
        self.assertIn("O''Brien", script)
        self.assertEqual("utf-8", run.call_args.kwargs["encoding"])
        self.assertIn("-Profile Private -RemoteAddress LocalSubnet", script)

    def native_capture(self, *, print_ok=True, black_bottom=False, expected_size=(8, 9)):
        user32, gdi32 = Mock(), Mock()
        user32.GetAncestor.return_value = 456
        user32.GetDC.return_value = 11
        user32.PrintWindow.return_value = int(print_ok)
        gdi32.CreateCompatibleDC.return_value = 22
        gdi32.SelectObject.return_value = 44
        width, height = 8, 9
        pixels = bytes(component for y in range(height) for x in range(width) for component in ((0, 0, 0, 0) if black_bottom and y >= 6 else (32, 17, 11 + x, 0)))
        buffer = ctypes.create_string_buffer(pixels)

        def rectangle(_window, pointer):
            pointer._obj.left = pointer._obj.top = 0
            pointer._obj.right, pointer._obj.bottom = width, height
            return 1

        def bitmap(_dc, _header, _usage, bits, _section, _offset):
            bits._obj.value = ctypes.addressof(buffer)
            return 33

        user32.GetClientRect.side_effect = rectangle
        gdi32.CreateDIBSection.side_effect = bitmap
        libraries = {"user32": user32, "gdi32": gdi32}
        patcher = patch.object(desktop.ctypes, "WinDLL", side_effect=lambda name, **kwargs: libraries[name], create=True)
        return user32, gdi32, patcher, expected_size

    def test_native_capture_prints_complete_client_without_desktop_pixels(self):
        user32, gdi32, native, size = self.native_capture()
        with native:
            image = desktop.capture_windows_client(123, size)
        self.assertEqual(size, image.size)
        self.assertEqual((18, 17, 32), image.getpixel((7, 8)))
        user32.GetAncestor.assert_called_once_with(123, 2)
        user32.PrintWindow.assert_called_once_with(456, 22, 3)
        gdi32.DeleteObject.assert_called_once_with(33)
        gdi32.DeleteDC.assert_called_once_with(22)
        user32.ReleaseDC.assert_called_once_with(456, 11)

    def test_native_capture_fails_explicitly_and_cleans_up_when_printwindow_fails(self):
        user32, gdi32, native, size = self.native_capture(print_ok=False)
        with native, self.assertRaisesRegex(OSError, "PrintWindow"):
            desktop.capture_windows_client(123, size)
        gdi32.DeleteObject.assert_called_once_with(33)
        gdi32.DeleteDC.assert_called_once_with(22)
        user32.ReleaseDC.assert_called_once_with(456, 11)

    def test_native_capture_rejects_missing_lower_section(self):
        user32, gdi32, native, size = self.native_capture(black_bottom=True)
        with native, self.assertRaisesRegex(OSError, "missing its lower"):
            desktop.capture_windows_client(123, size)
        gdi32.DeleteObject.assert_called_once_with(33)

    def test_native_capture_rejects_incorrect_client_dimensions(self):
        user32, gdi32, native, size = self.native_capture(expected_size=(8, 10))
        with native, self.assertRaisesRegex(OSError, "expected"):
            desktop.capture_windows_client(123, size)
        user32.PrintWindow.assert_not_called()

    def test_demo_capture_failure_exits_without_saving_clipped_image(self):
        app = self.app(demo=True)
        app.root.destroy = Mock()
        output = Path(self.temp.name) / "screenshot.png"
        with patch.object(desktop, "capture_windows_client", side_effect=OSError("PrintWindow failed")), self.assertLogs(level="ERROR"):
            app.capture_demo(output)
        self.assertIsInstance(app.screenshot_error, OSError)
        app.root.destroy.assert_called_once()
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
