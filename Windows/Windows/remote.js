(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch (_) { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); } catch (_) {} }
  };
  const messages = {
    en: {
      watch: 'Watch ↗', left: 'Left', drag: 'Drag', right: 'Right', connect: 'Connect', speed: 'Speed',
      video: 'Video', mouse: 'Mouse', keyboard: 'Keyboard', language: 'Language', interfaceLanguage: 'Interface language',
      videoControls: 'Video controls', previousVideo: 'Previous video', playPause: 'Play or pause', nextVideo: 'Next video',
      mouseControls: 'Mouse controls', touchpad: 'Touchpad: move with one finger, tap to click, scroll with two fingers',
      leftClick: 'Left click', rightClick: 'Right click', dragOff: 'Drag: hold the left mouse button',
      dragOn: 'Drag active: release the left mouse button', scroll: 'Scroll', scrollUp: 'Scroll up', scrollDown: 'Scroll down',
      scrollSurface: 'Slide one finger up or down to scroll', phoneInput: 'Phone input', type: 'Type…', draft: 'Text draft',
      speech: 'Browser dictation', stopSpeech: 'Stop dictation', sendDraft: 'Send draft to computer',
      commonActions: 'Common actions', backspace: 'Computer backspace', space: 'Computer space', enter: 'Computer Enter',
      phoneKeyboard: 'Open phone keyboard', connectionSettings: 'Connection settings', pairingCode: 'Pairing code',
      mouseSpeed: 'Mouse movement speed', controlMode: 'Control mode', connectingSettings: 'Connecting; open connection settings',
      connectedSettings: 'Connected; open connection settings', disconnectedSettings: 'Disconnected; open connection settings',
      invalid_token: 'Invalid pairing code. Check the code in the receiver.', enterPairing: 'Enter the pairing code from the receiver.',
      input_unavailable: 'The computer did not accept input.', invalid_request: 'Unable to perform this action.',
      accessibility_permission: 'Allow WatchMouse in Mac System Settings → Privacy & Security → Accessibility.',
      accessibility_relaunch: 'Add the current WatchMouse app in Mac Accessibility settings, enable it, then reopen WatchMouse.',
      windows_elevation: 'Windows did not accept input. Check whether the target app is running as administrator.',
      timeout: 'Connection timed out. Retrying…', disconnected: 'Connection lost. Retrying…',
      networkOffline: 'Network disconnected. Reconnect to Wi-Fi.', invalidAddress: 'This address is not a WatchMouse receiver.',
      invalidResponse: 'Invalid response from the receiver.', notConnected: 'Not connected.',
      inputPermission: 'Enable input permission on the computer.', finishComposition: 'Finish choosing the current character first.',
      stopSpeechFirst: 'Stop dictation first.', speechUnavailable: 'Browser dictation is unavailable.',
      deleteDraft: 'Delete selected text or the character before the cursor in the draft',
      deleteComputer: 'Press Backspace in the current computer window'
    },
    zh: {
      watch: '手表 ↗', left: '左键', drag: '拖动', right: '右键', connect: '连接', speed: '速度',
      video: '视频', mouse: '鼠标', keyboard: '键鼠', language: '语言', interfaceLanguage: '界面语言',
      videoControls: '视频遥控', previousVideo: '上一个视频', playPause: '播放或暂停', nextVideo: '下一个视频',
      mouseControls: '鼠标控制', touchpad: '触控板：单指移动，轻点单击，双指滚动', leftClick: '鼠标左键', rightClick: '鼠标右键',
      dragOff: '拖动，点击按住左键', dragOn: '拖动已开启，点击松开左键', scroll: '滚轮', scrollUp: '向上滚动', scrollDown: '向下滚动',
      scrollSurface: '单指上下滑动滚动页面', phoneInput: '手机输入', type: '输入…', draft: '输入草稿',
      speech: '浏览器语音输入', stopSpeech: '停止语音', sendDraft: '发送草稿到电脑', commonActions: '常用操作',
      backspace: '电脑退格', space: '电脑空格', enter: '电脑回车', phoneKeyboard: '打开手机键盘',
      connectionSettings: '连接设置', pairingCode: '配对码', mouseSpeed: '鼠标移动速度', controlMode: '遥控模式',
      connectingSettings: '正在连接，打开连接设置', connectedSettings: '已连接，打开连接设置', disconnectedSettings: '未连接，打开连接设置',
      invalid_token: '配对码无效，请核对接收器中的配对码', enterPairing: '请输入接收器中的配对码',
      input_unavailable: '电脑未接收输入', invalid_request: '操作失败',
      accessibility_permission: '请在 Mac 系统设置 → 隐私与安全性 → 辅助功能中允许 WatchMouse',
      accessibility_relaunch: '请在 Mac 辅助功能设置中添加当前 WatchMouse，开启权限后重新打开应用',
      windows_elevation: 'Windows 未接受输入。请确认目标窗口没有以管理员身份运行。',
      timeout: '连接超时，正在重试…', disconnected: '连接断开，正在重试…', networkOffline: '网络断开，请重新连接 Wi-Fi',
      invalidAddress: '此地址不是 WatchMouse 接收器', invalidResponse: '接收器响应异常', notConnected: '未连接',
      inputPermission: '电脑输入权限未开启', finishComposition: '请先完成选字', stopSpeechFirst: '请先停止语音',
      speechUnavailable: '语音不可用', deleteDraft: '删除草稿中光标左侧的文字或选中文字',
      deleteComputer: '在电脑当前窗口按退格，删除光标左侧文字'
    }
  };
  let language = storage.get('watchmouse_language') === 'zh' ? 'zh' : 'en';
  const t = key => messages[language][key] || messages[language].invalid_request;
  const localError = key => Object.assign(new Error(t(key)), {errorCode: key});
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
  let statusInFlight = false;
  let statusCheckQueued = false;
  let statusTimer = null;
  let reconnectFailures = 0;
  let retryBlocked = false;
  let inputEpoch = 0;
  let connectionState = 'connecting';
  let connectionMessageKey = '';
  let actionMessageKey = '', actionError = false;
  let textMessageKey = '', textError = false;
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
    $('watchLink').href = '/watch?lang=' + (language === 'zh' ? 'zh-CN' : 'en') + (token ? '&token=' + encodeURIComponent(token) : '');
  }
  refreshWatchLink();

  function renderConnection() {
    $('statusDot').className = 'status-dot ' + (connectionState === 'connected' ? 'connected' : connectionState === 'connecting' ? '' : 'error');
    $('connectionButton').setAttribute('aria-label', t(connectionState + 'Settings'));
    $('connectionMessage').textContent = connectionMessageKey ? t(connectionMessageKey) : '';
  }
  function feedback(key = '', error = false) {
    actionMessageKey = key; actionError = error;
    $('actionFeedback').textContent = error && key ? t(key) : '';
    $('actionFeedback').classList.toggle('error', error);
    $('actionFeedback').classList.toggle('visually-hidden', !error);
  }
  function textFeedback(key = '', error = false) {
    textMessageKey = key; textError = error;
    $('textFeedback').textContent = error && key ? t(key) : '';
    $('textFeedback').classList.toggle('error', error);
    $('textFeedback').classList.toggle('visually-hidden', !error);
  }
  function applyLanguage() {
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(element => { element.textContent = t(element.dataset.i18n); });
    document.querySelectorAll('[data-i18n-aria]').forEach(element => { element.setAttribute('aria-label', t(element.dataset.i18nAria)); });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => { element.setAttribute('placeholder', t(element.dataset.i18nPlaceholder)); });
    $('languageSelect').value = language;
    refreshWatchLink();
    renderConnection(); updateDragUI(); updateDeleteLabel();
    feedback(actionMessageKey, actionError); textFeedback(textMessageKey, textError);
    if (speech) {
      speech.lang = language === 'zh' ? 'zh-CN' : 'en-US';
      $('speechButton').setAttribute('aria-label', t(speechListening ? 'stopSpeech' : 'speech'));
    }
  }
  $('languageSelect').addEventListener('change', event => {
    language = event.target.value === 'zh' ? 'zh' : 'en';
    storage.set('watchmouse_language', language);
    if (speechListening && speech) speech.stop();
    applyLanguage();
  });
  function discardInput(messageKey = 'notConnected') {
    inputEpoch++;
    while (queue.length) {
      const item = queue.shift();
      if (item.reject) item.reject(localError(messageKey));
    }
    if (motionTimer) { clearTimeout(motionTimer); motionTimer = null; }
    pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
    clearRailGesture();
    pointers.clear(); gesture = null;
    $('touchpad').classList.remove('is-touching');
    $('touchIndicator').hidden = true;
    dragActive = false; updateDragUI();
  }
  function setConnection(ok, messageKey = '') {
    connected = ok;
    connectionState = ok ? 'connected' : 'disconnected';
    connectionMessageKey = ok ? '' : messageKey;
    renderConnection();
    if (!ok) { discardInput(messageKey); setConnectionPanel(true); }
  }
  function setConnectionPanel(open) {
    $('connectionPanel').hidden = !open;
    $('connectionButton').setAttribute('aria-expanded', String(open));
  }
  function serverErrorKey(code, message, fallback = 'input_unavailable') {
    if (code && Object.prototype.hasOwnProperty.call(messages.en, code)) return code;
    // Older receivers report Chinese messages; normalize known cases instead
    // of showing untranslated server strings or untrusted error details.
    if (/管理员|administrator/i.test(message || '')) return 'windows_elevation';
    if (/辅助功能|Accessibility/i.test(message || '')) {
      return /重新|重启|reopen|relaunch/i.test(message || '') ? 'accessibility_relaunch' : 'accessibility_permission';
    }
    return fallback;
  }
  function errorMessage(error) {
    if (error.status === 401 || error.status === 403) return 'invalid_token';
    if (error.status === 409) return serverErrorKey(error.errorCode, error.message);
    if (error.status === 400) return 'invalid_request';
    if (error.name === 'AbortError') return 'timeout';
    return serverErrorKey(error.errorCode, error.message, 'invalid_request');
  }
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 7000);
    try {
      const response = await fetch(path, {cache: 'no-store', ...options, signal: controller.signal});
      let result;
      try { result = await response.json(); } catch (_) { throw localError('invalidResponse'); }
      if (!response.ok || result.ok === false) {
        const error = new Error(result.error || '');
        error.status = response.status;
        error.errorCode = result.errorCode;
        throw error;
      }
      return result;
    } catch (error) {
      if (error instanceof TypeError) throw localError('disconnected');
      throw error;
    } finally { clearTimeout(timeout); }
  }
  function cancelStatusTimer() { if (statusTimer) { clearTimeout(statusTimer); statusTimer = null; } }
  function scheduleConnectionCheck() {
    cancelStatusTimer();
    if (retryBlocked || document.hidden || navigator.onLine === false) return;
    // Poll gently when healthy and back off to a bounded rate while the
    // receiver restarts. Never replay input accumulated during a disconnect.
    const delay = connected ? 5000 : Math.min(15000, 1000 * 2 ** Math.min(reconnectFailures, 4));
    statusTimer = setTimeout(() => { statusTimer = null; checkConnection(); }, delay);
  }
  async function checkConnection(manual = false) {
    cancelStatusTimer();
    if (manual) { retryBlocked = false; reconnectFailures = 0; }
    if (retryBlocked || document.hidden || navigator.onLine === false) return;
    if (statusInFlight) { statusCheckQueued = true; return; }
    statusInFlight = true;
    const version = ++statusVersion, requestedToken = token, wasConnected = connected;
    if (!connected) { connectionState = 'connecting'; renderConnection(); }
    $('pairButton').disabled = true;
    try {
      const result = await request('/api/status' + (requestedToken ? '?token=' + encodeURIComponent(requestedToken) : ''), {headers: requestedToken ? {'X-WatchMouse-Token': requestedToken} : {}});
      if (version !== statusVersion || requestedToken !== token) return;
      if (result.app !== 'WatchMouse') { retryBlocked = true; throw localError('invalidAddress'); }
      if (!result.paired) {
        retryBlocked = true;
        setConnection(false, token ? 'invalid_token' : 'enterPairing');
        feedback();
        return;
      }
      storage.set('watchmouse_token', token);
      if (result.inputReady === false) {
        const key = serverErrorKey(result.inputErrorCode, result.inputError, 'inputPermission');
        setConnection(false, key); feedback(key, true);
        reconnectFailures++;
        return;
      }
      reconnectFailures = 0;
      setConnection(true);
      if (!wasConnected || manual) setConnectionPanel(false);
      feedback();
    } catch (error) {
      if (version !== statusVersion || requestedToken !== token) return;
      const key = errorMessage(error);
      if (key === 'invalid_token') retryBlocked = true;
      reconnectFailures++;
      setConnection(false, key); feedback();
    } finally {
      statusInFlight = false;
      $('pairButton').disabled = false;
      if (statusCheckQueued) { statusCheckQueued = false; checkConnection(); }
      else scheduleConnectionCheck();
    }
  }

  // Serialize input and merge adjacent motion packets to preserve distance
  // without issuing a network request for every touch sample.
  function enqueue(item) {
    if (!connected) {
      if (item.reject) item.reject(localError('notConnected'));
      feedback('notConnected', true);
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
        const epoch = inputEpoch;
        try {
          await request('/api/command', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': token}, body: JSON.stringify({...payload, token})});
          if (epoch !== inputEpoch) { if (item.reject) item.reject(localError('notConnected')); continue; }
          if (item.resolve) item.resolve();
          feedback();
        } catch (error) {
          if (item.reject) item.reject(error);
          if (epoch !== inputEpoch) continue;
          while (queue.length) {
            const dropped = queue.shift();
            if (dropped.reject) dropped.reject(error);
          }
          pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
          const message = errorMessage(error);
          statusVersion++;
          setConnection(false, message);
          feedback(message, true);
          if (message === 'invalid_token') retryBlocked = true;
          reconnectFailures = 0;
          scheduleConnectionCheck();
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
    const nextToken = $('pairingCode').value.trim();
    if (nextToken !== token) { statusVersion++; setConnection(false, 'notConnected'); }
    token = nextToken;
    refreshWatchLink();
    checkConnection(true);
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
    $('dragButton').setAttribute('aria-label', t(dragActive ? 'dragOn' : 'dragOff'));
    $('touchpad').classList.toggle('dragging', dragActive);
  }
  $('dragButton').addEventListener('click', () => {
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
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
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
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
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
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
    $('deleteTextButton').setAttribute('aria-label', t(hasDraft ? 'deleteDraft' : 'deleteComputer'));
  }
  $('textInput').addEventListener('input', () => { inputVersion++; updateDeleteLabel(); textFeedback(); });
  updateDeleteLabel();
  function previousCharacterRange(text, caret) {
    // Segment the complete string, so emoji families and combining marks are
    // removed together, even if a selection was placed inside a character.
    const segments = typeof Intl !== 'undefined' && Intl.Segmenter
      ? Array.from(new Intl.Segmenter(language, {granularity: 'grapheme'}).segment(text), item => ({index: item.index, length: item.segment.length}))
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
      textFeedback(composing ? 'finishComposition' : 'stopSpeechFirst', true);
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
    if (composing) { textFeedback('finishComposition', true); return; }
    if (speechListening) { textFeedback('stopSpeechFirst', true); return; }
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
    speech.lang = language === 'zh' ? 'zh-CN' : 'en-US';
    speech.continuous = false;
    speech.interimResults = true;
    let startingText = '';
    speech.onstart = () => { speechListening = true; $('speechButton').textContent = '■'; $('speechButton').setAttribute('aria-label', t('stopSpeech')); textFeedback(); };
    speech.onresult = event => {
      const transcript = Array.from(event.results).map(result => result[0].transcript).join('');
      $('textInput').value = (startingText + transcript).slice(0, 4000);
      inputVersion++;
      updateDeleteLabel();
    };
    speech.onend = () => { speechListening = false; $('speechButton').textContent = '🎙'; $('speechButton').setAttribute('aria-label', t('speech')); };
    speech.onerror = () => { speechListening = false; $('speechButton').textContent = '🎙'; $('speechButton').setAttribute('aria-label', t('speech')); textFeedback('speechUnavailable', true); };
    $('speechButton').addEventListener('click', () => {
      if (speechListening) { speech.stop(); return; }
      startingText = $('textInput').value;
      try { speech.start(); } catch (_) { textFeedback('speechUnavailable', true); }
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
    if (document.hidden) { cancelStatusTimer(); statusVersion++; releaseDragOnLeave(); discardInput(); }
    else checkConnection();
  });
  window.addEventListener('pagehide', releaseDragOnLeave);
  window.addEventListener('blur', releaseDragOnLeave);
  window.addEventListener('online', () => checkConnection());
  window.addEventListener('offline', () => { cancelStatusTimer(); statusVersion++; setConnection(false, 'networkOffline'); feedback(); });
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
  applyLanguage();
  checkConnection();
})();
