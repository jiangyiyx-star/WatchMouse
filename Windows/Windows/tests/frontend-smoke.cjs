// No browser dependencies: exercises the shipped script's event and API flow.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const path = require('path');
const html = fs.readFileSync(path.join(__dirname, '..', 'remote.html'), 'utf8');
const source = fs.readFileSync(path.join(__dirname, '..', 'remote.js'), 'utf8');
const wait = () => new Promise(resolve => setTimeout(resolve, 30));
async function settle(app, timeout = 5000) {
  const end = Date.now() + timeout;
  let stable = 0, count = -1;
  while (Date.now() < end) {
    await wait();
    if (!app.active() && app.records.length === count) stable++; else stable = 0;
    count = app.records.length;
    if (stable >= 2) return;
  }
  throw new Error('mock command queue did not settle');
}
function movementTotal(app) {
  return app.records.filter(packet => packet.command?.startsWith('M ')).reduce((total, packet) => {
    const [x, y] = packet.command.slice(2).split(',').map(Number);
    return [total[0] + x, total[1] + y];
  }, [0, 0]);
}

function createApp(savedMode = null, inputStatus = {}, options = {}) {
  let document;
  let scrollCalls = 0;
  let rectReads = 0;
  class Element {
    constructor() {
      this.tagName = ''; this.parentElement = null; this.children = []; this.childNodes = [];
      this.listeners = {}; this.style = {setProperty(name, value) {this[name] = value;}}; this.dataset = {}; this.attributes = {};
      this.captured = new Set();
      this.hidden = false; this.value = ''; this.textContent = ''; this.disabled = false;
      this.selectionStart = 0; this.selectionEnd = 0;
      const classes = new Set();
      this.classList = {
        toggle(name, force = !classes.has(name)) {if (force) classes.add(name); else classes.delete(name);},
        add(name) {classes.add(name);}, remove(name) {classes.delete(name);}, contains(name) {return classes.has(name);},
        set(value) {classes.clear(); for (const name of value.split(/\s+/).filter(Boolean)) classes.add(name);},
        toString() {return [...classes].join(' ');}
      };
    }
    addEventListener(name, listener) {(this.listeners[name] ||= []).push(listener);}
    emit(name, event = {}) {
      const delivered = {...event, target: event.target || this, defaultPrevented: false, preventDefault() {this.defaultPrevented = true;}, stopPropagation() {this.propagationStopped = true;}};
      for (const listener of this.listeners[name] || []) listener(delivered);
      return delivered;
    }
    dispatchEvent(event) {this.emit(event.type, event); return true;}
    get textContent() {return this.childNodes.map(node => typeof node === 'string' ? node : node.textContent).join('');}
    set textContent(value) {this.children = []; this.childNodes = [String(value)];}
    get className() {return this.classList.toString();}
    set className(value) {this.classList.set(value);}
    setAttribute(key, value) {
      this.attributes[key] = String(value);
      if (key === 'class') this.className = value;
      if (key.startsWith('data-')) this.dataset[key.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value);
    }
    getAttribute(key) {return this.attributes[key] ?? null;}
    querySelectorAll(selector) {return selectAll(selector, this);}
    querySelector(selector) {return this.querySelectorAll(selector)[0] || null;}
    getBoundingClientRect() {rectReads++; return {left: 0, top: 0};}
    setPointerCapture(id) {this.captured.add(id);}
    hasPointerCapture(id) {return this.captured.has(id);}
    releasePointerCapture(id) {this.captured.delete(id); this.emit('lostpointercapture', {pointerId: id});}
    focus() {document.activeElement = this;}
    blur() {if (document.activeElement === this) document.activeElement = null;}
    scrollIntoView() {scrollCalls++;}
    click() {if (!this.disabled) this.emit('click');}
    setSelectionRange(start, end = start) {this.selectionStart = start; this.selectionEnd = end;}
    setRangeText(text, start, end) {
      this.value = this.value.slice(0, start) + text + this.value.slice(end);
      this.setSelectionRange(start + text.length);
    }
  }
  // Parse enough HTML structure to preserve actual ancestry and one identity
  // per button, including buttons containing SVG rather than text glyphs.
  const elements = {};
  const allElements = [];
  document = new Element(); document.tagName = '#document';
  const stack = [document];
  const voidTags = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr']);
  const decode = text => text.replace(/&(?:amp|lt|gt|quot|apos|nbsp);|&#(?:x[0-9a-f]+|\d+);/gi, entity => {
    if (entity.startsWith('&#')) return String.fromCodePoint(entity[2].toLowerCase() === 'x' ? parseInt(entity.slice(3), 16) : parseInt(entity.slice(2), 10));
    return {amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0'}[entity.slice(1, -1).toLowerCase()];
  });
  let position = 0;
  const tags = /<!--[\s\S]*?-->|<![^>]*>|<\/?([A-Za-z][\w:-]*)\b([^>]*)>/g;
  for (const match of html.matchAll(tags)) {
    stack.at(-1).childNodes.push(decode(html.slice(position, match.index)));
    position = match.index + match[0].length;
    if (!match[1]) continue;
    const tagName = match[1].toLowerCase();
    if (match[0].startsWith('</')) {
      const index = stack.findLastIndex(node => node.tagName === tagName);
      if (index > 0) stack.length = index;
      continue;
    }
    const element = new Element(); element.tagName = tagName;
    const attributes = /([^\s=/'">]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+)))?/g;
    for (const attribute of match[2].replace(/\/$/, '').matchAll(attributes)) element.setAttribute(attribute[1].toLowerCase(), decode(attribute[2] ?? attribute[3] ?? attribute[4] ?? ''));
    element.hidden = Object.hasOwn(element.attributes, 'hidden');
    element.parentElement = stack.at(-1);
    element.parentElement.children.push(element); element.parentElement.childNodes.push(element);
    allElements.push(element);
    if (element.attributes.id) elements[element.attributes.id] = element;
    if (!voidTags.has(tagName) && !match[0].endsWith('/>')) stack.push(element);
  }
  function parseSimple(selector) {
    if (!selector) throw new Error('Empty selector in smoke DOM');
    let remaining = selector;
    const tag = /^[\w-]+|^\*/.exec(remaining);
    const filters = [];
    if (tag) remaining = remaining.slice(tag[0].length);
    while (remaining) {
      const name = /^([.#])([\w-]+)/.exec(remaining);
      const attribute = /^\[([\w-]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\]\s]+)))?\s*\]/.exec(remaining);
      if (name) {
        filters.push({kind: name[1] === '.' ? 'class' : 'id', name: name[2]});
        remaining = remaining.slice(name[0].length);
      } else if (attribute) {
        filters.push({kind: 'attribute', name: attribute[1], value: attribute[2] ?? attribute[3] ?? attribute[4]});
        remaining = remaining.slice(attribute[0].length);
      } else throw new Error('Unsupported selector in smoke DOM: ' + selector);
    }
    return {tag: tag?.[0]?.toLowerCase(), filters};
  }
  function matchesSimple(element, selector) {
    if (selector.tag && selector.tag !== '*' && selector.tag !== element.tagName) return false;
    return selector.filters.every(filter => {
      if (filter.kind === 'class') return element.classList.contains(filter.name);
      if (filter.kind === 'id') return element.attributes.id === filter.name;
      return Object.hasOwn(element.attributes, filter.name) && (filter.value === undefined || element.attributes[filter.name] === filter.value);
    });
  }
  function selectAll(selector, context = document) {
    const chains = selector.split(',').map(part => part.trim().split(/\s+/).map(parseSimple));
    const matchesChain = (element, chain) => {
      if (!matchesSimple(element, chain.at(-1))) return false;
      let ancestor = element.parentElement;
      for (let index = chain.length - 2; index >= 0; index--) {
        while (ancestor && !matchesSimple(ancestor, chain[index])) ancestor = ancestor.parentElement;
        if (!ancestor) return false;
        ancestor = ancestor.parentElement;
      }
      return true;
    };
    return allElements.filter(element => {
      let ancestor = element.parentElement;
      while (ancestor && ancestor !== context) ancestor = ancestor.parentElement;
      return ancestor === context && chains.some(chain => matchesChain(element, chain));
    });
  }
  // Standard DOM API: nearest ancestor (or self) matching the selector.
  Element.prototype.closest = function (selector) {
    const chains = selector.split(',').map(part => part.trim().split(/\s+/).map(parseSimple));
    for (let node = this; node; node = node.parentElement) {
      for (const chain of chains) {
        if (!matchesSimple(node, chain.at(-1))) continue;
        let ancestor = node.parentElement, matched = true;
        for (let index = chain.length - 2; index >= 0; index--) {
          while (ancestor && !matchesSimple(ancestor, chain[index])) ancestor = ancestor.parentElement;
          if (!ancestor) { matched = false; break; }
          ancestor = ancestor.parentElement;
        }
        if (matched) return node;
      }
    }
    return null;
  };
  document.hidden = false; document.activeElement = null;
  document.body = allElements.find(element => element.tagName === 'body');
  document.documentElement = allElements.find(element => element.tagName === 'html');
  document.getElementById = id => elements[id] || null;
  const commands = document.querySelectorAll('[data-command]');
  const keys = document.querySelectorAll('[data-key]');
  const modes = document.querySelectorAll('[data-mode]');
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
  const frames = new Map();
  let nextTimerId = 1, statusActive = 0, maxStatusActive = 0, statusFailure = null;
  let clockAdvance = 0, intervalCalls = 0;
  let holdCommands = Boolean(options.holdCommands), holdStatus = Boolean(options.holdStatus);
  const pendingNetwork = [];
  function scheduleTimeout(callback, delay) {
    if (delay <= 100 && !options.manualMotion) return setTimeout(callback, delay);
    const id = nextTimerId++; timers.set(id, {callback, delay}); return id;
  }
  function cancelTimeout(id) { if (!timers.delete(id)) clearTimeout(id); }
  function runStatusTimer() {
    const entry = [...timers.entries()].sort((a, b) => a[1].delay - b[1].delay)[0];
    if (!entry) return false;
    timers.delete(entry[0]); clockAdvance += entry[1].delay; entry[1].callback(); return entry[1].delay;
  }
  function runMotionTimer() {
    const entry = [...timers.entries()].find(([, timer]) => timer.delay <= 100);
    if (!entry) return false;
    timers.delete(entry[0]); clockAdvance += entry[1].delay; entry[1].callback(); return true;
  }
  function releaseOneCommand() {
    const entry = pendingNetwork.find(request => request.kind === 'command');
    if (!entry) return false;
    clockAdvance += 90; entry.release(); return true;
  }
  function networkWait(kind, signal) {
    const held = kind === 'status' ? holdStatus : holdCommands;
    const delay = kind === 'status' ? options.statusDelay || 0 : options.commandDelay || 2;
    return new Promise((resolve, reject) => {
      let timer;
      const entry = {kind, release: () => finish()};
      const abort = () => finish(Object.assign(new Error('aborted'), {name: 'AbortError'}));
      function finish(error) {
        if (timer) clearTimeout(timer);
        signal?.removeEventListener('abort', abort);
        const index = pendingNetwork.indexOf(entry);
        if (index >= 0) pendingNetwork.splice(index, 1);
        if (error) reject(error); else resolve();
      }
      if (signal?.aborted) { abort(); return; }
      signal?.addEventListener('abort', abort, {once: true});
      if (held) pendingNetwork.push(entry); else timer = setTimeout(() => finish(), delay);
    });
  }
  function resumeNetwork(kind) {
    if (kind === 'command') holdCommands = false; else holdStatus = false;
    for (const entry of [...pendingNetwork]) if (entry.kind === kind) entry.release();
  }

  const statusResult = {app: 'WatchMouse', paired: true, ...inputStatus};
  let active = 0, maxActive = 0, failure = null;
  const dragState = {held: false}, commandEffects = [], beacons = [];
  const browserLocation = {href: options.href || 'http://192.168.1.5:53514/?token=testtoken123456789', host: '192.168.1.5:53514'};
  const historyUpdates = [];
  if (!options.noHistory) window.history = {replaceState(_state, _title, href) { browserLocation.href = String(href); historyUpdates.push(browserLocation.href); }};
  const sandbox = {
    console, document, window, URL, Map, Promise, Math, Number, TypeError, Error, JSON, Array, Blob, Event, Intl,
    AbortController, setTimeout: scheduleTimeout, clearTimeout: cancelTimeout, setInterval: () => {intervalCalls++; return 0;}, performance: {now: () => performance.now() + clockAdvance},
    location: browserLocation,
    localStorage: {getItem: key => stored.get(key) || null, setItem: (key, value) => stored.set(key, value)},
    matchMedia: () => ({matches: false}),
    requestAnimationFrame: callback => {
      const id = nextTimerId++;
      frames.set(id, setTimeout(() => {frames.delete(id); callback();}, 16));
      return id;
    },
    cancelAnimationFrame: id => {clearTimeout(frames.get(id)); frames.delete(id);},
    navigator: {onLine: true, sendBeacon: (url, blob) => {
      beacons.push({url, blob});
      if (options.simulateDragRace) { dragState.held = false; commandEffects.push('beacon MU'); }
      return true;
    }},
    fetch: async (url, requestOptions) => {
      if (url.startsWith('/api/status')) {
        statusActive++; maxStatusActive = Math.max(maxStatusActive, statusActive);
        statusRequests.push({url, token: requestOptions.headers?.['X-WatchMouse-Token']});
        try { await networkWait('status', requestOptions.signal); } finally { statusActive--; }
        if (statusFailure) throw new TypeError('network request failed');
        return {ok: true, json: async () => ({...statusResult})};
      }
      active++; maxActive = Math.max(maxActive, active);
      const packet = JSON.parse(requestOptions.body);
      records.push(packet);
      try { await networkWait('command', requestOptions.signal); } finally { active--; }
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
  return {elements, document, window, dragState, commandEffects, beacons, location: browserLocation, historyUpdates, commands, keys, modes, records, stored, draft, statusRequests, timers, frames, runStatusTimer, runMotionTimer, releaseOneCommand, maxStatusActive: () => maxStatusActive, maxActive: () => maxActive, active: () => active, rectReads: () => rectReads, scrollCalls: () => scrollCalls, intervalCalls: () => intervalCalls, holdCommands: () => {holdCommands = true;}, holdStatus: () => {holdStatus = true;}, resumeCommands: () => resumeNetwork('command'), resumeStatus: () => resumeNetwork('status'), failNext: (status, error, errorCode) => {failure = {status, error, errorCode};}, setStatusFailure: fail => {statusFailure = fail;}, setStatus: update => Object.assign(statusResult, update)};
}

(async () => {
  const app = createApp();
  const {elements, document, commands, records, stored, draft} = app;
  await wait();
  assert.equal(elements.connectionButton.attributes['aria-label'], 'Connected; open connection settings');
  assert.equal(elements.actionFeedback.textContent, '', 'success does not announce or display text');
  assert(!elements.mousePanel.hidden && elements.douyinPanel.hidden && elements.keyboardPanel.hidden);
  assert.equal(document.activeElement, null);
  assert(elements.speechButton.hidden);
  assert.deepEqual(document.querySelectorAll('.missing-control button'), []);
  assert.deepEqual(document.querySelectorAll('[data-missing]'), []);
  const inputButtons = document.querySelectorAll('.draft-actions button, .draft-composer button');
  assert(inputButtons.includes(elements.sendTextButton) && !inputButtons.includes(elements.douyinModeButton));

  elements.douyinModeButton.click();
  assert(elements.mousePanel.hidden && !elements.douyinPanel.hidden && elements.keyboardPanel.hidden);
  assert.equal(stored.get('watchmouse_mode'), 'douyin');
  assert.equal(elements.douyinModeButton.attributes['aria-pressed'], 'true');
  elements.keyboardModeButton.click();
  assert(!elements.mousePanel.hidden && elements.douyinPanel.hidden && !elements.keyboardPanel.hidden);
  assert.equal(document.activeElement, elements.textInput, 'trusted keyboard-mode click focuses native textarea');
  assert.equal(app.scrollCalls(), 0);
  elements.mouseModeButton.click();
  assert(elements.keyboardPanel.hidden && !elements.mousePanel.hidden);
  assert.equal(document.activeElement, null);
  const restored = createApp('keyboard');
  assert(!restored.elements.keyboardPanel.hidden);
  assert.equal(restored.document.activeElement, null, 'restoring mode must not auto-open native keyboard');
  assert(createApp('invalid').elements.keyboardPanel.hidden);

  // Gamepad mode: Xbox/PlayStation layouts, press-and-hold buttons, analog sticks.
  elements.gamepadModeButton.click();
  assert(elements.mousePanel.hidden && elements.douyinPanel.hidden && elements.keyboardPanel.hidden && !elements.gamepadPanel.hidden);
  assert.equal(stored.get('watchmouse_mode'), 'gamepad');
  assert.equal(elements.gamepadModeButton.attributes['aria-pressed'], 'true');
  assert.equal(elements.gamepadPanel.dataset.layout, 'xbox', 'Xbox layout is the default');
  assert.equal(elements.xboxLayoutButton.attributes['aria-pressed'], 'true');
  elements.psLayoutButton.click();
  assert.equal(elements.gamepadPanel.dataset.layout, 'ps', 'PlayStation layout swaps in DualShock labels');
  assert.equal(stored.get('watchmouse_pad_layout'), 'ps');
  assert.equal(elements.psLayoutButton.attributes['aria-pressed'], 'true');
  assert.equal(elements.xboxLayoutButton.attributes['aria-pressed'], 'false');
  elements.xboxLayoutButton.click();
  assert.equal(elements.gamepadPanel.dataset.layout, 'xbox');
  assert.equal(createApp('gamepad', {}, {stored: new Map([['watchmouse_pad_layout', 'ps']])}).elements.gamepadPanel.dataset.layout, 'ps', 'chosen layout persists across reloads');

  const padButton = name => document.querySelectorAll('#gamepadPanel [data-pad]').find(button => button.dataset.pad === name);

  // Layout follows a real controller: shoulders in the two top corners, thumb
  // stacks hugging the bottom edges, View/Menu parked out of thumb reach.
  for (const shoulder of ['lt', 'lb', 'rb', 'rt']) {
    assert(padButton(shoulder), 'shoulder ' + shoulder + ' has a button');
  }
  assert(padButton('select') && padButton('start'), 'Select and Start exist');
  assert(document.querySelector('#gamepadPanel .pad-grip-left') && document.querySelector('#gamepadPanel .pad-grip-right'),
    'left and right thumb grips are separate groups');
  assert(document.querySelector('#gamepadPanel .pad-shoulders') && document.querySelector('#gamepadPanel .pad-field'),
    'shoulder row and thumb field are laid out separately');

  // Immersive mode: one button toggles the fullscreen class, and leaving the
  // gamepad tab drops it again so the browse views keep their chrome.
  const fullscreenButton = document.getElementById('padFullscreenButton');
  assert(fullscreenButton, 'fullscreen button is present');
  fullscreenButton.emit('click');
  assert(document.body.classList.contains('pad-immersive'), 'fullscreen button enters immersive mode');
  assert.equal(fullscreenButton.attributes['aria-pressed'], 'true');
  await wait();
  fullscreenButton.emit('click');
  assert(!document.body.classList.contains('pad-immersive'), 'fullscreen button exits immersive mode');

  records.length = 0;
  padButton('a').emit('pointerdown', {pointerId: 21, button: 0});
  assert(padButton('a').classList.contains('is-pressed'));
  padButton('a').emit('pointerup', {pointerId: 21, button: 0});
  await wait();
  assert.deepEqual(records.map(packet => [packet.key, packet.state]), [['space', 'down'], ['space', 'up']],
    'A is held as its mapped key and released on pointerup');

  // Held shoulders and sticks nest by reference count, so two sources for one
  // key never release it early.
  records.length = 0;
  padButton('dup').emit('pointerdown', {pointerId: 22, button: 0});
  await wait();
  assert.deepEqual(records.map(packet => [packet.key, packet.state]), [['w', 'down']], 'd-pad up holds W');
  const leftStick = document.querySelectorAll('#gamepadPanel .stick').find(node => node.dataset.stick === 'left');
  leftStick.getBoundingClientRect = () => ({left: 0, top: 0, width: 100, height: 100});
  leftStick.emit('pointerdown', {pointerId: 23, button: 0, clientX: 50, clientY: 50});
  await wait();
  assert.equal(records.length, 1, 'stick centre stays inside the dead zone');
  leftStick.emit('pointermove', {pointerId: 23, clientX: 50, clientY: 2});
  await wait();
  assert.equal(records.length, 1, 'd-pad up already holds W, so the stick does not re-send the same key');
  leftStick.emit('pointermove', {pointerId: 23, clientX: 98, clientY: 50});
  await wait();
  assert.deepEqual(records.slice(1).map(packet => [packet.key, packet.state]), [['d', 'down']], 'stick right adds D');
  leftStick.emit('pointerup', {pointerId: 23, clientX: 98, clientY: 50});
  await wait();
  assert.deepEqual(records.slice(2).map(packet => [packet.key, packet.state]), [['d', 'up']],
    'releasing the stick drops only its own key');
  padButton('dup').emit('pointerup', {pointerId: 22, button: 0});
  await wait();
  assert.deepEqual(records.slice(3).map(packet => [packet.key, packet.state]), [['w', 'up']],
    'the d-pad release still releases W it held');
  assert(!padButton('dup').classList.contains('is-pressed') && !leftStick.classList.contains('active'));

  // Trackpad in the seam between the grips: drag moves the cursor, a short tap
  // clicks, holding still right-clicks, and leaving the tab clears it.
  const padTrackpad = document.getElementById('padTrackpad');
  assert(padTrackpad, 'the pad keeps a trackpad between the two grips');
  padTrackpad.getBoundingClientRect = () => ({left: 600, top: 200, width: 200, height: 100});

  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 31, button: 0, clientX: 600, clientY: 200});
  assert(padTrackpad.classList.contains('active'), 'touching the pad trackpad highlights it');
  padTrackpad.emit('pointermove', {pointerId: 31, clientX: 620, clientY: 208});
  padTrackpad.emit('pointermove', {pointerId: 31, clientX: 640, clientY: 210});
  padTrackpad.emit('pointerup', {pointerId: 31, clientX: 640, clientY: 210});
  await wait(); await wait(); await wait();
  const padMoves = records.filter(packet => packet.command?.startsWith('M '));
  assert(padMoves.length >= 1, 'dragging the pad trackpad moves the mouse');
  assert(!records.some(packet => packet.command === 'C'), 'a drag is not a click');
  assert(!padTrackpad.classList.contains('active'), 'the highlight clears on release');

  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 32, button: 0, clientX: 600, clientY: 200});
  padTrackpad.emit('pointerup', {pointerId: 32, clientX: 601, clientY: 201});
  await wait(); await wait(); await wait();
  assert.equal(records.filter(packet => packet.command).at(-1)?.command, 'C', 'a short tap clicks the left button');

  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 33, button: 0, clientX: 600, clientY: 200});
  await new Promise(resolve => setTimeout(resolve, 470));
  padTrackpad.emit('pointerup', {pointerId: 33, clientX: 600, clientY: 200});
  await wait(); await wait(); await wait();
  assert.equal(records.filter(packet => packet.command).at(-1)?.command, 'RC', 'holding still right-clicks');

  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 34, button: 0, clientX: 600, clientY: 200});
  elements.mouseModeButton.click();
  await wait(); await wait(); await wait();
  assert(!padTrackpad.classList.contains('active'), 'leaving the pad tab clears the trackpad state');
  elements.gamepadModeButton.click();
  await wait(); await wait(); await wait();

  // Rotating the phone: browsers can drop the touch without a pointerup or
  // pointercancel (iOS in landscape is the usual culprit). The pad trackpad
  // must clear itself, or it stays "held" forever and stops responding.
  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 35, button: 0, clientX: 600, clientY: 200});
  assert(padTrackpad.classList.contains('active'), 'the pad trackpad is held before rotating');
  app.window.emit('orientationchange');
  await wait();
  assert(!padTrackpad.classList.contains('active'), 'rotating clears the stuck touch on the pad trackpad');
  padTrackpad.emit('pointerdown', {pointerId: 36, button: 0, clientX: 600, clientY: 200});
  padTrackpad.emit('pointermove', {pointerId: 36, clientX: 640, clientY: 210});
  padTrackpad.emit('pointerup', {pointerId: 36, clientX: 640, clientY: 210});
  await wait(); await wait(); await wait();
  assert(records.some(packet => packet.command?.startsWith('M ')), 'the pad trackpad works again after rotating');

  // A lost pointerup without any rotation must self-heal on the next touch too.
  records.length = 0;
  padTrackpad.emit('pointerdown', {pointerId: 37, button: 0, clientX: 600, clientY: 200});
  padTrackpad.emit('pointerdown', {pointerId: 38, button: 0, clientX: 600, clientY: 200});
  padTrackpad.emit('pointermove', {pointerId: 38, clientX: 630, clientY: 206});
  padTrackpad.emit('pointerup', {pointerId: 38, clientX: 630, clientY: 206});
  await wait(); await wait(); await wait();
  assert(records.some(packet => packet.command?.startsWith('M ')), 'a lost pointerup does not lock the pad trackpad');
  assert(!padTrackpad.classList.contains('active'), 'the pad trackpad ends up released');

  // Same failure mode on the mouse touchpad: one stale finger used to turn
  // every later drag into a two-finger scroll.
  records.length = 0;
  elements.mouseModeButton.click();
  await wait();
  elements.touchpad.emit('pointerdown', {pointerId: 39, pointerType: 'touch', clientX: 0, clientY: 0});
  app.window.emit('orientationchange');
  await wait();
  elements.touchpad.emit('pointerdown', {pointerId: 40, pointerType: 'touch', clientX: 0, clientY: 0});
  elements.touchpad.emit('pointermove', {pointerId: 40, clientX: 10, clientY: 4});
  elements.touchpad.emit('pointerup', {pointerId: 40, clientX: 10, clientY: 4});
  await wait(); await wait(); await wait();
  assert(records.some(packet => packet.command?.startsWith('M ')), 'the mouse touchpad still moves the cursor after rotating');
  elements.gamepadModeButton.click();
  await wait(); await wait(); await wait();

  // Leaving gamepad mode while a button is down must not leave it stuck.
  records.length = 0;
  padButton('b').emit('pointerdown', {pointerId: 24, button: 0});
  assert(padButton('b').classList.contains('is-pressed'));
  elements.mouseModeButton.click();
  await wait();
  assert(elements.gamepadPanel.hidden && !elements.mousePanel.hidden);
  assert(records.some(packet => packet.command === 'MU'), 'leaving gamepad mode queues a release for held keys');
  assert(!padButton('b').classList.contains('is-pressed'));
  assert(!document.body.classList.contains('pad-immersive'), 'leaving the pad tab also leaves immersive mode');

