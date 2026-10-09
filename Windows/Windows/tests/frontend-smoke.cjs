// No browser dependencies: exercises the shipped script's event and API flow.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'remote.html'), 'utf8');
const source = fs.readFileSync(path.join(__dirname, '..', 'remote.js'), 'utf8');
const wait = () => new Promise(resolve => setTimeout(resolve, 30));

function createApp(savedMode = null, inputStatus = {}, options = {}) {
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
    setAttribute(key, value) {
      this.attributes[key] = value;
      if (key.startsWith('data-')) this.dataset[key.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = value;
    }
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
  const elements = {}, allElements = [];
  for (const match of html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*)>/g)) {
    const element = new Element();
    allElements.push(element);
    const id = /\bid="([^"]+)"/.exec(match[2])?.[1];
    if (id) elements[id] = element;
    element.hidden = /\bhidden\b/.test(match[2]);
    for (const attribute of match[2].matchAll(/([\w-]+)="([^"]*)"/g)) element.setAttribute(attribute[1], attribute[2]);
    for (const className of (element.attributes.class || '').split(' ')) element.classList.add(className);
    element.textContent = /^[^<]*/.exec(html.slice(match.index + match[0].length))[0];
  }
  const commands = allElements.filter(element => element.dataset.command);
  const keys = allElements.filter(element => element.dataset.key);
  const modes = allElements.filter(element => element.dataset.mode);
  document = new Element(); document.hidden = false; document.activeElement = null; document.body = new Element(); document.documentElement = new Element();
  document.getElementById = id => elements[id];
  document.querySelectorAll = selector => {
    if (/^\[data-[\w-]+\]$/.test(selector)) return allElements.filter(element => Object.prototype.hasOwnProperty.call(element.attributes, selector.slice(1, -1)));
    return [...new Set([...keys, ...commands, elements.deleteTextButton, elements.openPhoneKeyboard, elements.sendTextButton, elements.speechButton])];
  };
  const window = new Element(); window.isSecureContext = false; window.innerHeight = 640;
  window.visualViewport = new Element(); window.visualViewport.height = 640; window.visualViewport.offsetTop = 0;
  if (options.secureSpeech) {
    window.isSecureContext = true;
    window.SpeechRecognition = class {
      constructor() { window.recognition = this; }
      start() { this.onstart(); }
      stop() { this.stopCalls = (this.stopCalls || 0) + 1; this.onend(); }
    };
  }
  const records = [], statusRequests = [], stored = options.stored || new Map(savedMode ? [['watchmouse_mode', savedMode]] : []);
  const timers = new Map();
  let nextTimerId = 1, statusActive = 0, maxStatusActive = 0, statusFailure = null;
  function scheduleTimeout(callback, delay) {
    if (delay <= 100) return setTimeout(callback, delay);
    const id = nextTimerId++; timers.set(id, {callback, delay}); return id;
  }
  function cancelTimeout(id) { if (!timers.delete(id)) clearTimeout(id); }
  function runStatusTimer() {
    const entry = [...timers.entries()].sort((a, b) => a[1].delay - b[1].delay)[0];
    if (!entry) return false;
    timers.delete(entry[0]); entry[1].callback(); return entry[1].delay;
  }

  const statusResult = {app: 'WatchMouse', paired: true, ...inputStatus};
  let active = 0, maxActive = 0, failure = null;
  const dragState = {held: false}, commandEffects = [];
  const browserLocation = {href: options.href || 'http://192.168.1.5:53514/?token=testtoken123456789', host: '192.168.1.5:53514'};
  const historyUpdates = [];
  if (!options.noHistory) window.history = {replaceState(_state, _title, href) { browserLocation.href = String(href); historyUpdates.push(browserLocation.href); }};
  const sandbox = {
    console, document, window, URL, Map, Promise, Math, Number, TypeError, Error, JSON, Array, Blob, Event, Intl,
    AbortController, setTimeout: scheduleTimeout, clearTimeout: cancelTimeout, setInterval: () => 0, performance,
    location: browserLocation,
    localStorage: {getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value)},
    matchMedia: () => ({matches: false}), requestAnimationFrame: callback => callback(),
    navigator: {onLine: true, sendBeacon: () => {
      if (options.simulateDragRace) { dragState.held = false; commandEffects.push('beacon MU'); }
      return true;
    }},
    fetch: async (url, requestOptions) => {
      if (url.startsWith('/api/status')) {
        statusActive++; maxStatusActive = Math.max(maxStatusActive, statusActive);
        statusRequests.push({url, token: requestOptions.headers?.['X-WatchMouse-Token']});
        if (options.statusDelay) await new Promise(resolve => setTimeout(resolve, options.statusDelay));
        statusActive--;
        if (statusFailure) throw new TypeError('network request failed');
        return {ok: true, json: async () => ({...statusResult})};
      }
      active++; maxActive = Math.max(maxActive, active);
      const packet = JSON.parse(requestOptions.body);
      records.push(packet);
      await new Promise(resolve => setTimeout(resolve, 2));
      active--;
      if (failure) {
        const {status, error, errorCode} = failure; failure = null;
        return {ok: false, status, json: async () => ({ok: false, error, errorCode})};
      }
      if (options.simulateDragRace && ['MD', 'MU'].includes(packet.command)) {
        dragState.held = packet.command === 'MD'; commandEffects.push(packet.command);
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
  return {elements, document, window, dragState, commandEffects, location: browserLocation, historyUpdates, commands, keys, modes, records, stored, draft, statusRequests, timers, runStatusTimer, maxStatusActive: () => maxStatusActive, maxActive: () => maxActive, failNext: (status, error, errorCode) => {failure = {status, error, errorCode};}, setStatusFailure: fail => {statusFailure = fail;}, setStatus: update => Object.assign(statusResult, update)};
}

(async () => {
  const app = createApp();
  const {elements, document, commands, records, stored, draft} = app;
  await wait();
  assert.equal(elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings');
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
  assert(elements.deleteTextButton.attributes['aria-label'].includes('in the draft'));
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
  assert(elements.deleteTextButton.attributes['aria-label'].includes('Backspace in the current computer window'));

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
  assert(app.runStatusTimer()); await wait();
  assert(!elements.connectionPanel.hidden, 'healthy polling leaves settings open while being edited');
  elements.connectionButton.click();
  assert(elements.connectionPanel.hidden);
  const permissionError = '请在 Mac 系统设置 → 隐私与安全性 → 辅助功能中允许 WatchMouse';
  const unavailable = createApp(null, {inputReady: false, inputError: permissionError}); await wait();
  assert.equal(unavailable.stored.get('watchmouse_token'), 'testtoken123456789', 'pairing token remains saved while input permission is denied');
  assert.equal(unavailable.elements.connectionButton.attributes['aria-label'], 'Disconnected; open connection settings');
  assert(!unavailable.elements.connectionPanel.hidden);
  assert.equal(unavailable.elements.connectionMessage.textContent, 'Allow WatchMouse in Mac System Settings → Privacy & Security → Accessibility.');
  assert.equal(unavailable.elements.actionFeedback.textContent, 'Allow WatchMouse in Mac System Settings → Privacy & Security → Accessibility.');
  unavailable.draft('授权后发送'); unavailable.elements.sendTextButton.click(); await wait();
  assert.equal(unavailable.records.length, 0, 'permission-denied status blocks input requests');
  assert.equal(unavailable.elements.textInput.value, '授权后发送');
  unavailable.setStatus({inputReady: true, inputError: ''}); assert(unavailable.runStatusTimer()); await wait();
  assert.equal(unavailable.elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings');
  unavailable.elements.sendTextButton.click(); await wait();
  assert.equal(unavailable.records.at(-1).text, '授权后发送');
  assert.equal(unavailable.elements.textInput.value, '', 'retained draft can be sent after permission is granted');
  const unspecifiedPermission = createApp(null, {inputReady: false}); await wait();
  assert.equal(unspecifiedPermission.elements.connectionMessage.textContent, 'Enable input permission on the computer.');

  for (const [backendError, expected] of [
    [permissionError, 'Allow WatchMouse in Mac System Settings → Privacy & Security → Accessibility.'],
    ['Windows 未接受输入。请确认目标窗口没有以管理员身份运行。', 'Windows did not accept input. Check whether the target app is running as administrator.'],
    ['', 'The computer did not accept input.'],
    ['x'.repeat(201), 'The computer did not accept input.']
  ]) {
    const failed = createApp(); await wait();
    failed.draft('保留这段草稿'); failed.failNext(409, backendError); failed.elements.sendTextButton.click(); await wait();
    assert.equal(failed.elements.textInput.value, '保留这段草稿');
    assert.equal(failed.elements.textFeedback.textContent, expected);
    assert.equal(failed.elements.connectionMessage.textContent, expected);
    assert.equal(failed.elements.actionFeedback.textContent, expected);
    assert(failed.elements.textFeedback.classList.contains('error'));
    assert(!failed.elements.textFeedback.classList.contains('visually-hidden'));
    assert(!failed.elements.sendTextButton.disabled);
  }
  assert.equal(document.documentElement.lang, 'en', 'new users start in English');
  assert.equal(elements.languageSelect.value, 'en');
  assert.equal(elements.keyboardModeButton.textContent, 'Keyboard');
  assert.equal(elements.textInput.attributes.placeholder, 'Type…');
  elements.languageSelect.value = 'zh'; elements.languageSelect.emit('change');
  assert.equal(stored.get('watchmouse_language'), 'zh');
  assert.equal(document.documentElement.lang, 'zh-CN');
  assert.equal(elements.keyboardModeButton.textContent, '键鼠');
  assert.equal(elements.textInput.attributes.placeholder, '输入…');
  assert.equal(elements.connectionButton.attributes['aria-label'], '已连接，打开连接设置');
  assert(elements.watchLink.href.includes('lang=zh-CN'));
  const reopened = createApp(null, {}, {stored, href: 'http://192.168.1.5:53514/'}); await wait();
  assert.equal(reopened.document.documentElement.lang, 'zh-CN', 'language persists after reopening');
  assert.equal(reopened.statusRequests[0].token, 'testtoken123456789', 'saved pairing works without QR token');
  assert.equal(reopened.elements.connectionButton.attributes['aria-label'], '已连接，打开连接设置');
  const correctedLink = createApp(null, {paired: false}, {
    href: 'http://192.168.1.5:53514/?token=old-pairing-key&view=mobile#controls'
  }); await wait();
  assert.equal(correctedLink.historyUpdates.length, 0, 'invalid pairing does not rewrite the URL');
  correctedLink.setStatus({paired: true, inputReady: false, inputErrorCode: 'accessibility_permission'});
  correctedLink.elements.pairingCode.value = 'new-pairing-key'; correctedLink.elements.pairButton.click(); await wait();
  assert.equal(correctedLink.stored.get('watchmouse_token'), 'new-pairing-key');
  const correctedUrl = new URL(correctedLink.location.href);
  assert.equal(correctedUrl.searchParams.get('token'), 'new-pairing-key', 'manual correction replaces stale QR key even before input permission');
  assert.equal(correctedUrl.searchParams.get('view'), 'mobile');
  assert.equal(correctedUrl.hash, '#controls');
  const correctedReload = createApp(null, {}, {stored: correctedLink.stored, href: correctedLink.location.href}); await wait();
  assert.equal(correctedReload.statusRequests[0].token, 'new-pairing-key', 'reload uses the corrected key from the updated URL');
  assert.equal(correctedReload.elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings');
  const historyUnavailable = createApp(null, {}, {noHistory: true}); await wait();
  assert.equal(historyUnavailable.elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings', 'unavailable History API does not interrupt pairing');
  assert.equal(historyUnavailable.stored.get('watchmouse_token'), 'testtoken123456789');
  const speechApp = createApp(null, {}, {secureSpeech: true}); await wait();
  assert.equal(speechApp.window.recognition.lang, 'zh-CN', 'existing dictation locale is independent of the English interface');
  speechApp.elements.speechButton.click();
  assert.equal(speechApp.elements.speechButton.attributes['aria-label'], 'Stop dictation');
  speechApp.elements.languageSelect.value = 'zh'; speechApp.elements.languageSelect.emit('change');
  assert.equal(speechApp.window.recognition.lang, 'zh-CN', 'interface selection does not reconfigure dictation');
  assert.equal(speechApp.window.recognition.stopCalls || 0, 0, 'interface selection does not stop active dictation');
  assert.equal(speechApp.elements.speechButton.textContent, '■', 'active recording remains active');
  assert.equal(speechApp.elements.speechButton.attributes['aria-label'], '停止语音', 'only dictation control labels change language');
  speechApp.elements.languageSelect.value = 'en'; speechApp.elements.languageSelect.emit('change');
  assert.equal(speechApp.window.recognition.stopCalls || 0, 0);
  assert.equal(speechApp.elements.speechButton.attributes['aria-label'], 'Stop dictation');
  speechApp.elements.speechButton.click();
  assert.equal(speechApp.window.recognition.stopCalls, 1, 'the explicit stop control still ends dictation');

  const staleQueue = createApp(); await wait();
  staleQueue.failNext(409, '', 'input_unavailable');
  staleQueue.commands.find(button => button.dataset.command === 'C').click();
  staleQueue.commands.find(button => button.dataset.command === 'RC').click();
  await wait();
  assert.equal(staleQueue.records.length, 1, 'disconnect drops input queued behind a failed request');
  assert(staleQueue.runStatusTimer()); await wait();
  assert.equal(staleQueue.records.length, 1, 'old queued clicks are not sent after reconnection');

  const reconnect = createApp(); await wait();
  reconnect.draft('Keep this draft');
  reconnect.setStatusFailure(true); assert(reconnect.runStatusTimer()); await wait();
  assert.equal(reconnect.elements.connectionButton.attributes['aria-label'], 'Disconnected; open connection settings');
  reconnect.commands.find(button => button.dataset.command === 'C').click();
  assert.equal(reconnect.records.length, 0, 'input is not queued while disconnected');
  reconnect.setStatusFailure(false); assert(reconnect.runStatusTimer()); await wait();
  assert.equal(reconnect.elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings');
  assert.equal(reconnect.elements.textInput.value, 'Keep this draft');
  assert.equal(reconnect.records.length, 0, 'reconnection never replays stale input');
  reconnect.elements.sendTextButton.click(); await wait();
  assert.equal(reconnect.records.at(-1).text, 'Keep this draft');
  reconnect.document.hidden = true; reconnect.document.emit('visibilitychange');
  assert.equal(reconnect.timers.size, 0, 'status polling stops while the page is hidden');
  const hiddenCount = reconnect.statusRequests.length;
  reconnect.window.emit('online'); await wait();
  assert.equal(reconnect.statusRequests.length, hiddenCount, 'hidden page does not issue status requests');
  reconnect.document.hidden = false; reconnect.document.emit('visibilitychange'); await wait();
  assert.equal(reconnect.statusRequests.length, hiddenCount + 1);

  const hiddenDrag = createApp(null, {}, {simulateDragRace: true}); await wait();
  hiddenDrag.elements.dragButton.click(); // MD is now in flight.
  hiddenDrag.commands.find(button => button.dataset.command === 'C').click(); // Queued click ends this drag in the UI.
  hiddenDrag.elements.dragButton.click(); // A new queued drag is also stale when the page hides.
  hiddenDrag.keys[0].click(); // A queued video key must be discarded.
  hiddenDrag.draft('Do not send this old draft'); hiddenDrag.elements.sendTextButton.click();
  hiddenDrag.document.hidden = true; hiddenDrag.document.emit('visibilitychange');
  await wait();
  assert.deepEqual(hiddenDrag.records.map(packet => packet.command), ['MD', 'MU'], 'only ordered mouse-up survives hidden-page cleanup');
  assert.deepEqual(hiddenDrag.commandEffects, ['beacon MU', 'MD', 'MU'], 'ordered release follows mouse-down when the beacon arrives early');
  assert.equal(hiddenDrag.dragState.held, false, 'receiver does not remain in drag after the page is hidden');
  assert.equal(hiddenDrag.elements.textInput.value, 'Do not send this old draft', 'discarded queued text stays in the draft');
  hiddenDrag.document.hidden = false; hiddenDrag.document.emit('visibilitychange'); await wait();
  assert.equal(hiddenDrag.records.length, 2, 'resuming does not replay dropped clicks, mouse-down, keys or text');

  const wrongToken = createApp(null, {paired: false}); await wait();
  assert.equal(wrongToken.elements.connectionMessage.textContent, 'Invalid pairing code. Check the code in the receiver.');
  assert.equal(wrongToken.timers.size, 0, 'invalid credentials are not retried endlessly');
  wrongToken.setStatus({paired: true}); wrongToken.elements.pairingCode.value = 'corrected'; wrongToken.elements.pairButton.click(); await wait();
  assert.equal(wrongToken.stored.get('watchmouse_token'), 'corrected');
  const overlapping = createApp(null, {}, {statusDelay: 10});
  overlapping.document.emit('visibilitychange'); overlapping.document.emit('visibilitychange');
  await wait(); await wait();
  assert.equal(overlapping.maxStatusActive(), 1, 'multiple resume triggers never overlap status requests');
  for (const [code, expected] of [
    ['accessibility_permission', 'Allow WatchMouse in Mac System Settings → Privacy & Security → Accessibility.'],
    ['windows_elevation', 'Windows did not accept input. Check whether the target app is running as administrator.']
  ]) {
    const coded = createApp(null, {inputReady: false, inputErrorCode: code, inputError: 'untranslated backend detail'}); await wait();
    assert.equal(coded.elements.connectionMessage.textContent, expected);
    coded.elements.languageSelect.value = 'zh'; coded.elements.languageSelect.emit('change');
    assert(/[\u4e00-\u9fff]/.test(coded.elements.connectionMessage.textContent), 'dynamic permission feedback switches language');
  }
  console.log('PASS: integrated minimal UI/silent success, modes/native focus, viewport resize, mouse/drag, independent scroll rail/fractions/cancel/cleanup, draft deletion/backspace, IME/Unicode send, pairing/input readiness, actionable permission errors/failed-send preservation, authenticated serialized requests, saved EN/ZH interface and pairing, interface-only dictation labels, non-overlapping status checks, permission/restart reconnect, hidden-page suspension, stale-input discard.');
})().catch(error => {console.error(error); process.exitCode = 1;});
