"""Independent pad leases and replay protection; no native devices are created."""
from concurrent.futures import ThreadPoolExecutor
import http.client
import json
import socket
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pad_control
import receiver
from test_pad import FakeController, FakePad


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class PadPoolTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.seed = FakePad()
        self.created = [self.seed]

        def factory():
            pad = FakePad()
            self.created.append(pad)
            return pad

        self.factory = Mock(side_effect=factory)
        self.pool = pad_control.PadPool(seed=self.seed, factory=self.factory, clock=self.clock)

    def tearDown(self):
        self.pool.close()

    def assert_code(self, code, operation, *args, **kwargs):
        with self.assertRaises((pad_control.PadSessionError, pad_control.PadRequestError)) as caught:
            operation(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_probe_seed_is_used_by_first_join_and_lazy_devices_are_independent(self):
        self.assertEqual(0, self.pool.info()["activeGamepads"])
        first = self.pool.join("phone-one")
        self.assertEqual({"player": 1, "maxPlayers": 4, "leaseSeconds": 15},
                         {key: value for key, value in first.items() if key != "session"})
        self.assertGreaterEqual(len(first["session"]), 32)
        self.assertEqual(0, self.factory.call_count)
        second = self.pool.join("phone-two")
        self.assertEqual(2, second["player"])
        self.assertNotEqual(first["session"], second["session"])
        self.assertEqual(1, self.factory.call_count)
        self.pool.apply(first["session"], 1, {"lx": .5, "buttons": ["a"]})
        self.pool.apply(second["session"], 1, {"rt": .7, "buttons": ["b"]})
        self.assertEqual(("a",), self.created[0].applied[-1]["buttons"])
        self.assertEqual(.5, self.created[0].applied[-1]["lx"])
        self.assertEqual(("b",), self.created[1].applied[-1]["buttons"])
        self.assertEqual(.7, self.created[1].applied[-1]["rt"])
        self.assertEqual(0, self.created[1].applied[-1]["lx"])

    def test_simultaneous_retries_allocate_one_device_and_one_lease(self):
        with ThreadPoolExecutor(max_workers=8) as workers:
            results = list(workers.map(self.pool.join, ["one-activation"] * 24))
        self.assertTrue(all(result == results[0] for result in results))
        self.assertEqual(1, self.pool.info()["activeGamepads"])
        self.assertEqual(0, self.factory.call_count)

    def test_capacity_is_four_and_fifth_join_does_not_create_an_extra_device(self):
        joined = [self.pool.join(f"phone-{number}") for number in range(4)]
        self.assertEqual([1, 2, 3, 4], [item["player"] for item in joined])
        self.assert_code("gamepad_full", self.pool.join, "phone-five")
        self.assertEqual(3, self.factory.call_count)
        self.assertEqual(4, self.pool.info()["activeGamepads"])

    def test_recycled_seat_has_new_lease_and_old_requests_cannot_write_or_leave_it(self):
        first, second = self.pool.join("first"), self.pool.join("second")
        self.pool.leave(first["session"], "first")
        replacement = self.pool.join("replacement")
        self.assertEqual(first["player"], replacement["player"])
        self.assertNotEqual(first["session"], replacement["session"])
        self.assertTrue(self.seed.closed)
        self.pool.apply(replacement["session"], 1, {"buttons": ["y"]})
        snapshot = list(self.created[-1].applied)
        self.assert_code("gamepad_session_expired", self.pool.apply, first["session"], 100, {"buttons": ["a"]})
        self.pool.leave(first["session"], "first")
        # Even an old leave carrying a current request ID cannot remove its
        # different, newly issued lease.
        self.pool.leave(first["session"], "replacement")
        self.assertEqual(snapshot, self.created[-1].applied)
        self.assertFalse(self.created[-1].closed)
        self.assertFalse(self.created[1].closed)
        self.assertEqual(2, self.pool.info()["activeGamepads"])
        self.assertEqual(second, self.pool.join("second"))

    def test_missing_session_and_invalid_sequence_never_apply(self):
        joined = self.pool.join("phone")
        self.assert_code("gamepad_session_required", self.pool.apply, None, 1, {})
        for seq in (None, True, False, 0, -1, 1.0, "1", [], {}, pad_control.MAX_SEQUENCE + 1):
            with self.subTest(seq=seq):
                self.assert_code("invalid_request", self.pool.apply, joined["session"], seq, {})
        self.assertEqual([], self.seed.applied)
        self.pool.apply(joined["session"], pad_control.MAX_SEQUENCE, {})
        self.assertEqual(1, len(self.seed.applied))

    def test_old_sequence_is_ignored_and_does_not_renew_the_lease(self):
        joined = self.pool.join("phone")
        self.pool.apply(joined["session"], 2, {"buttons": ["a"]})
        self.clock.advance(14)
        for seq in (1, 2):
            result = self.pool.apply(joined["session"], seq, {"buttons": ["b"]})
            self.assertTrue(result["ignored"])
            self.assertTrue(result["stale"])
        self.assertEqual(1, len(self.seed.applied))
        self.clock.advance(1)
        self.assert_code("gamepad_session_expired", self.pool.apply, joined["session"], 3, {})
        self.assertTrue(self.seed.closed)

    def test_join_retries_also_do_not_renew_an_abandoned_lease(self):
        joined = self.pool.join("phone")
        self.clock.advance(14)
        self.assertEqual(joined, self.pool.join("phone"))
        self.clock.advance(1)
        self.assert_code("gamepad_session_expired", self.pool.join, "phone")
        self.assertEqual(0, self.pool.info()["activeGamepads"])

    def test_new_neutral_heartbeat_renews_lease_and_expiry_releases_only_its_owner(self):
        first, second = self.pool.join("one"), self.pool.join("two")
        self.clock.advance(14)
        self.pool.apply(first["session"], 1, {})
        self.clock.advance(1)
        self.assertEqual(1, self.pool.expire())
        self.assertFalse(self.seed.closed)
        self.assertTrue(self.created[1].closed)
        self.assertEqual(1, self.pool.info()["activeGamepads"])
        self.clock.advance(14)
        self.assert_code("gamepad_session_expired", self.pool.apply, first["session"], 2, {})
        self.assert_code("gamepad_session_expired", self.pool.apply, second["session"], 1, {})

    def test_cancel_before_join_prevents_late_allocation(self):
        self.pool.leave(request_id="cancelled")
        self.assert_code("gamepad_session_expired", self.pool.join, "cancelled")
        self.assertEqual(0, self.factory.call_count)
        self.assertEqual([], self.seed.applied)
        self.assertFalse(self.seed.closed)

    def test_cancel_by_request_id_retires_a_join_whose_response_was_lost(self):
        joined = self.pool.join("lost-response")
        self.pool.leave(request_id="lost-response")
        self.assertTrue(self.seed.closed)
        self.assert_code("gamepad_session_expired", self.pool.join, "lost-response")
        self.assert_code("gamepad_session_expired", self.pool.apply, joined["session"], 1, {})
        self.assertEqual(0, self.pool.info()["activeGamepads"])

    def test_cancel_while_a_device_is_being_created_cannot_leave_a_live_late_join(self):
        self.pool.join("first")
        entered, release = threading.Event(), threading.Event()
        result, errors = [], []
        created = FakePad()
        def slow_factory():
            entered.set()
            release.wait(timeout=2)
            return created
        self.factory.side_effect = slow_factory
        def join():
            try:
                result.append(self.pool.join("cancel-during-create"))
            except Exception as error:
                errors.append(error)
        joining = threading.Thread(target=join)
        cancelling = threading.Thread(target=self.pool.leave, kwargs={"request_id": "cancel-during-create"})
        joining.start()
        try:
            self.assertTrue(entered.wait(timeout=2))
            cancelling.start()
        finally:
            release.set()
            joining.join(timeout=2)
            if cancelling.ident is not None:
                cancelling.join(timeout=2)
        self.assertFalse(joining.is_alive())
        self.assertFalse(cancelling.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(1, len(result))
        self.assertTrue(created.closed)
        self.assertEqual(1, self.pool.info()["activeGamepads"])
        self.assert_code("gamepad_session_expired", self.pool.join, "cancel-during-create")
        self.assert_code("gamepad_session_expired", self.pool.apply, result[0]["session"], 1, {})

    def test_pool_watchdog_expires_lease_without_a_status_or_input_request(self):
        self.pool.join("phone")
        self.seed.close = Mock(wraps=self.seed.close)
        self.clock.advance(15)
        self.pool._watchdog.join(timeout=.6)
        self.assertEqual(1, self.seed.close.call_count)
        self.assertTrue(self.seed.closed)
        self.assertEqual(0, len(self.pool._sessions))

    def test_tombstones_are_bounded_and_expire(self):
        for number in range(300):
            self.pool.leave(request_id=f"cancel-{number}")
        self.assertEqual(pad_control.MAX_TOMBSTONES, len(self.pool._tombstones))
        self.assert_code("gamepad_session_expired", self.pool.join, "cancel-299")
        self.clock.advance(60)
        self.assertEqual(1, self.pool.join("cancel-299")["player"])
        self.assertEqual(0, len(self.pool._tombstones))

    def test_leave_is_idempotent_and_does_not_affect_other_phones(self):
        first, second = self.pool.join("one"), self.pool.join("two")
        self.pool.leave(first["session"], "one")
        self.pool.leave(first["session"], "one")
        self.pool.leave("unknown")
        self.pool.leave()
        self.assertEqual(1, self.pool.info()["activeGamepads"])
        self.assertFalse(self.created[1].closed)
        self.assertEqual(second, self.pool.join("two"))

    def test_invalid_ids_and_mismatched_leave_do_not_release_devices(self):
        for request_id in (None, [], {}, 1, True, "", "x" * 129):
            self.assert_code("invalid_request", self.pool.join, request_id)
        joined = self.pool.join("phone")
        self.assert_code("invalid_request", self.pool.leave, joined["session"], "wrong-owner")
        self.assert_code("invalid_request", self.pool.leave, [], None)
        self.assertFalse(self.seed.closed)

    def test_new_device_failure_does_not_touch_existing_phone_or_report_keyboard_fallback(self):
        self.pool.join("working")
        self.factory.side_effect = RuntimeError("mock no XInput slot")
        self.assert_code("gamepad_unavailable", self.pool.join, "unavailable")
        self.assertFalse(self.seed.closed)
        self.assertEqual([], self.seed.applied)
        self.assertTrue(self.pool.info()["nativeGamepad"])
        self.assertEqual("vigem", self.pool.info()["padBackend"])
        self.assertEqual(1, self.pool.info()["activeGamepads"])

    def test_capability_flag_preserves_native_mode_while_a_device_is_unavailable(self):
        seed = FakePad(available=False, error="没有可用的 XInput 手柄席位")
        seed.native_capable = True
        pool = pad_control.PadPool(seed=seed, factory=FakePad, clock=self.clock)
        try:
            self.assertTrue(pool.info()["nativeGamepad"])
            self.assertEqual("vigem", pool.info()["padBackend"])
            self.assert_code("gamepad_unavailable", pool.join, "phone")
            self.assertEqual(0, pool.info()["activeGamepads"])
            # A later attempt can succeed after an external controller leaves.
            self.assertEqual(1, pool.join("retry")["player"])
        finally:
            pool.close()

    def test_four_distinct_targets_may_report_zero_without_being_rejected_or_given_fake_indices(self):
        self.seed.reported_xinput_index = 0
        def factory():
            pad = FakePad()
            pad.reported_xinput_index = 0
            self.created.append(pad)
            return pad
        self.factory.side_effect = factory
        joined = [self.pool.join(f"phone-{number}") for number in range(4)]
        self.assertEqual([1, 2, 3, 4], [entry["player"] for entry in joined])
        self.assertTrue(all("xinputIndex" not in entry for entry in joined))
        self.assertTrue(all(pad.reported_xinput_index == 0 for pad in self.created))
        self.assertEqual(4, len({id(pad) for pad in self.created}))
        for entry, button in zip(joined, ("a", "b", "x", "y")):
            self.pool.apply(entry["session"], 1, {"buttons": [button]})
        self.assertEqual([("a",), ("b",), ("x",), ("y",)], [pad.applied[-1]["buttons"] for pad in self.created])
        self.assert_code("gamepad_full", self.pool.join, "fifth")
        self.assertTrue(all(not pad.closed for pad in self.created))

    def test_factory_initialization_failure_keeps_mouse_receiver_usable(self):
        pool = pad_control.PadPool(factory=Mock(side_effect=RuntimeError("mock no driver")))
        try:
            self.assertFalse(pool.info()["nativeGamepad"])
            self.assert_code("gamepad_unavailable", pool.join, "phone")
        finally:
            pool.close()

    def test_factory_cannot_accidentally_give_two_sessions_the_same_device(self):
        self.pool.join("one")
        self.factory.side_effect = None
        self.factory.return_value = self.seed
        self.assert_code("gamepad_unavailable", self.pool.join, "two")
        self.assertFalse(self.seed.closed)
        self.assertEqual(1, self.pool.info()["activeGamepads"])

    def test_native_write_failure_retires_its_lease_but_preserves_other_phones(self):
        first, second = self.pool.join("one"), self.pool.join("two")
        self.seed.apply = Mock(side_effect=AssertionError("mock driver failure"))
        self.assert_code("gamepad_unavailable", self.pool.apply, first["session"], 1, {"buttons": ["a"]})
        self.assertTrue(self.seed.closed)
        self.assert_code("gamepad_session_expired", self.pool.apply, first["session"], 2, {})
        self.pool.apply(second["session"], 1, {"buttons": ["b"]})
        self.assertEqual(("b",), self.created[1].applied[-1]["buttons"])

    def test_close_retires_every_device_even_when_one_close_fails(self):
        joined = [self.pool.join(f"phone-{number}") for number in range(4)]
        self.seed.close = Mock(side_effect=OSError("mock removal failure"))
        self.pool.close()
        self.pool.close()
        self.assertEqual(0, self.pool.info()["activeGamepads"])
        self.assertEqual(1, self.seed.close.call_count)
        self.assertTrue(all(pad.closed for pad in self.created[1:]))
        for session in joined:
            self.assert_code("gamepad_session_expired", self.pool.apply, session["session"], 1, {})

    def test_close_unused_probe_removes_it_without_allocating_other_targets(self):
        self.pool.close()
        self.assertTrue(self.seed.closed)
        self.assertEqual(0, self.factory.call_count)


class SessionEndpointTests(unittest.TestCase):
    def setUp(self):
        self.pads = []

        def factory():
            pad = FakePad()
            self.pads.append(pad)
            return pad

        self.factory = Mock(side_effect=factory)
        self.controller = FakeController()
        self.server = receiver.create_server(host="127.0.0.1", port=0, token="test-token",
                                            controller=self.controller, pad_factory=self.factory)
        self.worker = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": .01}, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=2)

    def request(self, path, payload=None, token="test-token", origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-WatchMouse-Token"] = token
        if origin:
            headers["Origin"] = origin
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=2)
        try:
            connection.request("GET" if payload is None else "POST", path,
                               json.dumps(payload) if payload is not None else None, headers)
            response = connection.getresponse()
            return response.status, json.loads(response.read())
        finally:
            connection.close()

    def join(self, request_id):
        status, payload = self.request("/api/pad/join", {"requestId": request_id})
        self.assertEqual(200, status, payload)
        self.assertTrue(payload["ok"])
        return payload

    def state(self, joined, seq=1, pad=None):
        return self.request("/api/pad", {"session": joined["session"], "seq": seq, "pad": pad or {}})

    def test_two_phones_use_independent_native_pads(self):
        first, second = self.join("phone-one"), self.join("phone-two")
        self.assertEqual(200, self.state(first, pad={"buttons": ["a"]})[0])
        self.assertEqual(200, self.state(second, pad={"lx": -.8, "buttons": ["y"]})[0])
        self.assertEqual(("a",), self.pads[0].applied[-1]["buttons"])
        self.assertEqual(("y",), self.pads[1].applied[-1]["buttons"])
        self.assertEqual(-.8, self.pads[1].applied[-1]["lx"])
        self.assertEqual([], self.controller.calls)
        _, status = self.request("/api/status")
        self.assertEqual(2, status["activeGamepads"])
        self.assertEqual(4, status["maxGamepads"])
        self.assertEqual(2, status["commandCount"])
        self.assertIn("gamepad.multiplayer", status["features"])
        self.assertNotIn("session", status)
        self.assertNotIn(first["session"], json.dumps(status))

    def test_four_limit_and_idempotent_join(self):
        joined = [self.join(f"phone-{number}") for number in range(4)]
        self.assertEqual(joined[0], self.join("phone-0"))
        status, body = self.request("/api/pad/join", {"requestId": "fifth"})
        self.assertEqual((409, "gamepad_full"), (status, body["errorCode"]))
        self.assertEqual(4, self.factory.call_count)
        self.assertEqual([], self.controller.calls)

    def test_old_state_is_acknowledged_but_never_applied_or_counted(self):
        joined = self.join("phone")
        self.assertEqual(200, self.state(joined, 2, {"buttons": ["a"]})[0])
        status, payload = self.state(joined, 1, {"buttons": ["b"]})
        self.assertEqual(200, status)
        self.assertTrue(payload["ignored"])
        self.assertTrue(payload["stale"])
        self.assertEqual(1, len(self.pads[0].applied))
        self.assertEqual(1, self.server.command_count)

    def test_leave_before_delayed_join_blocks_allocation(self):
        self.assertEqual(200, self.request("/api/pad/leave", {"requestId": "cancelled"})[0])
        status, body = self.request("/api/pad/join", {"requestId": "cancelled"})
        self.assertEqual((409, "gamepad_session_expired"), (status, body["errorCode"]))
        self.assertEqual(1, self.factory.call_count)  # only the startup probe
        self.assertFalse(self.pads[0].closed)

    def test_lease_reuse_protects_new_phone_from_late_state_and_release(self):
        old = self.join("old")
        self.assertEqual(200, self.request("/api/pad/leave", {"session": old["session"], "requestId": "old"})[0])
        new = self.join("new")
        self.assertEqual(old["player"], new["player"])
        self.assertNotEqual(old["session"], new["session"])
        status, body = self.state(old, 50, {"buttons": ["a"]})
        self.assertEqual((409, "gamepad_session_expired"), (status, body["errorCode"]))
        self.assertEqual(200, self.request("/api/pad/leave", {"session": old["session"], "requestId": "old"})[0])
        self.assertEqual([], self.pads[1].applied)
        self.assertFalse(self.pads[1].closed)
        self.assertEqual(200, self.state(new, 1, {"buttons": ["b"]})[0])

    def test_all_session_endpoints_require_pairing_and_same_origin(self):
        for path, payload in (("/api/pad/join", {"requestId": "phone"}),
                              ("/api/pad/leave", {"requestId": "phone"}),
                              ("/api/pad", {"session": "unknown", "seq": 1, "pad": {}})):
            self.assertEqual(401, self.request(path, payload, token="wrong")[0])
            self.assertEqual(403, self.request(path, payload, origin="http://other.example")[0])
        self.assertEqual(0, self.server.pad_pool.info()["activeGamepads"])
        self.assertEqual([], self.pads[0].applied)

    def test_input_release_failure_cannot_skip_closing_native_pads(self):
        self.join("one")
        self.join("two")
        self.server.shutdown()
        self.controller.release_all = Mock(side_effect=OSError("mock keyboard release failure"))
        with self.assertRaises(OSError):
            self.server.server_close()
        self.assertTrue(all(pad.closed for pad in self.pads))
        self.assertEqual(-1, self.server.socket.fileno())
        self.controller.release_all = Mock()


class ServerConstructionTests(unittest.TestCase):
    def test_bind_failure_closes_the_probe_and_stops_pool_watchdog(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        seed, pools = FakePad(), []
        pool_class = pad_control.PadPool
        def capture_pool(*args, **kwargs):
            pool = pool_class(*args, **kwargs)
            pools.append(pool)
            return pool
        try:
            with patch.object(pad_control, "PadPool", side_effect=capture_pool):
                with self.assertRaises(OSError):
                    receiver.create_server(host="127.0.0.1", port=listener.getsockname()[1], token="test-token",
                                           controller=FakeController(), pad=seed)
            self.assertTrue(seed.closed)
            self.assertTrue(pools[0]._stop.is_set())
            pools[0]._watchdog.join(timeout=2)
            self.assertFalse(pools[0]._watchdog.is_alive())
        finally:
            listener.close()

    def test_early_socket_creation_failure_also_closes_the_probe(self):
        seed = FakePad()
        with patch.object(receiver.ThreadingHTTPServer, "__init__", side_effect=OSError("mock socket creation failure")):
            with self.assertRaises(OSError):
                receiver.create_server(host="127.0.0.1", port=0, token="test-token", controller=FakeController(), pad=seed)
        self.assertTrue(seed.closed)


if __name__ == "__main__":
    unittest.main()
