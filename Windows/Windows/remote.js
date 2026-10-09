(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch (_) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (_) {} }
  };
  const url = new URL(location.href);
  let token = url.searchParams.get('token') || storage.get('watchmouse_token') || '';
  let connected = false;
  let draining = false;
  let dragActive = false;
  let composing = false;
  let pendingX = 0, pendingY = 0, pendingScroll = 0;
  let pendingRailScroll = 0;
  let railPointer = null;
  let motionTimer = null;
  let statusVersion = 0;
  const queue = [];
  const pointers = new Map();
  let gesture = null;
  let speech = null;
  let speechListening = false;
  let inputVersion = 0;
  let sensitivity = Number(storage.get('watchmouse_sensitivity')) || 1.4;
  const savedMode = storage.get('watchmouse_mode');
  let mode = null;

  $('sensitivity').value = String(sensitivity);
  $('pairingCode').value = token;
  $('serverAddress').textContent = location.host;
  function refreshWatchLink() {
    $('watchLink').href = '/watch' + (token ? '?token=' + encodeURIComponent(token) : '');
  }
  refreshWatchLink();

  function feedback(message, error = false) {
    $('actionFeedback').textContent = error ? message : '';
    $('actionFeedback').classList.toggle('error', error);
    $('actionFeedback').classList.toggle('visually-hidden', !error);
  }
  function textFeedback(message = '', error = false) {
    $('textFeedback').textContent = error ? message : '';
    $('textFeedback').classList.toggle('error', error);
    $('textFeedback').classList.toggle('visually-hidden', !error);
  }
  function setConnection(ok, message) {
    connected = ok;
    $('statusDot').className = 'status-dot ' + (ok ? 'connected' : 'error');
    $('connectionButton').setAttribute('aria-label', (ok ? '已连接' : '未连接') + '，打开连接设置');
    $('connectionMessage').textContent = ok ? '' : message;
    if (!ok) {
      while (queue.length) {
        const item = queue.shift();
        if (item.reject) item.reject(new Error(message));
      }
      pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
      clearRailGesture();
      dragActive = false;
      updateDragUI();
      setConnectionPanel(true);
    }
  }
  function setConnectionPanel(open) {
    $('connectionPanel').hidden = !open;
    $('connectionButton').setAttribute('aria-expanded', String(open));
  }
  function errorMessage(error) {
    if (error.status === 401 || error.status === 403) return '配对码无效';
    if (error.status === 409) return error.message && error.message.length <= 200 && error.message !== '操作失败' ? error.message : '电脑未接收输入';
    if (error.status === 400) return '操作失败';
    if (error.name === 'AbortError') return '连接超时';
    return error.message && error.message.length <= 24 ? error.message : '操作失败';
  }
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    try {
      const response = await fetch(path, {cache: 'no-store', ...options, signal: controller.signal});
      let result;
      try { result = await response.json(); } catch (_) { throw new Error('响应异常'); }
      if (!response.ok || result.ok === false) {
        const error = new Error(result.error || '操作失败');
        error.status = response.status;
        throw error;
      }
      return result;
    } catch (error) {
      if (error instanceof TypeError) throw new Error('连接断开');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  async function checkConnection() {
    const version = ++statusVersion;
    $('connectionButton').setAttribute('aria-label', '正在连接，打开连接设置');
    $('statusDot').className = 'status-dot';
    $('connectionMessage').textContent = '';
    $('pairButton').disabled = true;
    try {
      const result = await request('/api/status' + (token ? '?token=' + encodeURIComponent(token) : ''), {headers: token ? {'X-WatchMouse-Token': token} : {}});
      if (version !== statusVersion) return;
      if (result.app !== 'WatchMouse') throw new Error('地址无效');
      if (!result.paired) {
        setConnection(false, '输入配对码');
        feedback();
        return;
      }
      storage.set('watchmouse_token', token);
      if (result.inputReady === false) {
        const message = result.inputError || '电脑输入权限未开启';
        setConnection(false, message);
        feedback(message, true);
        return;
      }
      setConnection(true);
      setConnectionPanel(false);
      feedback();
    } catch (error) {
      if (version !== statusVersion) return;
      const message = errorMessage(error);
      setConnection(false, message);
      feedback();
    } finally { if (version === statusVersion) $('pairButton').disabled = false; }
  }

  // Serialize input and merge adjacent motion packets to preserve distance
  // without issuing a network request for every touch sample.
  function enqueue(item) {
    if (!connected) {
      if (item.reject) item.reject(new Error('未连接'));
      feedback('未连接', true);
      setConnectionPanel(true);
      return;
    }
    const last = queue[queue.length - 1];
    if (last && item.kind === last.kind && (item.kind === 'move' || (item.kind === 'scroll' && item.source === last.source))) {
      if (item.kind === 'move') { last.x += item.x; last.y += item.y; }
      else last.amount += item.amount;
    } else queue.push(item);
    drain();
  }
  async function drain() {
    if (draining) return;
    draining = true;
    try {
      while (queue.length && connected) {
        const item = queue.shift();
        let payload = item.payload;
        if (item.kind === 'move') {
          const x = Math.max(-4096, Math.min(4096, item.x)), y = Math.max(-4096, Math.min(4096, item.y));
          if (x !== item.x || y !== item.y) queue.unshift({kind: 'move', x: item.x - x, y: item.y - y});
          if (!x && !y) continue;
          payload = {command: 'M ' + x + ',' + y};
        }
        if (item.kind === 'scroll') {
          const amount = Math.max(-100, Math.min(100, item.amount));
          if (amount !== item.amount) queue.unshift({kind: 'scroll', amount: item.amount - amount, source: item.source});
          if (!amount) continue;
          payload = {command: 'S ' + amount};
        }
        try {
          await request('/api/command', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': token}, body: JSON.stringify({...payload, token})});
          if (item.resolve) item.resolve();
          feedback();
        } catch (error) {
          if (item.reject) item.reject(error);
          while (queue.length) {
            const dropped = queue.shift();
            if (dropped.reject) dropped.reject(error);
          }
          pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
          const message = errorMessage(error);
          setConnection(false, message);
          feedback(message, true);
        }
      }
    } finally { draining = false; }
  }
  function flushMotion() {
    if (motionTimer) { clearTimeout(motionTimer); motionTimer = null; }
    const x = Math.trunc(pendingX), y = Math.trunc(pendingY), scroll = Math.trunc(pendingScroll), railScroll = Math.trunc(pendingRailScroll);
    pendingX -= x; pendingY -= y; pendingScroll -= scroll; pendingRailScroll -= railScroll;
    if (x || y) enqueue({kind: 'move', x, y});
    if (scroll) enqueue({kind: 'scroll', amount: scroll});
    if (railScroll) enqueue({kind: 'scroll', amount: railScroll, source: 'rail'});
  }
  function scheduleMotion() { if (!motionTimer) motionTimer = setTimeout(flushMotion, 28); }
  function send(payload) {
    flushMotion();
    return new Promise((resolve, reject) => enqueue({kind: 'command', payload, resolve, reject}));
  }
  function sendQuietly(payload) { send(payload).catch(() => {}); }

  $('connectionButton').addEventListener('click', () => setConnectionPanel($('connectionPanel').hidden));
  $('pairButton').addEventListener('click', () => {
    token = $('pairingCode').value.trim();
    refreshWatchLink();
    checkConnection();
  });
  $('pairingCode').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); $('pairButton').click(); } });
  $('sensitivity').addEventListener('input', event => { sensitivity = Number(event.target.value); storage.set('watchmouse_sensitivity', String(sensitivity)); });
  document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => {
    if (dragActive && (button.dataset.command === 'C' || button.dataset.command === 'RC')) {
      dragActive = false;
      updateDragUI();
    }
    sendQuietly({command: button.dataset.command});
  }));
  document.querySelectorAll('[data-key]').forEach(button => button.addEventListener('click', () => {
    sendQuietly({key: button.dataset.key, modifiers: button.dataset.modifiers ? button.dataset.modifiers.split(',') : []});
  }));
  document.querySelectorAll('.draft-actions button, .draft-composer button, .mouse-buttons button, .scroll-rail button').forEach(button => button.addEventListener('pointerdown', event => event.preventDefault()));

  function updateDragUI() {
    $('dragButton').setAttribute('aria-pressed', String(dragActive));
    $('dragButton').setAttribute('aria-label', dragActive ? '拖动已开启，点击松开左键' : '拖动，点击按住左键');
    $('touchpad').classList.toggle('dragging', dragActive);
  }
  $('dragButton').addEventListener('click', () => {
    if (!connected) { feedback('未连接', true); setConnectionPanel(true); return; }
    dragActive = !dragActive;
    updateDragUI();
    sendQuietly({command: dragActive ? 'MD' : 'MU'});
  });

  const pad = $('touchpad');
  function showPointer(event) {
    const rect = pad.getBoundingClientRect();
    $('touchIndicator').style.left = (event.clientX - rect.left) + 'px';
    $('touchIndicator').style.top = (event.clientY - rect.top) + 'px';
    $('touchIndicator').hidden = false;
  }
  function centroid() {
    const values = [...pointers.values()];
    return values.reduce((out, point) => ({x: out.x + point.x / values.length, y: out.y + point.y / values.length}), {x: 0, y: 0});
  }
  pad.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();
    if (!connected) { feedback('未连接', true); setConnectionPanel(true); return; }
    pad.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
    if (pointers.size === 1) gesture = {started: performance.now(), moved: 0, multi: false, center: centroid()};
    else { gesture.multi = true; gesture.center = centroid(); }
    pad.classList.add('is-touching');
    showPointer(event);
  });
  pad.addEventListener('pointermove', event => {
    const previous = pointers.get(event.pointerId);
    if (!previous || !gesture) return;
    event.preventDefault();
    const dx = event.clientX - previous.x, dy = event.clientY - previous.y;
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
    gesture.moved += Math.hypot(dx, dy);
    if (pointers.size >= 2) {
      const center = centroid();
      pendingScroll -= (center.y - gesture.center.y) / 24;
      gesture.center = center;
    } else if (!gesture.multi) {
      pendingX += dx * sensitivity; pendingY += dy * sensitivity;
    }
    scheduleMotion();
    showPointer(event);
  });
  function finishPointer(event, cancelled) {
    if (!pointers.has(event.pointerId)) return;
    pointers.delete(event.pointerId);
    if (pointers.size) { if (gesture) gesture.center = centroid(); return; }
    flushMotion();
    if (!cancelled && gesture && !gesture.multi && gesture.moved < 8 && performance.now() - gesture.started < 450 && !dragActive) sendQuietly({command: 'C'});
    gesture = null;
    pendingScroll = 0;
    pad.classList.remove('is-touching');
    $('touchIndicator').hidden = true;
  }
  pad.addEventListener('pointerup', event => finishPointer(event, false));
  pad.addEventListener('pointercancel', event => finishPointer(event, true));
  pad.addEventListener('lostpointercapture', event => finishPointer(event, true));
  pad.addEventListener('contextmenu', event => event.preventDefault());

  const scrollSurface = $('scrollSurface');
  function clearRailGesture(discard = true) {
    const previous = railPointer;
    railPointer = null;
    scrollSurface.classList.remove('active');
    if (previous && scrollSurface.hasPointerCapture(previous.id)) scrollSurface.releasePointerCapture(previous.id);
    if (discard) {
      pendingRailScroll = 0;
      for (let index = queue.length - 1; index >= 0; index--) {
        if (queue[index].kind === 'scroll' && queue[index].source === 'rail') queue.splice(index, 1);
      }
    }
  }
  scrollSurface.addEventListener('pointerdown', event => {
    event.preventDefault();
    event.stopPropagation();
    if (railPointer || (event.pointerType === 'mouse' && event.button !== 0)) return;
    if (!connected) { feedback('未连接', true); setConnectionPanel(true); return; }
    scrollSurface.setPointerCapture(event.pointerId);
    railPointer = {id: event.pointerId, y: event.clientY};
    scrollSurface.classList.add('active');
  });
  scrollSurface.addEventListener('pointermove', event => {
    if (!railPointer || railPointer.id !== event.pointerId) return;
    event.preventDefault();
    event.stopPropagation();
    pendingRailScroll -= (event.clientY - railPointer.y) / 20;
    railPointer.y = event.clientY;
    scheduleMotion();
  });
  scrollSurface.addEventListener('pointerup', event => {
    if (!railPointer || railPointer.id !== event.pointerId) return;
    event.stopPropagation();
    flushMotion();
    clearRailGesture(false);
  });
  scrollSurface.addEventListener('pointercancel', event => { if (railPointer && railPointer.id === event.pointerId) clearRailGesture(); });
  scrollSurface.addEventListener('lostpointercapture', event => { if (railPointer && railPointer.id === event.pointerId) clearRailGesture(); });
  scrollSurface.addEventListener('contextmenu', event => event.preventDefault());

  function setMode(nextMode, focusInput = false) {
    if (!['douyin', 'mouse', 'keyboard'].includes(nextMode)) nextMode = 'mouse';
    if (mode && mode !== nextMode) releaseDragOnLeave();
    mode = nextMode;
    storage.set('watchmouse_mode', mode);
    $('douyinPanel').hidden = mode !== 'douyin';
    $('mousePanel').hidden = mode === 'douyin';
    $('keyboardPanel').hidden = mode !== 'keyboard';
    document.body.classList.toggle('keyboard-visible', mode === 'keyboard');
    document.body.classList.toggle('mode-douyin', mode === 'douyin');
    document.querySelectorAll('[data-mode]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.mode === mode)));
    if (connected) feedback();
    if (mode !== 'keyboard') { $('textInput').blur(); if (speechListening && speech) speech.stop(); }
    else if (focusInput) {
      // Keep focus inside the trusted button click so Android can open its
      // native keyboard immediately, rather than after an animation callback.
      $('textInput').focus({preventScroll: true});
    }
  }
  document.querySelectorAll('[data-mode]').forEach(button => button.addEventListener('click', () => setMode(button.dataset.mode, true)));
  $('openPhoneKeyboard').addEventListener('click', () => $('textInput').focus());
  $('textInput').addEventListener('compositionstart', () => { composing = true; });
  $('textInput').addEventListener('compositionend', () => { composing = false; textFeedback(); });
  function updateDeleteLabel() {
    const hasDraft = $('textInput').value.length > 0;
    $('deleteTextButton').setAttribute('aria-label', hasDraft ? '删除草稿中光标左侧的文字或选中文字' : '在电脑当前窗口按退格，删除光标左侧文字');
  }
  $('textInput').addEventListener('input', () => { inputVersion++; updateDeleteLabel(); textFeedback(); });
  updateDeleteLabel();
  function previousCharacterRange(text, caret) {
    // Segment the complete string, so emoji families and combining marks are
    // removed together, even if a selection was placed inside a character.
    const segments = typeof Intl !== 'undefined' && Intl.Segmenter
      ? Array.from(new Intl.Segmenter('zh', {granularity: 'grapheme'}).segment(text), item => ({index: item.index, length: item.segment.length}))
      : Array.from(text).reduce((list, character) => {
          const index = list.length ? list[list.length - 1].index + list[list.length - 1].length : 0;
          list.push({index, length: character.length});
          return list;
        }, []);
    return segments.find(item => item.index < caret && item.index + item.length >= caret);
  }
  $('deleteTextButton').addEventListener('click', () => {
    const input = $('textInput');
    input.focus({preventScroll: true});
    if (composing || speechListening) {
      textFeedback(composing ? '请先完成选字' : '请先停止语音', true);
      return;
    }
    textFeedback();
    if (!input.value) {
      sendQuietly({key: 'backspace', modifiers: []});
      return;
    }
    let start = input.selectionStart, end = input.selectionEnd;
    if (start === end) {
      if (start === 0) { textFeedback(); return; }
      const range = previousCharacterRange(input.value, start);
      start = range.index;
      end = range.index + range.length;
    }
    input.setRangeText('', start, end, 'end');
    input.dispatchEvent(new Event('input', {bubbles: true}));
    textFeedback();
  });
  $('sendTextButton').addEventListener('click', async () => {
    const input = $('textInput');
    const text = input.value;
    if (composing) { textFeedback('请先完成选字', true); return; }
    if (speechListening) { textFeedback('请先停止语音', true); return; }
    if (!text) { input.focus(); textFeedback(); return; }
    const sentVersion = inputVersion;
    $('sendTextButton').disabled = true;
    textFeedback();
    try {
      await send({text});
      if (inputVersion === sentVersion && input.value === text) { input.value = ''; inputVersion++; updateDeleteLabel(); }
      textFeedback();
    } catch (error) {
      textFeedback(errorMessage(error), true);
    } finally { $('sendTextButton').disabled = false; }
  });

  // Plain LAN HTTP uses the phone keyboard's own dictation. The optional
  // browser speech button is offered only in a supported secure context.
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (window.isSecureContext && Recognition) {
    $('speechButton').hidden = false;
    speech = new Recognition();
    speech.lang = 'zh-CN';
    speech.continuous = false;
    speech.interimResults = true;
    let startingText = '';
    speech.onstart = () => { speechListening = true; $('speechButton').textContent = '■'; $('speechButton').setAttribute('aria-label', '停止语音'); textFeedback(); };
    speech.onresult = event => {
      const transcript = Array.from(event.results).map(result => result[0].transcript).join('');
      $('textInput').value = (startingText + transcript).slice(0, 4000);
      inputVersion++;
      updateDeleteLabel();
    };
    speech.onend = () => { speechListening = false; $('speechButton').textContent = '🎙'; $('speechButton').setAttribute('aria-label', '浏览器语音输入'); };
    speech.onerror = () => { speechListening = false; $('speechButton').textContent = '🎙'; $('speechButton').setAttribute('aria-label', '浏览器语音输入'); textFeedback('语音不可用', true); };
    $('speechButton').addEventListener('click', () => {
      if (speechListening) { speech.stop(); return; }
      startingText = $('textInput').value;
      try { speech.start(); } catch (_) { textFeedback('语音不可用', true); }
    });
  }

  function releaseDragOnLeave() {
    // Best-effort release before the browser suspends the page. The receiver
    // also releases a held button when its session times out.
    if (dragActive) {
      flushMotion();
      // Keep an ordered release in the queue as well, so an in-flight MD
      // cannot leave the button held after the best-effort beacon arrives.
      sendQuietly({command: 'MU'});
      try { navigator.sendBeacon('/api/command', new Blob([JSON.stringify({token, command: 'MU'})], {type: 'application/json'})); } catch (_) {}
      dragActive = false;
      updateDragUI();
    }
    if (motionTimer) { clearTimeout(motionTimer); motionTimer = null; }
    pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
    clearRailGesture();
    for (let index = queue.length - 1; index >= 0; index--) {
      if (queue[index].kind === 'move' || queue[index].kind === 'scroll') queue.splice(index, 1);
    }
    pointers.clear(); gesture = null;
    pad.classList.remove('is-touching');
    $('touchIndicator').hidden = true;
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) releaseDragOnLeave();
    else checkConnection();
  });
  window.addEventListener('pagehide', releaseDragOnLeave);
  window.addEventListener('blur', releaseDragOnLeave);
  window.addEventListener('online', checkConnection);
  window.addEventListener('offline', () => { setConnection(false, '网络断开'); feedback(); });
  function syncViewport() {
    const viewport = window.visualViewport;
    const height = viewport ? viewport.height : window.innerHeight;
    const offset = viewport ? Math.max(0, viewport.offsetTop || 0) : 0;
    if (Number.isFinite(height) && height > 0) document.documentElement.style.setProperty('--viewport-height', height + 'px');
    document.documentElement.style.setProperty('--viewport-offset', offset + 'px');
    document.body.classList.toggle('compact-viewport', height < 300);
  }
  function viewportChanged() { releaseDragOnLeave(); syncViewport(); }
  window.addEventListener('resize', viewportChanged);
  window.addEventListener('orientationchange', viewportChanged);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', viewportChanged);
    window.visualViewport.addEventListener('scroll', viewportChanged);
  }
  setInterval(() => {
    if (dragActive && connected && !document.hidden) sendQuietly({command: 'MD'});
  }, 2000);
  syncViewport();
  setMode(savedMode);
  checkConnection();
})();