// Native pad mode: a receiver with ViGEmBus reports nativeGamepad, so the
  // gamepad panel posts controller snapshots instead of mapped keystrokes.
  const settle = () => new Promise(resolve => setTimeout(resolve, 140));
  // Settings diagnostics explain how keys are injected and warn when the
  // receiver cannot reach an elevated game.
  const diag = createApp('gamepad', {keyboardMode: 'scancode', elevated: false});
  await wait(); await wait();
  const diagNote = diag.document.getElementById('inputModeNote');
  assert(diagNote && !diagNote.hidden, 'connection settings show the input diagnostics note');
  assert(diagNote.textContent.includes('scancode'), 'the note names the scancode injection');
  assert(diagNote.textContent.toLowerCase().includes('administrator'), 'the note warns about elevated games');
  const plain = createApp('gamepad', {keyboardMode: 'virtual-key', elevated: true});
  await wait(); await wait();
  assert(plain.document.getElementById('inputModeNote').hidden,
    'a virtual-key receiver without elevation trouble shows no note');

  const native = createApp('gamepad', {nativeGamepad: true});
  await wait();
  const nativeButton = name => native.document.querySelectorAll('#gamepadPanel [data-pad]').find(button => button.dataset.pad === name);
  const nativePad = () => native.records.filter(packet => packet.pad).map(packet => packet.pad).at(-1);
  assert(native.document.querySelector('#gamepadPanel .gamepad-hint').textContent.includes('Xbox'),
    'the hint switches to the native mode wording');
  assert.equal(native.intervalCalls(), 0, 'native keep-alive uses timeouts, not a permanent interval');

  nativeButton('a').emit('pointerdown', {pointerId: 31, button: 0});
  await settle();
  assert.deepEqual(nativePad().buttons, ['a'], 'native mode posts the pad button id');
  assert.equal(native.records.filter(packet => packet.key).length, 0, 'native mode sends no keyboard commands');

  const nativeStick = native.document.querySelectorAll('#gamepadPanel .stick').find(node => node.dataset.stick === 'right');
  nativeStick.getBoundingClientRect = () => ({left: 0, top: 0, width: 100, height: 100});
  nativeStick.emit('pointerdown', {pointerId: 32, button: 0, clientX: 50, clientY: 50});
  nativeStick.emit('pointermove', {pointerId: 32, clientX: 100, clientY: 50});
  await settle();
  const axesSent = nativePad();
  assert(axesSent.rx > 0.9 && axesSent.ry === 0, 'the right stick travels as an analog axis');

  nativeButton('rt').emit('pointerdown', {pointerId: 33, button: 0});
  await settle();
  assert.equal(nativePad().rt, 1, 'RT travels as a trigger value');
  assert(!nativePad().buttons.includes('rt'), 'triggers are not duplicated as buttons');

  nativeStick.emit('pointerup', {pointerId: 32, clientX: 100, clientY: 50});
  nativeButton('rt').emit('pointerup', {pointerId: 33, button: 0});
  nativeButton('a').emit('pointerup', {pointerId: 31, button: 0});
  await settle();
  const neutralPad = nativePad();
  assert.deepEqual(neutralPad.buttons, [], 'releasing everything sends a neutral snapshot');
  assert.equal(neutralPad.rt, 0);
  assert.equal(neutralPad.rx, 0);

  // Leaving the panel while holding a native button must release it too.
  nativeButton('x').emit('pointerdown', {pointerId: 34, button: 0});
  await settle();
  assert.deepEqual(nativePad().buttons, ['x']);
  native.elements.mouseModeButton.click();
  await settle();
  assert.deepEqual(nativePad().buttons, [], 'switching mode releases the native pad');

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
  assert.equal(speechApp.elements.speechButton.attributes['aria-pressed'], 'true', 'active recording remains active without replacing its SVG');
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

  const tail = createApp(); await wait();
  tail.elements.sensitivity.value = '2'; tail.elements.sensitivity.emit('input');
  tail.elements.touchpad.emit('pointerdown', {pointerId: 101, pointerType: 'touch', clientX: 100, clientY: 100});
  tail.elements.touchpad.emit('pointerup', {pointerId: 101, clientX: 110, clientY: 130});
  await settle(tail);
  assert.deepEqual(movementTotal(tail), [20, 60], 'pointer-up includes the final position even without a final move event');
  assert(!tail.records.some(packet => packet.command === 'C'), 'moving before pointer-up must not become a tap');
  tail.elements.scrollSurface.emit('pointerdown', {pointerId: 102, pointerType: 'touch', clientY: 100});
  tail.elements.scrollSurface.emit('pointerup', {pointerId: 102, clientY: 140});
  await settle(tail);
  assert.equal(tail.records.at(-1).command, 'S -2', 'rail pointer-up also includes its final coordinate');

  const slow = createApp(null, {}, {holdCommands: true, manualMotion: true}); await wait();
  slow.elements.sensitivity.value = '2'; slow.elements.sensitivity.emit('input');
  slow.elements.touchpad.emit('pointerdown', {pointerId: 110, pointerType: 'touch', clientX: 0, clientY: 0});
  slow.elements.scrollSurface.emit('pointerdown', {pointerId: 111, pointerType: 'touch', clientY: 100});
  for (let step = 1; step <= 24; step++) {
    slow.elements.touchpad.emit('pointermove', {pointerId: 110, clientX: step * 3, clientY: 0});
    slow.elements.scrollSurface.emit('pointermove', {pointerId: 111, clientY: 100 + step * 20});
    slow.runMotionTimer();
  }
  slow.elements.touchpad.emit('pointerup', {pointerId: 110, clientX: 80, clientY: 0});
  slow.elements.scrollSurface.emit('pointerup', {pointerId: 111, clientY: 600});
  assert.equal(slow.records.length, 1, 'all samples arrive while exactly one command is in flight');
  for (let response = 0; response < 12 && slow.releaseOneCommand(); response++) await wait();
  await settle(slow);
  assert.deepEqual(movementTotal(slow), [160, 0], 'slow requests preserve every movement plus its tail');
  const wheelTotal = slow.records.filter(packet => packet.command?.startsWith('S ')).reduce((sum, packet) => sum + Number(packet.command.slice(2)), 0);
  assert.equal(wheelTotal, -25);
  assert(slow.records.length <= 4, 'one slow in-flight window leaves at most the original scroll plus one accumulated move/scroll batch');
  assert.equal(slow.maxActive(), 1);
  assert.equal(slow.rectReads(), 1, 'a continuous gesture reads its layout once rather than on every input event');
  console.log('PERF: 24 alternating samples during one held request:', slow.records.length, 'packets, full 160 px / 25 wheel steps,', slow.rectReads(), 'layout read (ACKs released manually).');

  const ordered = createApp(); await wait(); ordered.holdCommands();
  ordered.commands.find(button => button.dataset.command === 'C').click();
  ordered.elements.sensitivity.value = '2'; ordered.elements.sensitivity.emit('input');
  ordered.elements.touchpad.emit('pointerdown', {pointerId: 120, pointerType: 'touch', clientX: 0, clientY: 0});
  ordered.elements.touchpad.emit('pointermove', {pointerId: 120, clientX: 10, clientY: 0});
  ordered.commands.find(button => button.dataset.command === 'RC').click();
  ordered.elements.touchpad.emit('pointerup', {pointerId: 120, clientX: 20, clientY: 0});
  ordered.resumeCommands(); await settle(ordered);
  assert.deepEqual(ordered.records.map(packet => packet.command), ['C', 'M 20,0', 'RC', 'M 20,0'], 'discrete actions remain barriers between earlier and later motion');

  const large = createApp(); await wait(); large.elements.sensitivity.value = '2'; large.elements.sensitivity.emit('input');
  large.elements.touchpad.emit('pointerdown', {pointerId: 130, pointerType: 'touch', clientX: 0, clientY: 0});
  large.elements.touchpad.emit('pointerup', {pointerId: 130, clientX: 10001, clientY: 0}); await settle(large);
  assert.deepEqual(movementTotal(large), [20002, 0]);
  assert(large.records.every(packet => Math.abs(Number(packet.command.slice(2).split(',')[0])) <= 4096), 'large accumulated motion remains valid server-size chunks');

  const released = createApp(null, {}, {simulateDragRace: true}); await wait(); released.holdCommands();
  released.elements.dragButton.click();
  released.commands.find(button => button.dataset.command === 'C').click(); // UI is no longer dragging, but MD has not completed.
  assert.equal(released.elements.dragButton.attributes['aria-pressed'], 'false');
  released.window.visualViewport.emit('resize'); released.window.visualViewport.emit('resize');
  released.document.hidden = true; released.document.emit('visibilitychange');
  released.resumeCommands(); await settle(released);
  assert.deepEqual(released.records.map(packet => packet.command), ['MD', 'MU'], 'an in-flight MD is released even after its queued click changed the UI');
  assert.deepEqual(released.commandEffects, ['beacon MU', 'MD', 'MU']);
  assert.equal(released.dragState.held, false);
  assert.equal(released.beacons.length, 1, 'repeated resize/hide events do not pile up duplicate releases');

  const probeRace = createApp(null, {}, {simulateDragRace: true}); await wait();
  probeRace.holdStatus(); probeRace.window.emit('online');
  probeRace.holdCommands(); probeRace.elements.dragButton.click();
  probeRace.setStatusFailure(true); probeRace.resumeStatus(); await wait();
  assert.equal(probeRace.elements.connectionButton.attributes['aria-label'], 'Disconnected; open connection settings');
  probeRace.resumeCommands(); await settle(probeRace);
  assert.deepEqual(probeRace.records.map(packet => packet.command), ['MD', 'MU'], 'status failure retains an ordered release after the in-flight MD');
  assert.deepEqual(probeRace.commandEffects, ['beacon MU', 'MD', 'MU']);
  assert.equal(probeRace.dragState.held, false);
  assert(probeRace.records.every(packet => packet.token === 'testtoken123456789'), 'safety release keeps the mouse-down token');

  const queuedRelease = createApp(null, {}, {simulateDragRace: true}); await wait(); queuedRelease.holdCommands();
  queuedRelease.elements.dragButton.click(); queuedRelease.elements.dragButton.click(); // MU is queued before hiding.
  queuedRelease.document.hidden = true; queuedRelease.document.emit('visibilitychange');
  assert.equal(queuedRelease.beacons.length, 1, 'a queued normal MU must not suppress the background beacon');
  queuedRelease.resumeCommands(); await settle(queuedRelease);
  assert.deepEqual(queuedRelease.records.map(packet => packet.command), ['MD', 'MU']);
  assert.equal(queuedRelease.dragState.held, false);

  const acceptedText = createApp(); await wait(); acceptedText.holdCommands(); acceptedText.draft('Accepted once');
  acceptedText.elements.sendTextButton.click(); acceptedText.document.hidden = true; acceptedText.document.emit('visibilitychange');
  acceptedText.resumeCommands(); await settle(acceptedText);
  assert.equal(acceptedText.elements.textInput.value, '', 'an acknowledged in-flight text send remains confirmed after hiding');
  acceptedText.document.hidden = false; acceptedText.document.emit('visibilitychange'); await wait();
  assert.equal(acceptedText.records.length, 1, 'resuming never repeats accepted text');

  const bounded = createApp(); await wait(); bounded.holdCommands();
  for (let index = 0; index < 100; index++) bounded.commands.find(button => button.dataset.command === 'C').click();
  assert.equal(bounded.records.length, 1);
  assert.equal(bounded.elements.actionFeedback.textContent, 'Input queue is busy. Try again shortly.');
  bounded.document.hidden = true; bounded.document.emit('visibilitychange'); bounded.resumeCommands(); await settle(bounded);
  assert.equal(bounded.records.length, 1, 'background cleanup discards accumulated clicks instead of playing them later');

  const suspended = createApp(null, {}, {holdStatus: true});
  assert.equal(suspended.statusRequests.length, 1);
  suspended.document.hidden = true; suspended.document.emit('visibilitychange'); await wait();
  assert.equal(suspended.timers.size, 0, 'hiding aborts the current status probe and removes its timeout');
  assert.equal(suspended.frames.size, 0);
  assert.equal(suspended.intervalCalls(), 0, 'idle pages have no permanent heartbeat interval');
  suspended.window.emit('online'); await wait();
  assert.equal(suspended.statusRequests.length, 1);
  suspended.resumeStatus(); suspended.document.hidden = false; suspended.document.emit('visibilitychange'); await wait();
  assert.equal(suspended.statusRequests.length, 2, 'restoring performs one fresh status check');

  const heartbeat = createApp(); await wait();
  assert.equal(heartbeat.timers.size, 1, 'healthy idle page has only its status timer');
  heartbeat.elements.dragButton.click(); await wait();
  assert(heartbeat.runStatusTimer()); await wait();
  assert.equal(heartbeat.records.filter(packet => packet.command === 'MD').length, 2, 'only an idle held drag gets a heartbeat');
  heartbeat.document.hidden = true; heartbeat.document.emit('visibilitychange'); await settle(heartbeat);
  assert.equal(heartbeat.timers.size, 0, 'no heartbeat or polling remains in the background');

  console.log('PASS: integrated minimal UI/silent success, modes/native focus, viewport resize, mouse/drag, independent scroll rail/fractions/cancel/cleanup, draft deletion/backspace, IME/Unicode send, pairing/input readiness, actionable permission errors/failed-send preservation, authenticated serialized requests, saved EN/ZH interface and pairing, interface-only dictation labels, non-overlapping status checks, permission/restart reconnect, hidden-page suspension, stale-input discard, pad trackpad drag/tap/hold-right-click.');
})().catch(error => {console.error(error); process.exitCode = 1;});
