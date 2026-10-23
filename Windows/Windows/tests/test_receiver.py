"""Protocol and input safety checks. All keyboard/mouse injection is mocked."""
from __future__ import annotations

import http.client
from html.parser import HTMLParser
import json
import socket
from pathlib import Path
import sys
import threading
import time
import unittest
import tempfile
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlparse
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import input_control
import receiver


SCANCODE, KEYUP, EXTENDED = 0x0008, 0x0002, 0x0001


def press(name):
    """Keyboard event the way a real keyboard reports it: scancode, not VK."""
    return ("key", 0, input_control.SCAN[name],
            SCANCODE | (EXTENDED if name in input_control.EXTENDED else 0))


def release(name):
    event = list(press(name))
    event[3] |= KEYUP
    return tuple(event)


def snapshot(items):
    return [
        ("key", item.ki.wVk, item.ki.wScan, item.ki.dwFlags) if item.type == 1
        else ("mouse", item.mi.dx, item.mi.dy, item.mi.mouseData, item.mi.dwFlags)
        for item in items
    ]


class WatchLinks(HTMLParser):
    """Read watch controls the way a browser receives them, including &amp;."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.feed(source)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and "control" in attrs.get("class", "").split():
            self.links.append(attrs["href"])


class InputSafetyTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.controller = input_control.InputController(sender=lambda items: self.calls.append(snapshot(items)))

    def tearDown(self):
        self.controller.release_all()

    def events(self):
        return [event for call in self.calls for event in call]

    def test_ping_does_not_inject_input(self):
        self.assertEqual("PONG", self.controller.execute({"command": "PING"}))
        self.assertEqual([], self.calls)

    def test_unicode_text_preserves_chinese_and_supplementary_character(self):
        self.controller.execute({"text": "中文A🙂"})
        units = [0x4E2D, 0x6587, 0x41, 0xD83D, 0xDE42]
        expected = [("key", 0, unit, flag) for unit in units for flag in (4, 6)]
        self.assertEqual(expected, self.events())

    def test_line_endings_and_tab_use_control_keys(self):
        self.controller.execute({"text": "A\r\nB\r\t"})
        self.assertEqual([
            ("key", 0, 65, 4), ("key", 0, 65, 6),
            press("enter"), release("enter"),
            ("key", 0, 66, 4), ("key", 0, 66, 6),
            press("enter"), release("enter"),
            press("tab"), release("tab"),
        ], self.events())

    def test_shortcut_holds_modifiers_and_releases_in_reverse_order(self):
        self.controller.execute({"key": "a", "modifiers": ["ctrl", "shift", "ctrl"]})
        self.assertEqual([
            press("ctrl"), press("shift"),
            press("a"), release("a"),
            release("shift"), release("ctrl"),
        ], self.events())

    def test_extended_key_and_windows_modifier_flags(self):
        self.controller.execute({"key": "LEFT", "modifiers": ["win"]})
        self.assertEqual([
            press("win"), press("left"),
            release("left"), release("win"),
        ], self.events())

    def test_backspace_uses_nonextended_scancode(self):
        self.controller.execute({"key": "backspace"})
        self.assertEqual([press("backspace"), release("backspace")], self.events())

    def test_keys_are_sent_as_hardware_scancodes(self):
        """Games read scancodes; a virtual-key-only event is invisible to them."""
        self.controller.execute({"key": "w", "modifiers": ["ctrl"]})
        self.assertEqual([
            ("key", 0, input_control.SCAN["ctrl"], SCANCODE),
            ("key", 0, input_control.SCAN["w"], SCANCODE),
            ("key", 0, input_control.SCAN["w"], SCANCODE | KEYUP),
            ("key", 0, input_control.SCAN["ctrl"], SCANCODE | KEYUP),
        ], self.events())

    def test_scancode_falls_back_to_virtual_key_when_layout_has_none(self):
        """A layout without a scancode for the key still has to reach the app."""
        self.controller.user32 = Mock()
        self.controller.user32.MapVirtualKeyW.return_value = 0
        saved = input_control.SCAN.pop("f12")
        try:
            event = self.controller._key_event("f12")
        finally:
            input_control.SCAN["f12"] = saved
            self.controller._scans.pop("f12", None)
            self.controller.user32 = None
        self.assertEqual(input_control.VK["f12"], event.ki.wVk)
        self.assertEqual(0, event.ki.wScan)
        self.assertEqual(0, event.ki.dwFlags & input_control.KEYEVENTF_SCANCODE)

    def test_forward_delete_uses_extended_scancode(self):
        self.controller.execute({"key": "delete"})
        self.assertEqual([press("delete"), release("delete")], self.events())
        self.assertEqual(EXTENDED, self.events()[0][3] & EXTENDED)

    def test_failed_shortcut_releases_main_key_and_all_modifiers(self):
        def fail_once(items):
            self.calls.append(snapshot(items))
            if len(self.calls) == 1:
                raise OSError("partial injection")
        self.controller.sender = fail_once
        with self.assertRaises(OSError):
            self.controller.execute({"key": "a", "modifiers": ["ctrl", "shift"]})
        self.assertEqual([
            release("a"), release("shift"), release("ctrl"),
        ], self.calls[1])

    def test_native_sender_rejects_zero_or_partial_sendinput(self):
        for count in (0, 1):
            with self.subTest(count=count):
                self.controller.user32 = Mock()
                self.controller.user32.SendInput.return_value = count
                with self.assertRaises(OSError):
                    self.controller._native_send([input_control.key(65), input_control.key(65, flags=2)])

    def test_invalid_payloads_never_inject_input(self):
        payloads = [
            {}, {"command": "C", "text": "a"}, {"command": None},
            {"command": "M 0"}, {"command": "M 4097,0"},
            {"command": "M 1,2,3"}, {"command": "M NaN,1"},
            {"command": "S 101"}, {"command": "UNKNOWN"},
            {"key": "unsupported"}, {"key": "a", "modifiers": "ctrl"},
            {"key": "a", "modifiers": ["Ctrl"]}, {"key": "a", "modifiers": [None]},
            {"text": ""}, {"text": 123}, {"text": "a" * 4001},
            {"text": "bad\x00text"}, {"text": "\ud800"},
        ]
        for payload in payloads:
            with self.subTest(payload=str(payload)[:80]):
                with self.assertRaises((ValueError, TypeError)):
                    self.controller.execute(payload)
                self.assertEqual([], self.calls)

    def test_negative_wheel_data_is_encoded_as_unsigned_dword(self):
        self.controller.execute({"command": "S -2"})
        self.assertEqual([("mouse", 0, 0, 0xFFFFFF10, 0x0800)], self.events())

    def test_drag_expiry_releases_button_without_waiting(self):
        self.controller.execute({"command": "MD"})
        self.controller.drag_timer.cancel()
        self.controller.last_activity = time.monotonic() - 6
        self.controller._drag_expired()
        self.assertFalse(self.controller.dragging)
        self.assertEqual([0x0002, 0x0004], [event[-1] for event in self.events()])

    def test_repeated_drag_down_does_not_add_unmatched_press(self):
        self.controller.execute({"command": "MD"})
        self.controller.execute({"command": "MD"})
        self.controller.execute({"command": "MU"})
        self.assertEqual([0x0002, 0x0004], [event[-1] for event in self.events()])

    def test_gamepad_key_holds_down_until_the_phone_releases_it(self):
        self.controller.execute({"key": "space", "state": "down"})
        self.assertEqual([press("space")], self.events())
        self.assertEqual({"space"}, self.controller.held_keys)
        self.controller.execute({"key": "space", "state": "up"})
        self.assertEqual([press("space"), release("space")], self.events())
        self.assertEqual(set(), self.controller.held_keys)

    def test_repeated_hold_and_release_never_duplicate_events(self):
        for state in ("down", "down", "up", "up"):
            self.controller.execute({"key": "w", "state": state})
        self.assertEqual([press("w"), release("w")], self.events())

    def test_gamepad_release_frees_every_held_key(self):
        for name in ("w", "d", "space"):
            self.controller.execute({"key": name, "state": "down"})
        self.calls.clear()
        self.controller.execute({"command": "MU"})
        released = sorted(event[2] for event in self.events() if event[0] == "key" and event[-1] & KEYUP)
        self.assertEqual(sorted(input_control.SCAN[name] for name in ("w", "d", "space")), released)
        self.assertEqual(set(), self.controller.held_keys)

    def test_stuck_gamepad_key_is_released_after_the_phone_stops_sending(self):
        self.controller.execute({"key": "w", "state": "down"})
        self.calls.clear()
        self.controller.last_activity = time.monotonic() - 6
        self.controller._hold_expired()
        self.assertEqual([release("w")], self.events())
        self.assertEqual(set(), self.controller.held_keys)

    def test_hold_and_release_reject_bad_state_and_modifiers(self):
        for payload in (
            {"key": "w", "state": "pressed"},
            {"key": "w", "state": 1},
            {"key": "w", "state": "down", "modifiers": ["ctrl"]},
        ):
            with self.subTest(payload=str(payload)):
                with self.assertRaises((ValueError, TypeError)):
                    self.controller.execute(payload)
                self.assertEqual([], self.calls)

    def test_failed_drag_release_still_clears_timer_and_local_state(self):
        self.controller.execute({"command": "MD"})
        self.controller.sender = Mock(side_effect=OSError("injection blocked"))
        with self.assertRaises(OSError):
            self.controller.release_all()
        self.assertFalse(self.controller.dragging)
        self.assertIsNone(self.controller.drag_timer)

    def test_concurrent_text_and_shortcut_cannot_interleave_batches(self):
        first_batch = threading.Event()
        continue_text = threading.Event()
        calls = []
        def blocking_sender(items):
            calls.append(snapshot(items))
            if not first_batch.is_set():
                first_batch.set()
                self.assertTrue(continue_text.wait(timeout=2))
        self.controller.sender = blocking_sender
        text_worker = threading.Thread(target=lambda: self.controller.execute({"text": "a" * 130}))
        key_worker = threading.Thread(target=lambda: self.controller.execute({"key": "v", "modifiers": ["ctrl"]}))
        text_worker.start()
        self.assertTrue(first_batch.wait(timeout=2))
        key_worker.start()
        continue_text.set()
        text_worker.join(timeout=2)
        key_worker.join(timeout=2)
        self.assertFalse(text_worker.is_alive())
        self.assertFalse(key_worker.is_alive())
        self.assertEqual(4, len(calls))
        self.assertTrue(all(event[1] == 0 for batch in calls[:3] for event in batch))
        self.assertEqual(press("ctrl"), calls[-1][0])


class ReceiverProtocolTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.controller = input_control.InputController(sender=lambda items: self.calls.append(snapshot(items)))
        self.server = receiver.create_server(host="127.0.0.1", port=0, token="test-token", controller=self.controller)
        self.worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        self.worker.start()
        self.port = self.server.server_port

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def request(self, method="GET", path="/api/status", body=None, headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read().decode("utf-8")
        finally:
            connection.close()

    def command(self, payload, headers=None):
        merged = {"Content-Type": "application/json", "X-WatchMouse-Token": "test-token", **(headers or {})}
        return self.request("POST", "/api/command", json.dumps(payload, ensure_ascii=False).encode("utf-8"), merged)

    def wait_connections(self, count, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with self.server._connection_lock:
                if len(self.server._connections) == count:
                    return
            time.sleep(0.005)
        self.fail(f"Expected {count} active connections, got {len(self.server._connections)}")

    def raw_exchange(self, data, half_close=False):
        """Consume a response on a socket, including an optional trailing request."""
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            connection.sendall(data)
            if half_close:
                connection.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(connection)
            response.begin()
            result = response.status, dict(response.getheaders()), response.read()
            self.assert_socket_closed(connection)
            return result
        finally:
            connection.close()

    def assert_socket_closed(self, connection):
        try:
            self.assertEqual(b"", connection.recv(1), "Socket must close without another response")
        except ConnectionResetError:
            # Windows may reset when the peer closes with unread input bytes.
            pass

    def test_commands_status_and_no_content_share_one_http11_connection(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        accepted = Mock(wraps=self.server.process_request)
        try:
            with patch.object(self.server, "process_request", accepted):
                for command in ("M 1,2", "S -1", "C"):
                    connection.request("POST", "/api/command", json.dumps({"command": command}),
                                       {"Content-Type": "application/json", "X-WatchMouse-Token": "test-token"})
                    response = connection.getresponse()
                    self.assertEqual(11, response.version)
                    self.assertEqual(200, response.status)
                    self.assertTrue(json.loads(response.read())["ok"])
                    self.assertFalse(response.will_close)
                connection.request("GET", "/favicon.ico")
                response = connection.getresponse()
                self.assertEqual(204, response.status)
                self.assertIsNone(response.getheader("Content-Length"))
                self.assertEqual(b"", response.read())
                connection.request("GET", "/api/status?token=test-token")
                self.assertEqual(3, json.loads(connection.getresponse().read())["commandCount"])
                self.assertEqual(1, accepted.call_count)
            with self.server._connection_lock:
                peer = next(iter(self.server._connections))
                # BSD/macOS may return an enabled flag bitmask rather than literal 1.
                self.assertNotEqual(0, peer.getsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY))
        finally:
            connection.close()

    def test_fully_consumed_errors_do_not_break_next_request(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
        try:
            for body, headers, status in (
                ("{broken", {"Content-Type": "application/json"}, 400),
                ('{"command":"C"}', {"Content-Type": "application/json"}, 401),
                ("command=C", {"Content-Type": "text/plain"}, 415),
            ):
                connection.request("POST", "/api/command", body, headers)
                response = connection.getresponse()
                self.assertEqual(status, response.status)
                response.read()
                self.assertFalse(response.will_close)
            connection.request("POST", "/api/command", '{"command":"C"}',
                               {"Content-Type": "application/json", "X-WatchMouse-Token": "test-token"})
            response = connection.getresponse()
            self.assertEqual(200, response.status)
            response.read()
            self.assertEqual(1, self.server.command_count)
            self.assertEqual(1, len(self.calls))
        finally:
            connection.close()

    def test_rejected_unread_bodies_cannot_execute_a_trailing_request(self):
        trailing = b"GET /c?q=C&token=test-token HTTP/1.1\r\nHost: localhost\r\n\r\n"
        cases = (
            (b"POST /missing HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\n\r\nx", 404),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nOrigin: http://other.example\r\nContent-Length: 1\r\n\r\nx", 403),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: 32769\r\n\r\nx", 400),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: -1\r\n\r\nx", 400),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: 999999999999999999999999\r\n\r\nx", 400),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\nContent-Length: 1\r\n\r\nx", 400),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n", 400),
            (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nTransfer-Encoding: chunked\r\nContent-Length: 1\r\n\r\nx", 400),
            (b"GET /c?q=C&token=test-token HTTP/1.1\r\nHost: localhost\r\nContent-Length: 1\r\n\r\nx", 400),
        )
        for data, expected_status in cases:
            with self.subTest(data=data[:90]):
                status, headers, _ = self.raw_exchange(data + trailing)
                self.assertEqual(expected_status, status)
                self.assertEqual("close", headers["Connection"])
                self.assertEqual([], self.calls)
                self.assertEqual(0, self.server.command_count)

    def test_incomplete_body_cannot_execute_even_if_received_bytes_are_valid_json(self):
        body = b'{"command":"C"}'
        data = (b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                b"X-WatchMouse-Token: test-token\r\nContent-Length: " + str(len(body) + 1).encode() + b"\r\n\r\n" + body)
        status, headers, result = self.raw_exchange(data, half_close=True)
        self.assertEqual(400, status)
        self.assertIn("不完整", json.loads(result)["error"])
        self.assertEqual("close", headers["Connection"])
        self.assertEqual([], self.calls)

    def test_fragmented_body_is_read_completely_once(self):
        body = json.dumps({"text": "中文🙂"}, ensure_ascii=False).encode("utf-8")
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            connection.sendall(b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                               b"X-WatchMouse-Token: test-token\r\nConnection: close\r\nContent-Length: "
                               + str(len(body)).encode() + b"\r\n\r\n" + body[:12])
            self.wait_connections(1)
            self.assertEqual([], self.calls)
            connection.sendall(body[12:])
            response = http.client.HTTPResponse(connection)
            response.begin()
            self.assertEqual(200, response.status)
            response.read()
            self.assertEqual(1, self.server.command_count)
            self.assertEqual(8, len(self.calls[0]))
        finally:
            connection.close()

    def test_expect_continue_is_flushed_before_body_is_sent(self):
        body = b'{"command":"C"}'
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            connection.sendall(b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
                               b"X-WatchMouse-Token: test-token\r\nExpect: 100-continue\r\nConnection: close\r\nContent-Length: "
                               + str(len(body)).encode() + b"\r\n\r\n")
            interim = connection.makefile("rb")
            try:
                self.assertEqual(b"HTTP/1.1 100 Continue\r\n", interim.readline())
                self.assertEqual(b"\r\n", interim.readline())
            finally:
                interim.close()
            self.assertEqual([], self.calls)
            connection.sendall(body)
            response = http.client.HTTPResponse(connection)
            response.begin()
            self.assertEqual(200, response.status)
            response.read()
            self.assertEqual(1, len(self.calls))
        finally:
            connection.close()

    def test_expect_continue_rejects_oversize_without_waiting_for_body(self):
        status, headers, _ = self.raw_exchange(
            b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nExpect: 100-continue\r\nContent-Length: 32769\r\n\r\n")
        self.assertEqual(400, status)
        self.assertEqual("close", headers["Connection"])
        self.assertEqual([], self.calls)

    def test_idle_connection_and_stalled_body_expire(self):
        self.server.connection_timeout = .1
        connection = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            connection.sendall(b"GET /api/status HTTP/1.1\r\nHost: localhost\r\n\r\n")
            response = http.client.HTTPResponse(connection)
            response.begin()
            response.read()
            self.assertEqual(b"", connection.recv(1))
            self.wait_connections(0)
        finally:
            connection.close()
        status, headers, body = self.raw_exchange(
            b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: 50\r\n\r\nx")
        self.assertEqual(400, status)
        self.assertEqual("close", headers["Connection"])
        self.assertIn("超时", json.loads(body)["error"])
        self.assertEqual([], self.calls)

    def test_connection_limit_does_not_spawn_extra_handler_and_recovers(self):
        self.server.max_connections = 2
        connections = [socket.create_connection(("127.0.0.1", self.port), timeout=2) for _ in range(2)]
        try:
            self.wait_connections(2)
            with patch.object(self.server, "process_request_thread", wraps=self.server.process_request_thread) as handlers:
                extra = socket.create_connection(("127.0.0.1", self.port), timeout=2)
                try:
                    self.assertEqual(b"", extra.recv(1))
                    self.assertEqual(0, handlers.call_count)
                finally:
                    extra.close()
            connections.pop().close()
            self.wait_connections(1)
            self.assertEqual(200, self.command({"command": "PING"})[0])
        finally:
            for connection in connections:
                connection.close()

    def test_shutdown_interrupts_idle_and_partial_reads_then_refuses_input(self):
        # On Windows a recv already blocked in select can finish only when its
        # original socket timeout expires, despite cross-thread shutdown().
        self.server.connection_timeout = .2
        idle = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        partial = socket.create_connection(("127.0.0.1", self.port), timeout=2)
        try:
            partial.sendall(b"POST /api/command HTTP/1.1\r\nHost: localhost\r\nContent-Length: 20\r\n\r\nx")
            self.wait_connections(2)
            started = time.monotonic()
            self.server.shutdown()
            self.server.server_close()
            self.assertLess(time.monotonic() - started, 1)
            self.assert_socket_closed(idle)
            self.assert_socket_closed(partial)
            self.wait_connections(0)
            with self.assertRaises(OSError):
                self.server.execute({"command": "C"}, "127.0.0.1")
            self.assertEqual([], self.calls)
        finally:
            idle.close()
            partial.close()

    def test_close_waits_for_current_input_before_releasing_and_denies_queued_input(self):
        entered, finish, closing = threading.Event(), threading.Event(), threading.Event()
        events, errors = [], []
        def blocked_input(payload):
            events.append("execute")
            entered.set()
            finish.wait(timeout=2)
            return "OK"
        def close():
            closing.set()
            self.server.shutdown()
            self.server.server_close()
        def queued():
            try:
                self.server.execute({"command": "C"}, "queued")
            except OSError:
                errors.append("stopped")
        with patch.object(self.controller, "execute", side_effect=blocked_input), \
             patch.object(self.controller, "release_all", side_effect=lambda: events.append("release")):
            executing = threading.Thread(target=self.server.execute, args=({"command": "C"}, "first"))
            closer = threading.Thread(target=close)
            waiting = threading.Thread(target=queued)
            executing.start()
            try:
                self.assertTrue(entered.wait(timeout=2))
                closer.start()
                self.assertTrue(closing.wait(timeout=2))
                self.assertTrue(self.server._closing.wait(timeout=2))
                waiting.start()
                self.assertEqual(["execute"], events)
            finally:
                finish.set()
                executing.join(timeout=2)
                if closer.ident is not None:
                    closer.join(timeout=2)
                if waiting.ident is not None:
                    waiting.join(timeout=2)
            self.assertFalse(executing.is_alive())
            self.assertFalse(closer.is_alive())
            self.assertFalse(waiting.is_alive())
            self.assertEqual(["execute", "release"], events)
            self.assertEqual(["stopped"], errors)

    def test_permission_state_and_error_codes_remain_compatible(self):
        with patch.object(self.controller, "input_error", create=True, return_value="需要辅助功能权限"):
            status, _, body = self.request()
            public = json.loads(body)
            self.assertEqual(200, status)
            self.assertFalse(public["inputReady"])
            self.assertEqual("", public["inputError"])
            self.assertEqual("", public["inputErrorCode"])
            with patch.object(receiver.sys, "platform", "darwin"):
                _, _, body = self.request(path="/api/status?token=test-token")
                paired = json.loads(body)
                self.assertEqual("accessibility_permission", paired["inputErrorCode"])
                self.assertEqual("需要辅助功能权限", paired["inputError"])
        self.controller.sender = Mock(side_effect=OSError("需要辅助功能权限"))
        self.assertEqual("accessibility_permission", json.loads(self.command({"command": "C"})[2])["errorCode"])

    def test_public_status_does_not_claim_pairing(self):
        status, headers, body = self.request()
        self.assertEqual(200, status)
        data = json.loads(body)
        self.assertEqual("WatchMouse", data["app"])
        self.assertFalse(data["paired"])
        self.assertEqual("", data["lastClient"])
        self.assertEqual("no-store", headers["Cache-Control"])

    def test_status_accepts_header_or_query_token(self):
        for path, headers in (("/api/status?token=test-token", {}), ("/api/status", {"X-WatchMouse-Token": "test-token"})):
            with self.subTest(path=path):
                status, _, body = self.request(path=path, headers=headers)
                self.assertEqual(200, status)
                self.assertTrue(json.loads(body)["paired"])

    def test_status_reports_keyboard_mode_and_elevation(self):
        status, _, body = self.request(path="/api/status?token=test-token")
        payload = json.loads(body)
        self.assertEqual(200, status)
        self.assertEqual("scancode", payload["keyboardMode"])
        self.assertIn("elevated", payload)
        self.assertIn("gamepad.native", payload["features"])

    def test_nonascii_token_is_rejected_with_http_response(self):
        wrong_token = urlencode({"token": "你好"})
        status, _, body = self.request(path="/api/status?" + wrong_token)
        self.assertEqual(200, status)
        self.assertFalse(json.loads(body)["paired"])
        status, _, _ = self.request("POST", "/api/command", json.dumps({"token": "你好", "command": "C"}).encode(), {"Content-Type": "application/json"})
        self.assertEqual(401, status)
        self.assertEqual([], self.calls)

    def test_legacy_ping_is_public_but_click_requires_pairing(self):
        status, _, body = self.request(path="/c?q=PING")
        self.assertEqual((200, "PONG"), (status, body))
        status, _, _ = self.request(path="/c?q=C")
        self.assertEqual(401, status)
        self.assertEqual([], self.calls)
        status, _, body = self.request(path="/c?q=C&token=test-token")
        self.assertEqual((200, "OK"), (status, body))
        self.assertEqual(2, len(self.calls[0]))

    def test_authenticated_unicode_command_reports_result_and_count(self):
        status, _, body = self.command({"text": "你好🙂"})
        self.assertEqual(200, status)
        self.assertEqual({"ok": True, "result": "OK"}, json.loads(body))
        status, _, body = self.request(headers={"X-WatchMouse-Token": "test-token"})
        self.assertEqual(1, json.loads(body)["commandCount"])
        self.assertEqual(8, len(self.calls[0]))

    def test_missing_or_wrong_token_cannot_inject(self):
        for token in (None, "wrong", 123, ["test-token"]):
            payload = {"command": "C"}
            if token is not None:
                payload["token"] = token
            status, _, _ = self.request("POST", "/api/command", json.dumps(payload), {"Content-Type": "application/json"})
            self.assertEqual(401, status)
        self.assertEqual([], self.calls)

    def test_cross_origin_request_is_rejected_even_when_token_valid(self):
        status, _, _ = self.command({"command": "C"}, {"Origin": "http://other.example"})
        self.assertEqual(403, status)
        self.assertEqual([], self.calls)
        status, _, _ = self.command({"command": "PING"}, {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(200, status)

    def test_malformed_json_and_non_object_body_get_400(self):
        for body in (b"{broken", b"[]", b"null", b'"text"', b"\xff"):
            with self.subTest(body=body):
                status, _, text = self.request("POST", "/api/command", body, {"Content-Type": "application/json"})
                self.assertEqual(400, status)
                self.assertFalse(json.loads(text)["ok"])
        self.assertEqual([], self.calls)

    def test_oversized_body_and_invalid_operations_are_rejected(self):
        status, _, _ = self.request("POST", "/api/command", b"x" * 32769, {"Content-Type": "application/json"})
        self.assertEqual(400, status)
        for payload in ({"text": "x" * 4001}, {"command": "M 5000,0"}, {"key": "a", "modifiers": ["bad"]}, {"text": "a", "command": "C"}):
            self.assertEqual(400, self.command(payload)[0])
        self.assertEqual([], self.calls)

    def test_non_json_api_request_gets_415(self):
        status, _, _ = self.request("POST", "/api/command", "command=C&token=test-token", {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(415, status)
        self.assertEqual([], self.calls)

    def test_injection_failure_gets_409_and_does_not_increment_count(self):
        self.controller.sender = Mock(side_effect=OSError("input blocked"))
        status, _, body = self.command({"command": "C"})
        self.assertEqual(409, status)
        self.assertEqual({"ok": False, "error": "input blocked", "errorCode": "input_unavailable"}, json.loads(body))
        self.assertEqual(0, self.server.command_count)

    def test_watch_page_requires_no_javascript_and_escapes_messages(self):
        path = "/watch?" + urlencode({"token": "test-token", "message": "<script>alert(1)</script>"})
        status, _, body = self.request(path=path)
        self.assertEqual(200, status)
        self.assertIn("method='post'", body)
        self.assertIn("name='text'", body)
        self.assertNotIn("<script", body)
        self.assertIn("&lt;script&gt;", body)
        controls = WatchLinks(body).links
        self.assertEqual(14, len(controls))
        nonces = []
        for link in controls:
            self.assertEqual("/watch", urlparse(link).path)
            query = parse_qs(urlparse(link).query)
            self.assertEqual(["test-token"], query["token"])
            self.assertNotIn("command", query)
            nonces.append(query["action"][0])
        self.assertEqual(len(nonces), len(set(nonces)))
        self.assertEqual([], self.calls)

    def test_watch_rendered_link_executes_once_and_redirect_removes_action(self):
        _, _, page = self.request(path="/watch?token=test-token")
        link = WatchLinks(page).links[0]
        status, headers, _ = self.request(path=link)
        self.assertEqual(303, status)
        location = headers["Location"]
        self.assertNotIn("action", parse_qs(urlparse(location).query))
        self.assertEqual(1, self.server.command_count)
        self.assertEqual(1, len(self.calls))
        first_calls = list(self.calls)
        status, headers, _ = self.request(path=link)
        self.assertEqual(303, status)
        self.assertIn("已处理", parse_qs(urlparse(headers["Location"]).query)["message"][0])
        self.assertEqual(first_calls, self.calls)
        self.assertEqual(1, self.server.command_count)
        for _ in range(2):
            status, _, fresh_page = self.request(path=location)
            self.assertEqual(200, status)
            self.assertNotIn(link, WatchLinks(fresh_page).links)
        self.assertEqual(1, self.server.command_count)

    def test_watch_bad_token_cannot_execute_or_consume_valid_link(self):
        nonce = self.server.register_watch_action("C")
        for token in ("wrong", "你好", ""):
            path = "/watch?" + urlencode({"token": token, "action": nonce})
            self.assertEqual(401, self.request(path=path)[0])
            self.assertEqual([], self.calls)
        good_path = "/watch?" + urlencode({"token": "test-token", "action": nonce})
        self.assertEqual(303, self.request(path=good_path)[0])
        self.assertEqual(1, len(self.calls))
        self.assertEqual(1, self.server.command_count)

    def test_watch_unknown_or_expired_link_does_not_execute(self):
        with patch.object(receiver.time, "monotonic", return_value=100):
            nonce = self.server.register_watch_action("C")
        with patch.object(receiver.time, "monotonic", return_value=401):
            for action in (nonce, "unknown-nonce"):
                path = "/watch?" + urlencode({"token": "test-token", "action": action})
                status, headers, _ = self.request(path=path)
                self.assertEqual(303, status)
                self.assertIn("已处理", parse_qs(urlparse(headers["Location"]).query)["message"][0])
        self.assertEqual([], self.calls)
        self.assertEqual(0, self.server.command_count)

    def test_watch_nonce_can_be_consumed_by_only_one_concurrent_request(self):
        nonce = self.server.register_watch_action("C")
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.server.consume_watch_action, [nonce] * 24))
        self.assertEqual(1, results.count("C"))
        self.assertEqual(23, results.count(None))
        self.assertEqual([], self.calls)

    def test_watch_nonce_storage_bounds_evict_oldest_and_clear_expired(self):
        with patch.object(receiver.time, "monotonic", return_value=100):
            oldest = self.server.register_watch_action("C")
            for _ in range(2048):
                newest = self.server.register_watch_action("RC")
            self.assertIsNone(self.server.consume_watch_action(oldest))
            self.assertEqual("RC", self.server.consume_watch_action(newest))
            soon_expired = self.server.register_watch_action("C")
        with patch.object(receiver.time, "monotonic", return_value=401):
            fresh = self.server.register_watch_action("K enter")
            self.assertIsNone(self.server.consume_watch_action(soon_expired))
            self.assertEqual("K enter", self.server.consume_watch_action(fresh))

    def test_watch_failed_injection_cannot_reexecute_on_replay(self):
        nonce = self.server.register_watch_action("C")
        self.controller.sender = Mock(side_effect=OSError("input blocked <script>"))
        path = "/watch?" + urlencode({"token": "test-token", "action": nonce})
        status, headers, _ = self.request(path=path)
        self.assertEqual(303, status)
        self.assertIn("input blocked", parse_qs(urlparse(headers["Location"]).query)["message"][0])
        status, _, page = self.request(path=headers["Location"])
        self.assertEqual(200, status)
        self.assertIn("&lt;script&gt;", page)
        self.assertNotIn("<script>", page)
        self.assertEqual(303, self.request(path=path)[0])
        self.assertEqual(1, self.controller.sender.call_count)
        self.assertEqual(0, self.server.command_count)

    def test_watch_post_redirects_to_clean_page_and_refresh_does_not_repeat(self):
        form = urlencode({"token": "test-token", "command": "C"})
        status, headers, _ = self.request("POST", "/watch", form, {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(303, status)
        location = headers["Location"]
        self.assertEqual("/watch", urlparse(location).path)
        self.assertNotIn("command", parse_qs(urlparse(location).query))
        for _ in range(2):
            self.assertEqual(200, self.request(path=location)[0])
        self.assertEqual(1, len(self.calls))
        self.assertEqual(1, self.server.command_count)

    def test_watch_empty_text_is_rejected_instead_of_becoming_ping(self):
        form = urlencode({"token": "test-token", "text": ""})
        status, headers, _ = self.request("POST", "/watch", form, {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(303, status)
        message = parse_qs(urlparse(headers["Location"]).query)["message"][0]
        self.assertNotEqual("连接正常", message)
        self.assertIn("4000", message)
        self.assertEqual(0, self.server.command_count)
        self.assertEqual([], self.calls)

    def test_watch_bad_token_does_not_execute(self):
        form = urlencode({"token": "wrong", "command": "C"})
        self.assertEqual(401, self.request("POST", "/watch", form)[0])
        self.assertEqual([], self.calls)


    def test_watch_language_defaults_english_and_keeps_chinese_actions(self):
        _, _, english = self.request(path='/watch?token=test-token')
        self.assertIn("lang='en'", english)
        self.assertIn('Play / Pause', english)
        self.assertIn("name='lang' value='en'", english)
        _, _, chinese = self.request(path='/watch?token=test-token&lang=zh-CN')
        self.assertIn("lang='zh-CN'", chinese)
        self.assertIn('播放 / 暂停', chinese)
        link = WatchLinks(chinese).links[0]
        self.assertEqual(['zh-CN'], parse_qs(urlparse(link).query)['lang'])
        status, headers, _ = self.request(path=link)
        self.assertEqual(303, status)
        self.assertEqual(['zh-CN'], parse_qs(urlparse(headers['Location']).query)['lang'])

    def test_watch_localizes_known_windows_input_denial(self):
        self.controller.sender = Mock(side_effect=OSError('Windows 未接受输入。请确认目标窗口没有以管理员身份运行。'))
        nonce = self.server.register_watch_action('C')
        status, headers, _ = self.request(path='/watch?' + urlencode({'token':'test-token','action':nonce,'lang':'en'}))
        self.assertEqual(303,status)
        _, _, page = self.request(path=headers['Location'])
        self.assertIn('Windows rejected input',page)
        self.assertNotIn('Windows 未接受输入',page)

    def test_unknown_paths_do_not_expose_files(self):
        for path in ("/receiver.py", "/../receiver.py", "/%2e%2e/receiver.py", "/config.json"):
            self.assertEqual(404, self.request(path=path)[0])

    def test_shutdown_closes_socket_even_when_drag_release_fails(self):
        self.server.shutdown()
        with patch.object(self.controller, "release_all", side_effect=OSError("release failed")):
            with self.assertRaises(OSError):
                self.server.server_close()
        self.assertEqual(-1, self.server.socket.fileno())



class PairingPersistenceTests(unittest.TestCase):
    def test_settings_keep_pairing_key_across_restart_and_language_change(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(receiver, 'settings_path', return_value=Path(directory)/'config.json'):
                first=receiver.load_settings()
                self.assertGreaterEqual(len(first['token']),16)
                token=first['token']
                first['language']='zh-CN'
                receiver.save_settings(first)
                for _ in range(3):
                    again=receiver.load_settings()
                    self.assertEqual(token,again['token'])
                    self.assertEqual('zh-CN',again['language'])


if __name__ == "__main__":
    unittest.main()
