"""Launcher responsiveness and service lifecycle, without real input or settings."""
from __future__ import annotations

from pathlib import Path
import sys
import threading
import time
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_desktop_language import FakeWidget, desktop


class AppPerformanceTests(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patch.object(desktop.receiver, "load_settings", return_value={"token": "TEST-TOKEN-NEVER-USED", "port": 53514}),
            patch.object(desktop.receiver, "save_settings"),
            patch.object(desktop.WatchMouseApp, "check_network_profile"),
            patch.object(desktop.WatchMouseApp, "update_link", autospec=True),
            patch.object(desktop, "is_admin", return_value=False),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(lambda: [item.stop() for item in reversed(self.patches)])

    def app(self):
        with patch.object(desktop.receiver, "lan_addresses", return_value=["192.168.1.10"]):
            app = desktop.WatchMouseApp(FakeWidget())
            app.address_thread.join(timeout=2)
            self.assertFalse(app.address_thread.is_alive())
        app.poll_events()
        return app

    def test_slow_address_discovery_does_not_block_window_or_touch_tk(self):
        entered, release = threading.Event(), threading.Event()
        main_thread = threading.get_ident()
        calls = []

        def slow_addresses():
            calls.append(threading.get_ident())
            entered.set()
            release.wait(timeout=2)
            return ["192.168.1.20"]

        with patch.object(desktop.receiver, "lan_addresses", side_effect=slow_addresses) as lookup:
            started = time.perf_counter()
            app = desktop.WatchMouseApp(FakeWidget())
            elapsed = time.perf_counter() - started
            try:
                self.assertTrue(entered.wait(timeout=1))
                self.assertLess(elapsed, 0.5)
                self.assertNotEqual(main_thread, calls[0])
                self.assertEqual("", app.ip_var.get())
                self.assertEqual("disabled", app.copy_button["state"])
                self.assertTrue(app.addresses_pending)
                app.refresh_addresses()
                self.assertEqual(1, lookup.call_count)
            finally:
                release.set()
                app.address_thread.join(timeout=2)
        self.assertEqual("", app.ip_var.get(), "Worker must only enqueue, never update Tk variables")
        app.poll_events()
        self.assertEqual("192.168.1.20", app.ip_var.get())
        self.assertFalse(app.addresses_pending)
        self.assertEqual("normal", app.refresh_button["state"])

    def test_refresh_preserves_selected_address_and_network_warning(self):
        app = self.app()
        app.ip_var.set("192.168.1.20")
        app.network_warning = "Public network warning"
        app.apply_addresses(["192.168.1.10", "192.168.1.20"])
        self.assertEqual("192.168.1.20", app.ip_var.get())
        self.assertEqual("Public network warning", app.network_var.get())
        app.apply_addresses([])
        self.assertEqual("127.0.0.1", app.ip_var.get())
        self.assertIn("No local IPv4", app.network_var.get())

    def test_same_link_avoids_reencoding_qr_but_changes_invalidate_cache(self):
        # Call the unpatched method against isolated variables and image mocks.
        app = self.app()
        app.ip_var.set("192.168.1.10")
        fake_qr = Mock()
        fake_qr.get_matrix.return_value = [[0] * 35] * 35
        qrcode = types.SimpleNamespace(QRCode=Mock(return_value=fake_qr), constants=types.SimpleNamespace(ERROR_CORRECT_M=0))
        image_tk = types.ModuleType("PIL.ImageTk")
        image_tk.PhotoImage = Mock(return_value=object())
        with patch.dict(sys.modules, {"qrcode": qrcode, "PIL.ImageTk": image_tk}):
            REAL_UPDATE_LINK(app)
            REAL_UPDATE_LINK(app)
            self.assertEqual(1, qrcode.QRCode.call_count)
            self.assertEqual(1, image_tk.PhotoImage.call_count)
            app.ip_var.set("192.168.1.20")
            REAL_UPDATE_LINK(app)
            self.assertEqual(2, qrcode.QRCode.call_count)
            app.qr_size += 20
            REAL_UPDATE_LINK(app)
            self.assertEqual(3, qrcode.QRCode.call_count)
            app.token = "A DIFFERENT TEST TOKEN"
            REAL_UPDATE_LINK(app)
            self.assertEqual(4, qrcode.QRCode.call_count)

    def test_failed_qr_generation_can_retry_same_link(self):
        app = self.app()
        qrcode = types.SimpleNamespace(QRCode=Mock(side_effect=ValueError("mock encoding failure")), constants=types.SimpleNamespace(ERROR_CORRECT_M=0))
        with patch.dict(sys.modules, {"qrcode": qrcode}), patch.object(desktop.logging, "exception"):
            REAL_UPDATE_LINK(app)
            REAL_UPDATE_LINK(app)
        self.assertEqual(2, qrcode.QRCode.call_count)
        self.assertIsNone(app.qr_cache_key)
        self.assertIn("Copy", app.qr_text.get())

    def test_new_link_failure_removes_previous_qr_and_can_retry(self):
        app = self.app()
        fake_qr = Mock()
        fake_qr.get_matrix.return_value = [[0] * 35] * 35
        qrcode = types.SimpleNamespace(QRCode=Mock(return_value=fake_qr), constants=types.SimpleNamespace(ERROR_CORRECT_M=0))
        image_tk = types.ModuleType("PIL.ImageTk")
        image_tk.PhotoImage = Mock(return_value=object())
        with patch.dict(sys.modules, {"qrcode": qrcode, "PIL.ImageTk": image_tk}), patch.object(desktop.logging, "exception"):
            REAL_UPDATE_LINK(app)
            self.assertIsNotNone(app.qr_image)
            app.ip_var.set("192.168.1.20")
            qrcode.QRCode.side_effect = ValueError("mock encoding failure")
            REAL_UPDATE_LINK(app)
            self.assertEqual("", app.qr_label["image"])
            self.assertIsNone(app.qr_image)
            self.assertIsNone(app.qr_cache_key)
            qrcode.QRCode.side_effect = None
            REAL_UPDATE_LINK(app)
        self.assertIsNotNone(app.qr_image)
        self.assertIn("192.168.1.20", app.qr_cache_key[0])
        self.assertEqual("", app.qr_text.get())

    def test_delayed_start_callback_does_nothing_after_close(self):
        app = self.app()
        app.closing = True
        with patch.object(desktop.threading, "Thread") as thread:
            app.start()
        thread.assert_not_called()
        self.assertFalse(app.busy)

    def test_shutdown_failure_still_releases_server_socket(self):
        server = Mock()
        server.shutdown.side_effect = RuntimeError("mock shutdown failure")
        with self.assertRaisesRegex(RuntimeError, "mock shutdown failure"):
            desktop.shutdown_server(server)
        server.server_close.assert_called_once_with()

    def test_stop_releases_socket_before_restart_event(self):
        app = self.app()
        server = Mock()
        app.server = server
        app.stop(restart=True)
        app.operation_thread.join(timeout=2)
        self.assertIsNone(app.server)
        server.shutdown.assert_called_once_with()
        server.server_close.assert_called_once_with()
        with patch.object(app, "start") as restart:
            app.poll_events()
        restart.assert_called_once_with()
        self.assertEqual("Receiver stopped", app.status.get())

    def test_stop_error_still_closes_socket_and_returns_ui_to_idle(self):
        app = self.app()
        server = Mock()
        server.shutdown.side_effect = RuntimeError("mock shutdown failure")
        app.server = server
        app.stop()
        app.operation_thread.join(timeout=2)
        app.poll_events()
        server.server_close.assert_called_once_with()
        self.assertFalse(app.busy)
        self.assertEqual("normal", app.start_button["state"])

    def test_stale_health_result_cannot_overwrite_stopped_or_restarted_state(self):
        app = self.app()
        app.service_generation = 4
        app.status.set("服务已停止")
        app.health_pending = True
        app.events.put(("health", (3, False)))
        app.poll_events()
        self.assertEqual("Receiver stopped", app.status.get())
        self.assertFalse(app.health_pending)
        app.server = Mock()
        app.status.set("服务运行中")
        app.events.put(("health", (3, False)))
        app.poll_events()
        self.assertEqual("Receiver running", app.status.get())
        app.events.put(("health", (4, False)))
        app.poll_events()
        self.assertEqual("Receiver not responding", app.status.get())

    def test_single_health_request_in_flight_uses_captured_generation(self):
        app = self.app()
        app.server = Mock()
        app.service_generation = 7
        entered, release = threading.Event(), threading.Event()

        def status(*_args):
            entered.set()
            release.wait(timeout=2)
            return {"app": "WatchMouse", "paired": True}

        with patch.object(desktop, "request_json", side_effect=status) as request:
            app.health_check()
            self.assertTrue(entered.wait(timeout=1))
            app.health_check()
            self.assertEqual(1, request.call_count)
            app.service_generation = 8
            app.status.set("服务已停止")
            app.server = None
            release.set()
            kind, value = app.events.get(timeout=2)
        self.assertEqual(("health", (7, True)), (kind, value))
        app.events.put((kind, value))
        app.poll_events()
        self.assertEqual("Receiver stopped", app.status.get())

    def test_idle_polling_backs_off_but_busy_polling_remains_responsive(self):
        app = self.app()
        app.root.scheduled.clear()
        app.poll_events()
        self.assertEqual(250, app.root.scheduled[-1][0])
        app.busy = True
        app.poll_events()
        self.assertEqual(100, app.root.scheduled[-1][0])

    def test_close_during_server_creation_closes_unstarted_server_without_deadlock(self):
        app = self.app()
        server = Mock()
        entered, release = threading.Event(), threading.Event()

        def create(**_options):
            entered.set()
            release.wait(timeout=2)
            return server

        with patch.object(desktop, "request_json", side_effect=OSError("mock no listener")), patch.object(desktop.receiver, "create_server", side_effect=create):
            app.start()
            self.assertTrue(entered.wait(timeout=1))
            try:
                app.close()
            finally:
                release.set()
                app.operation_thread.join(timeout=2)
        self.assertFalse(app.operation_thread.is_alive())
        self.assertIsNone(app.server)
        server.server_close.assert_called_once_with()
        server.shutdown.assert_not_called()
        server.serve_forever.assert_not_called()

    def test_serving_thread_start_failure_closes_socket_without_shutdown_wait(self):
        app = self.app()
        server = Mock(server_address=("0.0.0.0", 53514))
        thread = Mock()
        thread.start.side_effect = RuntimeError("mock thread creation failed")
        with patch.object(desktop, "request_json", side_effect=OSError("mock no listener")), patch.object(desktop.receiver, "create_server", return_value=server), patch.object(desktop.threading, "Thread", return_value=thread), patch.object(desktop.logging, "exception"):
            app.start_worker()
        server.server_close.assert_called_once_with()
        server.shutdown.assert_not_called()
        self.assertIsNone(app.server)
        self.assertEqual("error", app.events.get_nowait()[0])


# Save the method before setUp patches it so QR tests can exercise its real logic.
REAL_UPDATE_LINK = desktop.WatchMouseApp.update_link


if __name__ == "__main__":
    unittest.main()
