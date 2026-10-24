import time
import unittest
import weakref
import sys
import types
from unittest.mock import Mock, patch

import pad_control


class FakeGamepad:
    def __init__(self):
        self.calls = []

    def reset(self):
        self.calls.append(("reset",))

    def update(self):
        self.calls.append(("update",))

    def press_button(self, button):
        self.calls.append(("press", button))

    def left_joystick_float(self, x_value_float, y_value_float):
        self.calls.append(("left", round(x_value_float, 3), round(y_value_float, 3)))

    def right_joystick_float(self, x_value_float, y_value_float):
        self.calls.append(("right", round(x_value_float, 3), round(y_value_float, 3)))

    def left_trigger_float(self, value_float):
        self.calls.append(("lt", round(value_float, 3)))

    def right_trigger_float(self, value_float):
        self.calls.append(("rt", round(value_float, 3)))


class FakeEngine:
    class XUSB_BUTTON:
        XUSB_GAMEPAD_A = "A"
        XUSB_GAMEPAD_B = "B"
        XUSB_GAMEPAD_X = "X"
        XUSB_GAMEPAD_Y = "Y"
        XUSB_GAMEPAD_LEFT_SHOULDER = "LB"
        XUSB_GAMEPAD_RIGHT_SHOULDER = "RB"
        XUSB_GAMEPAD_BACK = "BACK"
        XUSB_GAMEPAD_START = "START"
        XUSB_GAMEPAD_LEFT_THUMB = "LS"
        XUSB_GAMEPAD_RIGHT_THUMB = "RS"
        XUSB_GAMEPAD_DPAD_UP = "UP"
        XUSB_GAMEPAD_DPAD_DOWN = "DOWN"
        XUSB_GAMEPAD_DPAD_LEFT = "LEFT"
        XUSB_GAMEPAD_DPAD_RIGHT = "RIGHT"


