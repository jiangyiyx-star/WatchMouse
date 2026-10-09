"""Quartz adapter for the shared WatchMouse command protocol."""
from input_control import InputController as BaseController

# macOS virtual keycodes (ANSI positions; Unicode text is layout independent).
KEYS = {
    'a':0,'s':1,'d':2,'f':3,'h':4,'g':5,'z':6,'x':7,'c':8,'v':9,'b':11,
    'q':12,'w':13,'e':14,'r':15,'y':16,'t':17,'1':18,'2':19,'3':20,'4':21,
    '6':22,'5':23,'9':25,'7':26,'8':28,'0':29,'o':31,'u':32,'i':34,'p':35,
    'l':37,'j':38,'k':40,'n':45,'m':46,'enter':36,'tab':48,'space':49,
    'backspace':51,'escape':53,'esc':53,'home':115,'pageup':116,'delete':117,
    'end':119,'pagedown':121,'left':123,'right':124,'down':125,'up':126,
    'insert':114,'f1':122,'f2':120,'f3':99,'f4':118,'f5':96,'f6':97,'f7':98,
    'f8':100,'f9':101,'f10':109,'f11':103,'f12':111}

class InputController(BaseController):
    def __init__(self, quartz=None):
        if quartz is None:
            import Quartz as quartz
        self.q = quartz
        super().__init__(sender=self._translate)

    def trusted(self):
        import ApplicationServices
        return bool(ApplicationServices.AXIsProcessTrusted())

    def _check(self):
        if not self.trusted():
            raise OSError('请在 Mac 系统设置 → 隐私与安全性 → 辅助功能中允许 WatchMouse')

    def _post(self, event):
        if event is None:
            raise OSError('macOS 无法创建输入事件')
        self.q.CGEventPost(self.q.kCGHIDEventTap, event)

    def _translate(self, items):
        """Reuse shared validation and drag watchdog, translating only mouse packets."""
        self._check()
        q = self.q
        for item in items:
            if item.type != 0:
                raise ValueError('Mac 键盘事件必须通过 Quartz 接口')
            flags = item.mi.dwFlags
            location = q.CGEventGetLocation(q.CGEventCreate(None))
            if flags == 1:
                location = (location.x + item.mi.dx, location.y + item.mi.dy)
                kind = q.kCGEventLeftMouseDragged if self.dragging else q.kCGEventMouseMoved
                event = q.CGEventCreateMouseEvent(None, kind, location, q.kCGMouseButtonLeft)
                q.CGEventSetIntegerValueField(event, q.kCGMouseEventDeltaX, item.mi.dx)
                q.CGEventSetIntegerValueField(event, q.kCGMouseEventDeltaY, item.mi.dy)
            elif flags == 0x800:
                data = item.mi.mouseData & 0xffffffff
                if data >= 0x80000000:
                    data -= 0x100000000
                event = q.CGEventCreateScrollWheelEvent(None, q.kCGScrollEventUnitLine, 1, data // 120)
            else:
                kind, button = {2:(q.kCGEventLeftMouseDown,q.kCGMouseButtonLeft),
                                4:(q.kCGEventLeftMouseUp,q.kCGMouseButtonLeft),
                                8:(q.kCGEventRightMouseDown,q.kCGMouseButtonRight),
                                16:(q.kCGEventRightMouseUp,q.kCGMouseButtonRight)}[flags]
                event = q.CGEventCreateMouseEvent(None, kind, location, button)
            self._post(event)

    def press_key(self, name, modifiers):
        # Validate before checking permission or creating any events.
        if not isinstance(name, str) or name.lower() not in KEYS:
            raise ValueError('不支持的按键')
        if not isinstance(modifiers, list) or len(modifiers) > 4 or any(
                not isinstance(mod, str) or mod not in ('ctrl','shift','alt','win','cmd','control') for mod in modifiers):
            raise ValueError('无效组合键')
        self._check()
        q = self.q
        # Existing phone Ctrl shortcuts mean Command on Mac; control is literal Ctrl.
        masks = {'ctrl':q.kCGEventFlagMaskCommand,'cmd':q.kCGEventFlagMaskCommand,
                 'win':q.kCGEventFlagMaskCommand,'shift':q.kCGEventFlagMaskShift,
                 'alt':q.kCGEventFlagMaskAlternate,'control':q.kCGEventFlagMaskControl}
        flags = 0
        for mod in set(modifiers):
            flags |= masks[mod]
        for down in (True, False):
            event = q.CGEventCreateKeyboardEvent(None, KEYS[name.lower()], down)
            q.CGEventSetFlags(event, flags)
            self._post(event)

    def type_text(self, text):
        if not isinstance(text, str) or not text or len(text) > 4000 or '\x00' in text:
            raise ValueError('请输入 1–4000 字的有效文字')
        text.encode('utf-16-le', errors='strict')
        self._check()
        q = self.q
        for character in text.replace('\r\n','\n').replace('\r','\n'):
            if character in ('\n','\t'):
                self.press_key('enter' if character == '\n' else 'tab', [])
                continue
            length = len(character.encode('utf-16-le')) // 2
            for down in (True, False):
                event = q.CGEventCreateKeyboardEvent(None, 0, down)
                q.CGEventSetFlags(event, 0)
                q.CGEventKeyboardSetUnicodeString(event, length, character)
                self._post(event)
