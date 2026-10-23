import http.client
import json
import threading
import unittest

import input_control
import pad_control
import receiver


class FakePad:
    """Stands in for a ViGEmBus pad so the protocol is testable off-Windows."""

    def __init__(self, available=True, error=""):
        self.available = available
        self.error = error
        self.applied = []
        self.closed = False

    def apply(self, state):
        if not self.available:
            raise OSError("原生手柄不可用：" + self.error)
        self.applied.append(state)
        return "OK"

    def reset(self):
        self.applied.append("reset")

    def close(self):
        self.closed = True


class FakeController:
    def __init__(self):
        self.calls = []

    def execute(self, payload):
        self.calls.append(payload)
        return "OK"

    def release_all(self):
        self.calls.append("release_all")


class NormalizeTests(unittest.TestCase):
    def test_defaults_are_neutral(self):
        state = pad_control.normalize({})
        self.assertEqual(state["lx"], 0.0)
        self.assertEqual(state["rt"], 0.0)
        self.assertEqual(state["buttons"], ())

    def test_values_are_clamped_to_the_valid_range(self):
        state = pad_control.normalize({"lx": -4, "ly": 9, "rt": -2, "lt": 3})
        self.assertEqual((state["lx"], state["ly"]), (-1.0, 1.0))
        self.assertEqual((state["lt"], state["rt"]), (1.0, 0.0))

    def test_triggers_may_arrive_as_buttons(self):
        state = pad_control.normalize({"buttons": ["lt", "a"]})
        self.assertEqual(state["lt"], 1.0)
        self.assertEqual(state["buttons"], ("a",))

    def test_malformed_states_are_rejected(self):
        for bad in (None, [], {"lx": "1"}, {"lx": True}, {"buttons": "a"},
                    {"buttons": ["a", "nope"]}, {"buttons": [1]}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                pad_control.normalize(bad)


class PadEndpointTests(unittest.TestCase):
    def setUp(self):
        self.pad = FakePad()
        self.controller = FakeController()
        self.server = receiver.create_server(host="127.0.0.1", port=0, token="test-token",
                                            controller=self.controller, pad=self.pad)
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

    def post_pad(self, payload, headers=None, token_header="test-token"):
        merged = {"Content-Type": "application/json"}
        if token_header:
            merged["X-WatchMouse-Token"] = token_header
        merged.update(headers or {})
        return self.request("POST", "/api/pad", json.dumps(payload).encode("utf-8"), merged)

    def test_status_reports_the_native_backend(self):
        status, _, body = self.request(path="/api/status?token=test-token")
        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertTrue(payload["nativeGamepad"])
        self.assertEqual(payload["padBackend"], "vigem")
        self.assertIn("gamepad.native", payload["features"])

    def test_status_falls_back_to_keyboard_mapping(self):
        self.server.pad = FakePad(available=False, error="需要先安装 ViGEmBus 驱动")
        _, _, body = self.request(path="/api/status?token=test-token")
        payload = json.loads(body)
        self.assertFalse(payload["nativeGamepad"])
        self.assertEqual(payload["padBackend"], "keyboard")
        self.assertIn("ViGEmBus", payload["padError"])

    def test_snapshot_is_applied_and_counted(self):
        status, _, body = self.post_pad({"token": "test-token",
                                         "pad": {"lx": 0.5, "ly": -0.25, "buttons": ["a", "rt"]}})
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["result"], "OK")
        state = self.pad.applied[-1]
        self.assertEqual((state["lx"], state["ly"]), (0.5, -0.25))
        self.assertEqual(state["rt"], 1.0)
        self.assertEqual(state["buttons"], ("a",))
        _, _, status_body = self.request(path="/api/status?token=test-token")
        self.assertEqual(json.loads(status_body)["commandCount"], 1)

    def test_neutral_snapshot_releases_everything(self):
        self.post_pad({"token": "test-token", "pad": {"buttons": ["a"]}})
        self.post_pad({"token": "test-token", "pad": {"buttons": []}})
        self.assertEqual(self.pad.applied[-1]["buttons"], ())
        self.assertEqual(self.pad.applied[-1]["lt"], 0.0)

    def test_pad_requires_a_valid_token_and_json(self):
        status, _, _ = self.post_pad({"token": "wrong", "pad": {}}, token_header=None)
        self.assertEqual(status, 401)
        status, _, _ = self.request("POST", "/api/pad", b"pad=1", {"Content-Type": "application/x-www-form-urlencoded"})
        self.assertEqual(status, 415)
        status, _, _ = self.post_pad({"token": "test-token", "pad": {"buttons": ["nope"]}})
        self.assertEqual(status, 400)
        self.assertEqual(self.pad.applied, [])

    def test_cross_origin_pad_request_is_rejected(self):
        status, _, _ = self.post_pad({"token": "test-token", "pad": {}}, {"Origin": "http://evil.example"})
        self.assertEqual(status, 403)
        self.assertEqual(self.pad.applied, [])

    def test_unavailable_pad_returns_409_without_touching_keys(self):
        self.server.pad = FakePad(available=False, error="未安装 vgamepad（pip install vgamepad）")
        status, _, body = self.post_pad({"token": "test-token", "pad": {"buttons": ["a"]}})
        self.assertEqual(status, 409, body)
        self.assertEqual(self.controller.calls, [])

    def test_shutdown_closes_the_pad(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)
        self.assertTrue(self.pad.closed)


if __name__ == "__main__":
    unittest.main()