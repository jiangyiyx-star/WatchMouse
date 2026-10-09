// No browser dependencies: exercises the shipped script's event and API flow.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'remote.html'), 'utf8');
const source = fs.readFileSync(path.join(__dirname, '..', 'remote.js'), 'utf8');
const wait = () => new Promise(resolve => setTimeout(resolve, 30));

function createApp(savedMode = null) {
  let document;
  class Element {
    constructor() {
      this.listeners = {}; this.style = {setProperty(name, value) {this[name] = value;}}; this.dataset = {}; this.attributes = {};
      this.captured = new Set();
      this.hidden = false; this.value = ''; this.textContent = ''; this.disabled = false;
      this.selectionStart = 0; this.selectionEnd = 0;
      const classes = new Set();
      this.classList = {
        toggle(name, force = !classes.has(name)) {if (force) classes.add(name); else classes.delete(name);},
        add(name) {classes.add(name);}, remove(name) {classes.delete(name);}, contains(name) {return classes.has(name);}
      };
    }
    addEventListener(name, listener) {(this.listeners[name] ||= []).push(listener);}
    emit(name, event = {}) {
      const delivered = {...event, target: event.target || this, defaultPrevented: false, preventDefault() {this.defaultPrevented = true;}, stopPropagation() {this.propagationStopped = true;}};
      for (const listener of this.listeners[name] || []) listener(delivered);
      return delivered;
    }
    dispatchEvent(event) {this.emit(event.type, event); return true;}
    setAttribute(key, value) {this.attributes[key] = value;}
    getBoundingClientRect() {return {left: 0, top: 0};}
    setPointerCapture(id) {this.captured.add(id);}
    hasPointerCapture(id) {return this.captured.has(id);}
    releasePointerCapture(id) {this.captured.delete(id); this.emit('lostpointercapture', {pointerId: id});}
    focus() {document.activeElement = this;}
    blur() {if (document.activeElement === this) document.activeElement = null;}
    scrollIntoView() {}
    click() {this.emit('click');}
    setSelectionRange(start, end = start) {this.selectionStart = start; this.selectionEnd = end;}
    setRangeText(text, start, end) {
      this.value = this.value.slice(0, start) + text + this.value.slice(end);
      this.setSelectionRange(start + text.length);
    }
  }
  const elements = {};
  for (const match of html.matchAll(/<[^>]*\bid="([^"]+)"[^>]*>/g)) {
    elements[match[1]] = new Element();
    elements[match[1]].hidden = /\bhidden\b/.test(match[0]);
    for (const attribute of match[0].matchAll(/(aria-[\w-]+)="([^"]*)"/g)) elements[match[1]].setAttribute(attribute[1], attribute[2]);
    for (const className of (/class="([^"]*)"/.exec(match[0])?.[1] || '').split(' ')) elements[match[1]].classList.add(className);
    elements[match[1]].textContent = /^[^<]*/.exec(html.slice(match.index + match[0].length))[0];
  }
  function buttons(attribute) {
    const pattern = new RegExp('<button[^>]*\\b' + attribute + '="([^"]+)"([^>]*)>([^<]*)', 'g');
    return [...html.matchAll(pattern)].map(match => {
      const id = /\bid="([^"]+)"/.exec(match[0])?.[1];
      const button = id ? elements[id] : new Element();
      button.dataset[attribute.slice(5)] = match[1];
      button.dataset.modifiers = /data-modifiers="([^"]+)"/.exec(match[2])?.[1];
      button.textContent = match[3];
      return button;
    });
  }
  const commands = buttons('data-command');
  const keys = buttons('data-key');
  const modes = buttons('data-mode');
  document = new Element(); document.hidden = false; document.activeElement = null; document.body = new Element(); document.documentElement = new Element();
  document.getElementById = id => elements[id];
  document.querySelectorAll = selector => {
    if (selector === '[data-command]') return commands;
    if (selector === '[data-key]') return keys;
    if (selector === '[data-mode]') return modes;
    return [...new Set([...keys, ...commands, elements.deleteTextButton, elements.openPhoneKeyboard, elements.sendTextButton, elements.speechButton])];
  };
  const window = new Element(); window.isSecureContext = false; window.innerHeight = 640;
  window.visualViewport = new Element(); window.visualViewport.height = 640; window.visualViewport.offsetTop = 0;
  const records = [], stored = new Map(savedMode ? [['watchmouse_mode', savedMode]] : []);
  let active = 0, maxActive = 0, failure = null;
  const sandbox = {
    console, document, window, URL, Map, Promise, Math, Number, TypeError, Error, JSON, Array, Blob, Event, Intl,
    AbortController, setTimeout, clearTimeout, setInterval: () => 0, performance,
    location: {href: 'http://192.168.1.5:53514/?token=testtoken123456789', host: '192.168.1.5:53514'},
    localStorage: {getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value)},
    matchMedia: () => ({matches: false}), requestAnimationFrame: callback => callback(),
    navigator: {sendBeacon: () => true},
    fetch: async (url, options) => {
      if (url.startsWith('/api/status')) return {ok: true, json: async () => ({app: 'WatchMouse', paired: true})};
      active++; maxActive = Math.max(maxActive, active);
      records.push(JSON.parse(options.body));
      await new Promise(resolve => setTimeout(resolve, 2));
      active--;
      if (failure) {
        const {status, error} = failure; failure = null;
        return {ok: false, status, json: async () => ({ok: false, error})};
      }
      return {ok: true, json: async () => ({ok: true})};
    }
  };
  vm.runInNewContext(source, sandbox);
  function draft(text, start = text.length, end = start) {
    elements.textInput.value = text;
    elements.textInput.setSelectionRange(start, end);
    elements.textInput.emit('input');
  }
  return {elements, document, window, commands, keys, modes, records, stored, draft, maxActive: () => maxActive, failNext: (status, error) => {failure = {status, error};}};
}

