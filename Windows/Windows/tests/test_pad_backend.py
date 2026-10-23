import time
import unittest

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


if __name__ == "__main__":
    unittest.main()