class VirtualPadTests(unittest.TestCase):
    def setUp(self):
        self.gamepad = FakeGamepad()

        def opener():
            return (FakeEngine, self.gamepad), ""

        self.pad = pad_control.VirtualPad(opener=opener)

    def tearDown(self):
        self.pad.close()

    def test_write_maps_a_snapshot_onto_the_virtual_pad(self):
        self.assertTrue(self.pad.available)
        self.pad.apply(pad_control.normalize({"lx": 0.5, "ly": -0.25, "rx": -1, "lt": 1, "buttons": ["a", "rb"]}))
        press = [call for call in self.gamepad.calls if call[0] == "press"]
        self.assertEqual(sorted(call[1] for call in press), ["A", "RB"])
        self.assertIn(("left", 0.5, 0.25), self.gamepad.calls)  # screen y is inverted
        self.assertIn(("right", -1.0, 0.0), self.gamepad.calls)
        self.assertIn(("lt", 1.0), self.gamepad.calls)
        self.assertEqual(self.gamepad.calls[-1], ("update",))

    def test_identical_snapshots_do_not_resend(self):
        state = pad_control.normalize({"buttons": ["a"]})
        self.pad.apply(state)
        updates = len([call for call in self.gamepad.calls if call[0] == "update"])
        self.pad.apply(state)
        self.assertEqual(len([call for call in self.gamepad.calls if call[0] == "update"]), updates)

    def test_reset_returns_the_pad_to_neutral(self):
        self.pad.apply(pad_control.normalize({"buttons": ["a"], "rt": 1}))
        self.gamepad.calls.clear()
        self.pad.reset()
        self.assertNotIn("press", [call[0] for call in self.gamepad.calls])
        self.assertIn(("rt", 0.0), self.gamepad.calls)
        self.assertEqual(self.gamepad.calls[-1], ("update",))

    def test_watchdog_releases_a_pad_that_stops_reporting(self):
        original = pad_control.IDLE_RESET_SECONDS
        pad_control.IDLE_RESET_SECONDS = 0.05
        try:
            self.pad.apply(pad_control.normalize({"buttons": ["a"]}))
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                snapshot = pad_control.normalize({"buttons": ["a"]})
                if self.pad._state == pad_control.neutral() and self.gamepad.calls[-1] == ("update",):
                    break
                time.sleep(0.02)
            self.assertEqual(self.pad._state, pad_control.neutral())
            self.assertIn(("rt", 0.0), self.gamepad.calls)
            del snapshot
        finally:
            pad_control.IDLE_RESET_SECONDS = original

    def test_unavailable_backend_reports_the_reason(self):
        pad = pad_control.VirtualPad(opener=lambda: (None, "需要先安装 ViGEmBus 驱动"))
        self.assertFalse(pad.available)
        self.assertEqual(pad.error, "需要先安装 ViGEmBus 驱动")
        with self.assertRaises(OSError):
            pad.apply(pad_control.neutral())
        pad.close()

    def test_apply_failure_disables_and_releases_the_native_target(self):
        self.gamepad.update = Mock(side_effect=AssertionError("mock write failure"))
        with self.assertRaisesRegex(OSError, "写入失败") as caught:
            self.pad.apply(pad_control.normalize({"buttons": ["a"]}))
        self.assertIsNone(caught.exception.__context__)
        self.assertFalse(self.pad.available)
        self.assertIsNone(self.pad.engine)
        self.assertEqual(pad_control.neutral(), self.pad._state)
        self.assertEqual(0, self.pad.last_update)

    def test_watchdog_failure_disables_target_instead_of_losing_the_deadman(self):
        self.pad.apply(pad_control.normalize({"buttons": ["a"]}))
        self.gamepad.update = Mock(side_effect=OSError("mock disconnected bus"))
        self.pad.last_update = time.monotonic() - pad_control.IDLE_RESET_SECONDS - 1
        self.pad._watchdog.join(timeout=2)
        self.assertFalse(self.pad._watchdog.is_alive())
        self.assertFalse(self.pad.available)
        self.assertIn("重置失败", self.pad.error)
        self.assertEqual(pad_control.neutral(), self.pad._state)

    def test_close_clears_native_references_even_when_reset_unexpectedly_raises(self):
        with patch.object(self.pad, "reset", side_effect=RuntimeError("mock reset failure")):
            with self.assertRaises(RuntimeError):
                self.pad.close()
        self.assertTrue(self.pad._stop.is_set())
        self.assertIsNone(self.pad.pad)
        self.assertIsNone(self.pad.engine)
        self.assertEqual(pad_control.neutral(), self.pad._state)

    def test_retained_protocol_error_does_not_retain_a_native_device(self):
        # Each instance is created inside the opener, with no test-owned strong
        # reference. Keep the returned error to exercise traceback retention.
        references = []
        def opener():
            gamepad = FakeGamepad()
            references.append(weakref.ref(gamepad))
            return (FakeEngine, gamepad), ""
        seed = pad_control.VirtualPad(opener=opener)
        pool = pad_control.PadPool(seed=seed)
        try:
            joined = pool.join("phone")
            references[0]().update = Mock(side_effect=OSError("mock write failure"))
            with self.assertRaises(pad_control.PadSessionError) as caught:
                pool.apply(joined["session"], 1, {"buttons": ["a"]})
            self.assertEqual("gamepad_unavailable", caught.exception.code)
            self.assertIsNone(caught.exception.__context__)
            self.assertIsNone(references[0]())
        finally:
            pool.close()

    def test_vigem_reported_index_is_only_a_hint_and_never_uses_internal_target_index(self):
        native = FakeGamepad()
        native._busp, native._devicep = 123, 456
        native.get_index = Mock(side_effect=AssertionError("Do not use internal index"))
        def query(bus, device, output):
            self.assertEqual((123, 456), (bus, device))
            output._obj.value = 2
            return 0x20000000
        client = types.ModuleType("vgamepad.win.vigem_client")
        client.vigem_target_x360_get_user_index = Mock(side_effect=query)
        win = types.ModuleType("vgamepad.win")
        win.vigem_client = client
        with patch.dict(sys.modules, {"vgamepad.win": win, "vgamepad.win.vigem_client": client}):
            pad = pad_control.VirtualPad(opener=lambda: ((FakeEngine, native), ""))
        try:
            self.assertTrue(pad.available)
            self.assertEqual(2, pad.reported_xinput_index)
            self.assertIsNone(pad.xinput_index)
            native.get_index.assert_not_called()
        finally:
            pad.close()

    def test_xinput_query_uses_export_when_python_binding_is_missing(self):
        native = types.SimpleNamespace(_busp=123, _devicep=456)
        def query(_bus, _device, output):
            output._obj.value = 1
            return 0x20000000
        export = Mock(side_effect=query)
        client = types.ModuleType("vgamepad.win.vigem_client")
        client.vigemClient = types.SimpleNamespace(vigem_target_x360_get_user_index=export)
        win = types.ModuleType("vgamepad.win")
        win.vigem_client = client
        with patch.dict(sys.modules, {"vgamepad.win": win, "vgamepad.win.vigem_client": client}):
            self.assertEqual(1, pad_control._xinput_user_index(native))
        self.assertEqual(3, len(export.argtypes))

    def test_unreliable_xinput_query_does_not_disable_an_attached_native_target(self):
        for code, index in ((0xE0000014, 0xFFFFFFFF), (0x20000000, 4)):
            native = FakeGamepad()
            native._busp, native._devicep = 123, 456
            def query(_bus, _device, output):
                output._obj.value = index
                return code
            client = types.ModuleType("vgamepad.win.vigem_client")
            client.vigem_target_x360_get_user_index = Mock(side_effect=query)
            win = types.ModuleType("vgamepad.win")
            win.vigem_client = client
            with patch.dict(sys.modules, {"vgamepad.win": win, "vgamepad.win.vigem_client": client}):
                pad = pad_control.VirtualPad(opener=lambda: ((FakeEngine, native), ""))
            try:
                self.assertTrue(pad.available)
                self.assertTrue(pad.native_capable)
                self.assertIs(native, pad.pad)
                self.assertIsNone(pad.xinput_index)
                self.assertIsNone(pad.reported_xinput_index)
                self.assertEqual("", pad.error)
                self.assertIn("XInput", pad.index_error)
                client.vigem_target_x360_get_user_index.assert_called_once()
            finally:
                pad.close()

    def test_four_virtual_pads_reporting_vigem_zero_still_get_distinct_leases(self):
        # Reproduce upstream issue #31 through the real VirtualPad + PadPool,
        # while native handles, driver calls and all input are fully mocked.
        natives = []
        def factory():
            native = FakeGamepad()
            native._busp, native._devicep = 123, 456 + len(natives)
            native.get_index = Mock(side_effect=AssertionError("Never synthesize an XInput index"))
            natives.append(native)
            return pad_control.VirtualPad(opener=lambda: ((FakeEngine, native), ""))
        def query(_bus, _device, output):
            output._obj.value = 0
            return 0x20000000
        client = types.ModuleType("vgamepad.win.vigem_client")
        client.vigem_target_x360_get_user_index = Mock(side_effect=query)
        win = types.ModuleType("vgamepad.win")
        win.vigem_client = client
        with patch.dict(sys.modules, {"vgamepad.win": win, "vgamepad.win.vigem_client": client}):
            pool = pad_control.PadPool(factory=factory)
            try:
                joined = [pool.join(f"phone-{index}") for index in range(4)]
                self.assertEqual([1, 2, 3, 4], [entry["player"] for entry in joined])
                self.assertEqual(4, len({entry["session"] for entry in joined}))
                self.assertEqual(4, len({id(native) for native in natives}))
                self.assertTrue(all("xinputIndex" not in entry for entry in joined))
                self.assertEqual(4, pool.info()["activeGamepads"])
                with self.assertRaises(pad_control.PadSessionError) as full:
                    pool.join("fifth")
                self.assertEqual("gamepad_full", full.exception.code)
                for native in natives:
                    native.get_index.assert_not_called()
            finally:
                pool.close()


if __name__ == "__main__":
    unittest.main()
