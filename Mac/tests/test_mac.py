"""Exercise real Quartz event construction without posting desktop input."""
from pathlib import Path
import sys
import threading
import http.client
import json
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'Windows' / 'Windows'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import Quartz as Q
import receiver
from mac_input_control import InputController

class MacTests(unittest.TestCase):
    def setUp(self):
        self.events=[]
        self.post=patch.object(Q,'CGEventPost',side_effect=lambda tap,event:self.events.append(event))
        self.trust=patch('ApplicationServices.AXIsProcessTrusted',return_value=True)
        self.post.start(); self.trust.start()
        self.controller=InputController()
    def tearDown(self):
        self.controller.release_all()
        self.post.stop(); self.trust.stop()
    def test_unicode_and_control_characters(self):
        self.controller.execute({'text':'中文🙂\r\n\t'})
        self.assertEqual(10,len(self.events))
        for offset,text in ((0,'中'),(2,'文'),(4,'🙂')):
            for event in self.events[offset:offset+2]:
                self.assertEqual(text,Q.CGEventKeyboardGetUnicodeString(event,8,None,None)[1])
        self.assertEqual(36,Q.CGEventGetIntegerValueField(self.events[6],Q.kCGKeyboardEventKeycode))
        self.assertEqual(48,Q.CGEventGetIntegerValueField(self.events[8],Q.kCGKeyboardEventKeycode))
    def test_shortcuts_use_command_without_latching_modifiers(self):
        self.controller.execute({'key':'a','modifiers':['ctrl','shift','ctrl']})
        self.assertEqual([Q.kCGEventKeyDown,Q.kCGEventKeyUp],[Q.CGEventGetType(e) for e in self.events])
        self.assertEqual(Q.kCGEventFlagMaskCommand|Q.kCGEventFlagMaskShift,Q.CGEventGetFlags(self.events[0]))
    def test_drag_motion_release_and_watchdog(self):
        for command in ('MD','M 20,-10','MU','RC'):
            self.controller.execute({'command':command})
        self.assertEqual([Q.kCGEventLeftMouseDown,Q.kCGEventLeftMouseDragged,Q.kCGEventLeftMouseUp,
                          Q.kCGEventRightMouseDown,Q.kCGEventRightMouseUp],[Q.CGEventGetType(e) for e in self.events])
        self.controller.execute({'command':'MD'})
        self.controller.drag_timer.cancel()
        self.controller.last_activity=time.monotonic()-6
        self.controller._drag_expired()
        self.assertFalse(self.controller.dragging)
        self.assertEqual(Q.kCGEventLeftMouseUp,Q.CGEventGetType(self.events[-1]))
    def test_signed_scroll(self):
        self.controller.execute({'command':'S -2'})
        self.assertEqual(-2,Q.CGEventGetIntegerValueField(self.events[0],Q.kCGScrollWheelEventDeltaAxis1))
    def test_permission_denial_does_not_post_input(self):
        with patch('ApplicationServices.AXIsProcessTrusted',return_value=False):
            self.assertEqual('PONG',self.controller.execute({'command':'PING'}))
            for payload in ({'command':'C'},{'text':'中文'},{'key':'a'}):
                with self.assertRaises(OSError): self.controller.execute(payload)
        self.assertEqual([],self.events)
    def test_bad_requests_do_not_create_input(self):
        for payload in ({'command':'M 9999,0'},{'command':'S 101'},{'key':'bad'},
                        {'key':'a','modifiers':['bad']},{'text':'\ud800'},{'text':'\x00'},
                        {'text':'x','command':'C'}):
            with self.assertRaises((ValueError,TypeError)): self.controller.execute(payload)
        self.assertEqual([],self.events)
    def test_http_receiver_with_mac_controller(self):
        server=receiver.create_server(host='127.0.0.1',port=0,token='test',controller=self.controller)
        thread=threading.Thread(target=server.serve_forever,kwargs={'poll_interval':0.01},daemon=True)
        thread.start()
        try:
            conn=http.client.HTTPConnection('127.0.0.1',server.server_port)
            conn.request('POST','/api/command',json.dumps({'text':'中文🙂'}),
                         {'Content-Type':'application/json','X-WatchMouse-Token':'test'})
            response=conn.getresponse()
            self.assertEqual(200,response.status)
            self.assertTrue(json.loads(response.read())['ok'])
            conn.close()
            self.assertEqual(6,len(self.events))
        finally:
            server.shutdown(); server.server_close(); thread.join()
    def test_mac_settings_and_network(self):
        self.assertIn('Library/Application Support',str(receiver.settings_path()))
        output=b'en0: flags\n\tinet 192.168.1.20 netmask 0xffffff00\nutun0: flags\n\tinet 10.9.0.2 netmask 0xffffffff\n'
        with patch.object(receiver.subprocess,'check_output',return_value=output):
            self.assertEqual(['192.168.1.20'],receiver.lan_addresses())

if __name__=='__main__': unittest.main()