(async () => {
  const app = createApp();
  const {elements, document, commands, records, stored, draft} = app;
  await wait();
  assert.equal(elements.connectionButton.attributes['aria-label'], '已连接，打开连接设置');
  assert.equal(elements.connectionButton.textContent, '', 'connection has only a dot');
  assert.equal(elements.actionFeedback.textContent, '', 'success does not announce or display text');
  assert(!elements.mousePanel.hidden && elements.douyinPanel.hidden && elements.keyboardPanel.hidden);
  assert.equal(document.activeElement, null);
  assert(elements.speechButton.hidden);
  assert(!/<header|<h[12]|<details/.test(html), 'no visible title or advanced panel');
  assert(!/TRACKPAD|PHONE INPUT|在这里滑动|更多电脑按键|当前位置|已发送/.test(html));
  assert(!/media-controls/.test(html), 'video controls only appear in Douyin mode');
  assert(!/touchpad-grid|cursor-symbol|mouse-footer/.test(html), 'one integrated undecorated mouse controller');
  assert(!/scrollIntoView/.test(source), 'keyboard must not programmatically scroll the page');
  assert.equal(app.keys.length, 5, 'only three video keys and Enter/space');
  assert(!/data-key="delete"/.test(html), 'common delete must not send forward Delete');

  elements.douyinModeButton.click();
  assert(elements.mousePanel.hidden && !elements.douyinPanel.hidden && elements.keyboardPanel.hidden);
  assert.equal(stored.get('watchmouse_mode'), 'douyin');
  assert.equal(elements.douyinModeButton.attributes['aria-pressed'], 'true');
  elements.keyboardModeButton.click();
  assert(!elements.mousePanel.hidden && elements.douyinPanel.hidden && !elements.keyboardPanel.hidden);
  assert.equal(document.activeElement, elements.textInput, 'trusted keyboard-mode click focuses native textarea');
  elements.mouseModeButton.click();
  assert(elements.keyboardPanel.hidden && !elements.mousePanel.hidden);
  assert.equal(document.activeElement, null);
  const restored = createApp('keyboard');
  assert(!restored.elements.keyboardPanel.hidden);
  assert.equal(restored.document.activeElement, null, 'restoring mode must not auto-open native keyboard');
  assert(createApp('invalid').elements.keyboardPanel.hidden);

  const pad = elements.touchpad;
  pad.emit('pointerdown', {pointerId: 1, pointerType: 'touch', clientX: 100, clientY: 100});
  for (let i = 1; i <= 50; i++) pad.emit('pointermove', {pointerId: 1, clientX: 100 + i * 4, clientY: 100});
  pad.emit('pointerup', {pointerId: 1});
  await wait();
  const distance = records.filter(item => item.command?.startsWith('M ')).reduce((sum, item) => sum + Number(item.command.slice(2).split(',')[0]), 0);
  assert(Math.abs(distance - 280) <= 1);
  const beforeScroll = records.length;
  pad.emit('pointerdown', {pointerId: 2, pointerType: 'touch', clientX: 100, clientY: 100});
  pad.emit('pointerdown', {pointerId: 3, pointerType: 'touch', clientX: 120, clientY: 100});
  pad.emit('pointermove', {pointerId: 2, clientX: 100, clientY: 148});
  pad.emit('pointermove', {pointerId: 3, clientX: 120, clientY: 148});
  pad.emit('pointerup', {pointerId: 2}); pad.emit('pointerup', {pointerId: 3});
  await wait();
  assert(records.slice(beforeScroll).some(item => item.command === 'S -2'));
  const surface = elements.scrollSurface;
  const railStart = records.length;
  surface.emit('pointerdown', {pointerId: 20, pointerType: 'touch', clientY: 100});
  surface.emit('pointerup', {pointerId: 20}); await wait();
  assert.equal(records.length, railStart, 'tapping the rail does not click PC');
  for (const id of [21, 22]) {
    surface.emit('pointerdown', {pointerId: id, pointerType: 'touch', clientY: 100});
    surface.emit('pointermove', {pointerId: id, clientY: 110});
    surface.emit('pointerup', {pointerId: id});
  }
  await wait();
  assert.equal(records.at(-1).command, 'S -1', 'fractional rail movement is preserved between successful swipes');
  assert(records.slice(railStart).every(item => item.command?.startsWith('S ')), 'rail never sends a click or cursor movement');
  const beforeCancel = records.length;
  surface.emit('pointerdown', {pointerId: 23, pointerType: 'touch', clientY: 100});
  surface.emit('pointermove', {pointerId: 23, clientY: 110});
  surface.emit('pointercancel', {pointerId: 23});
  surface.emit('pointermove', {pointerId: 23, clientY: 190});
  surface.emit('pointerup', {pointerId: 23}); await wait();
  assert.equal(records.length, beforeCancel, 'cancel discards rail remainder and ignores later events');
  assert(!surface.classList.contains('active'));
  surface.emit('pointerdown', {pointerId: 24, pointerType: 'touch', clientY: 100});
  surface.emit('pointermove', {pointerId: 24, clientY: 110});
  elements.douyinModeButton.click(); elements.mouseModeButton.click();
  surface.emit('pointerdown', {pointerId: 25, pointerType: 'touch', clientY: 100});
  surface.emit('pointermove', {pointerId: 25, clientY: 110});
  surface.emit('pointerup', {pointerId: 25}); await wait();
  assert.equal(records.length, beforeCancel, 'mode switch discards rail remainder');
  surface.emit('pointerdown', {pointerId: 26, pointerType: 'touch', clientY: 100});
  app.window.visualViewport.height = 240; app.window.visualViewport.offsetTop = 12;
  app.window.visualViewport.emit('resize');
  surface.emit('pointermove', {pointerId: 26, clientY: 180}); surface.emit('pointerup', {pointerId: 26}); await wait();
  assert.equal(records.length, beforeCancel, 'viewport change cancels rail gesture');
  assert.equal(document.documentElement.style['--viewport-height'], '240px');
  assert.equal(document.documentElement.style['--viewport-offset'], '12px');
  assert(document.body.classList.contains('compact-viewport'));
  assert(!surface.hasPointerCapture(26));
  app.window.visualViewport.height = 640; app.window.visualViewport.offsetTop = 0; app.window.visualViewport.emit('resize');
  commands.find(button => button.dataset.command === 'S 3').click(); await wait();
  assert.equal(records.at(-1).command, 'S 3', 'rail arrow endpoints stay clickable');
  elements.dragButton.click(); await wait();
  assert.equal(elements.dragButton.attributes['aria-pressed'], 'true');
  commands.find(button => button.dataset.command === 'C').click(); await wait();
  assert.equal(elements.dragButton.attributes['aria-pressed'], 'false');
  elements.dragButton.click(); await wait();
  elements.douyinModeButton.click(); await wait();
  assert.equal(elements.dragButton.attributes['aria-pressed'], 'false');
  assert(records.some(item => item.command === 'MU'), 'leaving a mode releases drag');

  elements.keyboardModeButton.click();
  assert(elements.sendTextButton.emit('pointerdown').defaultPrevented, 'send preserves native textarea focus');
  const beforeDraftDelete = records.length;
  draft('中文🙂'); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '中文');
  assert.equal(elements.textInput.selectionStart, 2);
  assert.equal(document.activeElement, elements.textInput);
  assert.equal(records.length, beforeDraftDelete, 'draft editing does not affect PC');
  assert.equal(elements.deleteTextButton.textContent, '⌫');
  assert(elements.deleteTextButton.attributes['aria-label'].includes('删除草稿'));
  assert.equal(elements.textFeedback.textContent, '');
  draft('甲👨‍👩‍👧‍👦'); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '甲', 'delete a complete emoji family');
  draft('甲e\u0301'); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '甲', 'delete combining marks with their base');
  draft('第一段第二段', 3, 6); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '第一段');
  draft('甲乙丙', 2); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '甲丙');
  assert.equal(elements.textInput.selectionStart, 1);
  draft('甲乙', 0); elements.deleteTextButton.click();
  assert.equal(elements.textInput.value, '甲乙');
  assert.equal(records.length, beforeDraftDelete);
  draft(''); elements.deleteTextButton.click(); await wait();
  assert.equal(records.at(-1).key, 'backspace');
  assert(elements.deleteTextButton.attributes['aria-label'].includes('电脑当前窗口按退格'));

  draft('中文语音🙂\n第二行');
  elements.textInput.emit('compositionstart');
  const beforeComposition = records.length;
  elements.deleteTextButton.click(); elements.sendTextButton.click(); await wait();
  assert.equal(records.length, beforeComposition);
  assert.equal(elements.textInput.value, '中文语音🙂\n第二行');
  elements.textInput.emit('compositionend'); elements.sendTextButton.click(); await wait();
  assert(records.some(item => item.text === '中文语音🙂\n第二行'));
  assert.equal(elements.textInput.value, '');
  assert.equal(elements.textFeedback.textContent, '');
  assert.equal(elements.actionFeedback.textContent, '');
  assert.equal(app.maxActive(), 1);
  assert(records.every(item => item.token === 'testtoken123456789'));
  elements.connectionButton.click();
  assert(!elements.connectionPanel.hidden);
  elements.connectionButton.click();
  assert(elements.connectionPanel.hidden);
  const failed = createApp(); await wait();
  failed.draft('保留这段草稿'); failed.failNext(409, 'Windows 未接受输入'); failed.elements.sendTextButton.click(); await wait();
  assert.equal(failed.elements.textInput.value, '保留这段草稿');
  assert.equal(failed.elements.textFeedback.textContent, '电脑未接收输入');
  assert(failed.elements.textFeedback.classList.contains('error'));
  assert(!failed.elements.textFeedback.classList.contains('visually-hidden'));
  console.log('PASS: integrated minimal UI/silent success, modes/native focus, viewport resize, mouse/drag, independent scroll rail/fractions/cancel/cleanup, draft deletion/backspace, IME/Unicode send, pairing, failed-send preservation, authenticated serialized requests.');
})().catch(error => {console.error(error); process.exitCode = 1;});
