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
      video: 'Video', mouse: 'Mouse', gamepad: 'Pad', keyboard: 'Keyboard', language: 'Language', interfaceLanguage: 'Interface language',
      videoControls: 'Video controls', previousVideo: 'Previous video', playPause: 'Play or pause', nextVideo: 'Next video',
      gamepadControls: 'Gamepad controls', gamepadLayout: 'Gamepad layout', gamepadHint: 'Buttons map to keyboard keys for games that support them',
      leftStick: 'Left stick', rightStick: 'Right stick', dpad: 'D-pad', faceButtons: 'Face buttons',
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
      deleteComputer: 'Press Backspace in the current computer window', queueBusy: 'Input queue is busy. Try again shortly.'
    },
    zh: {
      watch: '手表 ↗', left: '左键', drag: '拖动', right: '右键', connect: '连接', speed: '速度',
      video: '抖音', mouse: '鼠标', gamepad: '手柄', keyboard: '键鼠', language: '语言', interfaceLanguage: '界面语言',
      videoControls: '视频遥控', previousVideo: '上一个视频', playPause: '播放或暂停', nextVideo: '下一个视频',
      gamepadControls: '手柄控制', gamepadLayout: '手柄布局', gamepadHint: '按键映射为键盘，适合支持键鼠的游戏',
      leftStick: '左摇杆', rightStick: '右摇杆', dpad: '方向键', faceButtons: '功能键',
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
      deleteComputer: '在电脑当前窗口按退格，删除光标左侧文字', queueBusy: '操作排队中，请稍后再试'
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
  let statusController = null;
  let dragHeartbeatTimer = null;
  let dragMayBeHeld = false;
  let dragToken = '';
  let lastInputAck = 0;
  let inFlightCommand = '';
  let inFlightToken = '';
  let releaseBeaconSent = false;
  let padRect = null;
  let indicatorPoint = null;
  let indicatorFrame = null;
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
      $('speechButton').setAttribute('aria-label', t(speechListening ? 'stopSpeech' : 'speech'));
    }
  }
  $('languageSelect').addEventListener('change', event => {
    language = event.target.value === 'zh' ? 'zh' : 'en';
    storage.set('watchmouse_language', language);
    applyLanguage();
  });
  function discardInput(messageKey = 'notConnected', preserveRelease = false) {
    inputEpoch++;
    const releases = [];
    while (queue.length) {
      const item = queue.shift();
      // Only the ordered mouse-up may survive hidden-page cleanup. It must
      // follow an in-flight mouse-down even if the beacon reaches the receiver
      // first; clicks, text, keys and motion are always discarded.
      if ((preserveRelease || item.safeRelease) && item.kind === 'command' && item.payload.command === 'MU' && Object.keys(item.payload).length === 1) {
        item.safeRelease = true;
        if (!releases.some(release => release.token === item.token)) releases.push(item);
      }
      else if (item.reject) item.reject(localError(messageKey));
    }
    queue.push(...releases);
    if (motionTimer) { clearTimeout(motionTimer); motionTimer = null; }
    pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
    clearRailGesture();
    pointers.clear(); gesture = null;
    cancelIndicator();
    $('touchpad').classList.remove('is-touching');
    $('touchIndicator').hidden = true;
    dragActive = false; updateDragUI();
  }
  function setConnection(ok, messageKey = '') {
    connected = ok;
    connectionState = ok ? 'connected' : 'disconnected';
    connectionMessageKey = ok ? '' : messageKey;
    renderConnection();
    if (!ok) {
      if (dragMayBeHeld) { releaseBeacon(); enqueueRelease(); }
      discardInput(messageKey); setConnectionPanel(true);
    }
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
  async function request(path, options = {}, controller = new AbortController(), timeoutMs = 7000) {
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
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
    statusTimer = setTimeout(() => {
      statusTimer = null;
      // Command acknowledgements already validate an active session. Avoid
      // an extra status request competing with continuous touch input.
      if (connected && (draining || pointers.size || railPointer)) scheduleConnectionCheck();
      else checkConnection();
    }, delay);
  }
  async function checkConnection(manual = false) {
    cancelStatusTimer();
    if (manual) { retryBlocked = false; reconnectFailures = 0; }
    if (retryBlocked || document.hidden || navigator.onLine === false) return;
    if (statusInFlight) { statusCheckQueued = true; return; }
    statusInFlight = true;
    const controller = new AbortController();
    statusController = controller;
    const version = ++statusVersion, requestedToken = token, wasConnected = connected;
    if (!connected) { connectionState = 'connecting'; renderConnection(); }
    $('pairButton').disabled = true;
    try {
      const result = await request('/api/status' + (requestedToken ? '?token=' + encodeURIComponent(requestedToken) : ''), {headers: requestedToken ? {'X-WatchMouse-Token': requestedToken} : {}}, controller, 4000);
      if (version !== statusVersion || requestedToken !== token) return;
      if (result.app !== 'WatchMouse') { retryBlocked = true; throw localError('invalidAddress'); }
      if (!result.paired) {
        retryBlocked = true;
        setConnection(false, token ? 'invalid_token' : 'enterPairing');
        feedback();
        return;
      }
      storage.set('watchmouse_token', token);
      // A manually corrected key must also replace an old QR key in the URL;
      // otherwise reloading or bookmarking the page restores the stale key.
      try {
        const pairedUrl = new URL(location.href);
        pairedUrl.searchParams.set('token', token);
        if (window.history && typeof window.history.replaceState === 'function') {
          window.history.replaceState(null, '', pairedUrl.href);
        }
      } catch (_) {}
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
      if (statusController === controller) statusController = null;
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
    // Bound discrete actions under a slow connection. Never silently drop an
    // accepted click/text action, and never let this limit block mouse-up.
    if (item.kind === 'command' && item.payload.command !== 'MU' && !item.safeRelease && queue.filter(entry => entry.kind === 'command' && !entry.safeRelease).length >= 32) {
      if (item.reject) item.reject(localError('queueBusy'));
      feedback('queueBusy', true);
      return;
    }
    item.token = token;
    const last = queue[queue.length - 1];
    if (last && last.token === item.token && item.kind === last.kind && (item.kind === 'move' || (item.kind === 'scroll' && item.source === last.source))) {
      if (item.kind === 'move') { last.x += item.x; last.y += item.y; }
      else last.amount += item.amount;
    } else queue.push(item);
    drain();
  }
  function enqueueRelease() {
    const releaseToken = dragToken || token;
    if (inFlightCommand === 'MU' && inFlightToken === releaseToken) return;
    const existing = queue.find(item => item.kind === 'command' && item.payload.command === 'MU' && item.token === releaseToken);
    if (existing) { existing.safeRelease = true; return; }
    // Mouse-up / held-key release is allowed after a disconnect. Retain its
    // original token and order behind an in-flight MD; never re-send any input.
    queue.push({kind: 'command', payload: {command: 'MU'}, token: releaseToken, safeRelease: true});
    drain();
  }
  async function drain() {
    if (draining) return;
    draining = true;
    try {
      while (queue.length && (connected || queue[0].safeRelease)) {
        const item = queue.shift();
        let payload = item.payload;
        if (item.kind === 'move') {
          const x = Math.max(-4096, Math.min(4096, item.x)), y = Math.max(-4096, Math.min(4096, item.y));
          if (x !== item.x || y !== item.y) queue.unshift({kind: 'move', x: item.x - x, y: item.y - y, token: item.token});
          if (!x && !y) continue;
          payload = {command: 'M ' + x + ',' + y};
        }
        if (item.kind === 'scroll') {
          const amount = Math.max(-100, Math.min(100, item.amount));
          if (amount !== item.amount) queue.unshift({kind: 'scroll', amount: item.amount - amount, source: item.source, token: item.token});
          if (!amount) continue;
          payload = {command: 'S ' + amount};
        }
        const epoch = inputEpoch;
        inFlightCommand = payload.command || '';
        inFlightToken = item.token;
        if (payload.command === 'MD') { dragMayBeHeld = true; dragToken = item.token; releaseBeaconSent = false; }
        try {
          await request('/api/command', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': item.token}, body: JSON.stringify({...payload, token: item.token})});
          lastInputAck = performance.now();
          if (['MU', 'C', 'RC'].includes(payload.command)) dragMayBeHeld = false;
          // An ACK still confirms execution if the page became hidden while
          // this request was in flight. Resolve it without replaying anything.
          if (item.resolve) item.resolve();
          if (epoch !== inputEpoch) continue;
          feedback();
          // While a request is in flight keep motion in three accumulators,
          // then materialize one following batch rather than a timer backlog.
          if (!queue.length) flushMotion();
        } catch (error) {
          if (item.reject) item.reject(error);
          // A failed safety release is not automatically replayed. The beacon
          // and receiver's drag timeout remain the bounded fallback.
          if (item.safeRelease) { dragMayBeHeld = false; continue; }
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
        } finally { inFlightCommand = ''; inFlightToken = ''; }
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
  function scheduleMotion() { if (!draining && !motionTimer) motionTimer = setTimeout(flushMotion, 16); }
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
    maintainDragHeartbeat();
  }
  function maintainDragHeartbeat() {
    if (dragHeartbeatTimer) { clearTimeout(dragHeartbeatTimer); dragHeartbeatTimer = null; }
    if (!dragActive || !connected || document.hidden) return;
    dragHeartbeatTimer = setTimeout(() => {
      dragHeartbeatTimer = null;
      if (dragActive && connected && !document.hidden && !draining && performance.now() - lastInputAck >= 1500) sendQuietly({command: 'MD'});
      maintainDragHeartbeat();
    }, 2000);
  }
  $('dragButton').addEventListener('click', () => {
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
    dragActive = !dragActive;
    updateDragUI();
    sendQuietly({command: dragActive ? 'MD' : 'MU'});
  });

  const pad = $('touchpad');
  function cancelIndicator() {
    if (indicatorFrame !== null) { cancelAnimationFrame(indicatorFrame); indicatorFrame = null; }
    indicatorPoint = null; padRect = null;
  }
  function showPointer(event) {
    indicatorPoint = {x: event.clientX, y: event.clientY};
    if (indicatorFrame !== null || document.hidden) return;
    indicatorFrame = requestAnimationFrame(() => {
      indicatorFrame = null;
      if (!indicatorPoint || !padRect || !pointers.size || document.hidden) return;
      $('touchIndicator').style.left = (indicatorPoint.x - padRect.left) + 'px';
      $('touchIndicator').style.top = (indicatorPoint.y - padRect.top) + 'px';
      $('touchIndicator').hidden = false;
    });
  }
  function centroid() {
    let x = 0, y = 0;
    for (const point of pointers.values()) { x += point.x; y += point.y; }
    return {x: x / pointers.size, y: y / pointers.size};
  }
  pad.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
    pad.setPointerCapture(event.pointerId);
    padRect = pad.getBoundingClientRect();
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY});
    if (pointers.size === 1) gesture = {started: performance.now(), moved: 0, multi: false, center: centroid()};
    else { gesture.multi = true; gesture.center = centroid(); }
    pad.classList.add('is-touching');
    showPointer(event);
  });
  function movePointer(event) {
    const previous = pointers.get(event.pointerId);
    if (!previous || !gesture || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return;
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
  }
  pad.addEventListener('pointermove', event => { event.preventDefault(); movePointer(event); });
  function finishPointer(event, cancelled) {
    if (!pointers.has(event.pointerId)) return;
    if (!cancelled) movePointer(event);
    pointers.delete(event.pointerId);
    if (pointers.size) { if (gesture) gesture.center = centroid(); return; }
    flushMotion();
    if (!cancelled && gesture && !gesture.multi && gesture.moved < 8 && performance.now() - gesture.started < 450 && !dragActive) sendQuietly({command: 'C'});
    gesture = null;
    pendingScroll = 0;
    pad.classList.remove('is-touching');
    cancelIndicator();
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
    if (Number.isFinite(event.clientY)) pendingRailScroll -= (event.clientY - railPointer.y) / 20;
    flushMotion();
    clearRailGesture(false);
  });
  scrollSurface.addEventListener('pointercancel', event => { if (railPointer && railPointer.id === event.pointerId) clearRailGesture(); });
  scrollSurface.addEventListener('lostpointercapture', event => { if (railPointer && railPointer.id === event.pointerId) clearRailGesture(); });
  scrollSurface.addEventListener('contextmenu', event => event.preventDefault());

  const PAD_KEYS = {
    lt: '1', lb: 'q', rb: 'r', rt: '2', select: 'tab', start: 'enter',
    a: 'space', b: 'escape', x: 'f', y: 'e',
    dup: 'w', ddown: 's', dleft: 'a', dright: 'd'
  };
  const STICK_KEYS = {
    left: {up: 'w', down: 's', left: 'a', right: 'd'},
    right: {up: 'up', down: 'down', left: 'left', right: 'right'}
  };
  const heldPadKeys = new Map();
  const stickPointers = new Map();
  const stickHeld = {left: new Set(), right: new Set()};
  let gamepadLayout = storage.get('watchmouse_pad_layout') === 'ps' ? 'ps' : 'xbox';

  function holdPadKey(name) {
    const count = heldPadKeys.get(name) || 0;
    heldPadKeys.set(name, count + 1);
    if (!count) sendQuietly({key: name, state: 'down'});
  }
  function releasePadKey(name) {
    const count = heldPadKeys.get(name) || 0;
    if (count <= 1) {
      heldPadKeys.delete(name);
      if (count === 1) sendQuietly({key: name, state: 'up'});
      return;
    }
    heldPadKeys.set(name, count - 1);
  }
  function syncStickKeys(side, nextKeys) {
    const previous = stickHeld[side];
    for (const name of previous) if (!nextKeys.has(name)) releasePadKey(name);
    for (const name of nextKeys) if (!previous.has(name)) holdPadKey(name);
    stickHeld[side] = nextKeys;
  }
  function keysFromStick(side, nx, ny) {
    const map = STICK_KEYS[side];
    const next = new Set();
    const dead = 0.32;
    if (ny <= -dead) next.add(map.up);
    if (ny >= dead) next.add(map.down);
    if (nx <= -dead) next.add(map.left);
    if (nx >= dead) next.add(map.right);
    return next;
  }
  function resetStickVisual(stick) {
    const knob = stick.querySelector('.stick-knob');
    if (knob) knob.style.transform = 'translate(-50%, -50%)';
    stick.classList.remove('active');
  }
  function clearGamepadUi() {
    document.querySelectorAll('#gamepadPanel .is-pressed').forEach(button => button.classList.remove('is-pressed'));
    document.querySelectorAll('#gamepadPanel .stick').forEach(resetStickVisual);
  }
  function releaseGamepadControls(sendServer = true) {
    const hadKeys = heldPadKeys.size > 0;
    heldPadKeys.clear();
    stickHeld.left = new Set();
    stickHeld.right = new Set();
    for (const [pointerId, state] of stickPointers) {
      if (state.stick.hasPointerCapture(pointerId)) state.stick.releasePointerCapture(pointerId);
    }
    stickPointers.clear();
    clearGamepadUi();
    if (hadKeys && sendServer) enqueueRelease();
  }
  function setGamepadLayout(layout) {
    gamepadLayout = layout === 'ps' ? 'ps' : 'xbox';
    storage.set('watchmouse_pad_layout', gamepadLayout);
    $('gamepadPanel').dataset.layout = gamepadLayout;
    $('xboxLayoutButton').setAttribute('aria-pressed', String(gamepadLayout === 'xbox'));
    $('psLayoutButton').setAttribute('aria-pressed', String(gamepadLayout === 'ps'));
  }
  setGamepadLayout(gamepadLayout);
  document.querySelectorAll('[data-layout]').forEach(button => {
    if (!button.closest('.layout-switcher')) return;
    button.addEventListener('click', () => setGamepadLayout(button.dataset.layout));
  });
  document.querySelectorAll('#gamepadPanel [data-pad]').forEach(button => {
    const bind = event => {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      const name = PAD_KEYS[button.dataset.pad];
      if (!name || button.classList.contains('is-pressed')) return;
      button.classList.add('is-pressed');
      try { button.setPointerCapture(event.pointerId); } catch (_) {}
      holdPadKey(name);
    };
    const unbind = event => {
      if (!button.classList.contains('is-pressed')) return;
      button.classList.remove('is-pressed');
      const name = PAD_KEYS[button.dataset.pad];
      if (name) releasePadKey(name);
      try { if (button.hasPointerCapture(event.pointerId)) button.releasePointerCapture(event.pointerId); } catch (_) {}
    };
    button.addEventListener('pointerdown', bind);
    button.addEventListener('pointerup', unbind);
    button.addEventListener('pointercancel', unbind);
    button.addEventListener('lostpointercapture', unbind);
    button.addEventListener('contextmenu', event => event.preventDefault());
  });
  document.querySelectorAll('#gamepadPanel .stick').forEach(stick => {
    const side = stick.dataset.stick;
    const knob = stick.querySelector('.stick-knob');
    stick.addEventListener('pointerdown', event => {
      if (event.button !== undefined && event.button !== 0) return;
      event.preventDefault();
      stickPointers.set(event.pointerId, {stick, side});
      stick.setPointerCapture(event.pointerId);
      stick.classList.add('active');
      moveStick(event);
    });
    function moveStick(event) {
      if (!stickPointers.has(event.pointerId)) return;
      const rect = stick.getBoundingClientRect();
      const radius = Math.min(rect.width, rect.height) / 2;
      let nx = (event.clientX - (rect.left + radius)) / radius;
      let ny = (event.clientY - (rect.top + radius)) / radius;
      const magnitude = Math.hypot(nx, ny);
      if (magnitude > 1) { nx /= magnitude; ny /= magnitude; }
      if (knob) knob.style.transform = 'translate(calc(-50% + ' + (nx * 28) + '%), calc(-50% + ' + (ny * 28) + '%))';
      syncStickKeys(side, keysFromStick(side, nx, ny));
    }
    function endStick(event) {
      if (!stickPointers.has(event.pointerId)) return;
      stickPointers.delete(event.pointerId);
      syncStickKeys(side, new Set());
      resetStickVisual(stick);
      try { if (stick.hasPointerCapture(event.pointerId)) stick.releasePointerCapture(event.pointerId); } catch (_) {}
    }
    stick.addEventListener('pointermove', moveStick);
    stick.addEventListener('pointerup', endStick);
    stick.addEventListener('pointercancel', endStick);
    stick.addEventListener('lostpointercapture', endStick);
    stick.addEventListener('contextmenu', event => event.preventDefault());
  });
  document.querySelectorAll('#gamepadPanel button, #gamepadPanel .stick').forEach(node => {
    node.addEventListener('pointerdown', event => event.preventDefault());
  });

  function setMode(nextMode, focusInput = false) {
    if (!['douyin', 'mouse', 'keyboard', 'gamepad'].includes(nextMode)) nextMode = 'mouse';
    if (mode && mode !== nextMode) releaseDragOnLeave();
    mode = nextMode;
    storage.set('watchmouse_mode', mode);
    $('douyinPanel').hidden = mode !== 'douyin';
    $('gamepadPanel').hidden = mode !== 'gamepad';
    $('mousePanel').hidden = mode === 'douyin' || mode === 'gamepad';
    $('keyboardPanel').hidden = mode !== 'keyboard';
    document.body.classList.toggle('keyboard-visible', mode === 'keyboard');
    document.body.classList.toggle('mode-douyin', mode === 'douyin');
    document.body.classList.toggle('mode-gamepad', mode === 'gamepad');
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
    // Interface language changes leave dictation locale and active sessions unchanged.
    speech.lang = 'zh-CN';
    speech.continuous = false;
    speech.interimResults = true;
    let startingText = '';
    speech.onstart = () => { speechListening = true; $('speechButton').setAttribute('aria-pressed', 'true'); $('speechButton').setAttribute('aria-label', t('stopSpeech')); textFeedback(); };
    speech.onresult = event => {
      const transcript = Array.from(event.results).map(result => result[0].transcript).join('');
      $('textInput').value = (startingText + transcript).slice(0, 4000);
      inputVersion++;
      updateDeleteLabel();
    };
    speech.onend = () => { speechListening = false; $('speechButton').setAttribute('aria-pressed', 'false'); $('speechButton').setAttribute('aria-label', t('speech')); };
    speech.onerror = () => { speechListening = false; $('speechButton').setAttribute('aria-pressed', 'false'); $('speechButton').setAttribute('aria-label', t('speech')); textFeedback('speechUnavailable', true); };
    $('speechButton').addEventListener('click', () => {
      if (speechListening) { speech.stop(); return; }
      startingText = $('textInput').value;
      try { speech.start(); } catch (_) { textFeedback('speechUnavailable', true); }
    });
  }

  function releaseDragOnLeave() {
    // Best-effort release before the browser suspends the page. The receiver
    // also releases a held button when its session times out.
    const hadPadKeys = heldPadKeys.size > 0;
    if (dragActive || dragMayBeHeld || hadPadKeys) {
      flushMotion();
      // Keep an ordered release in the queue as well, so an in-flight MD
      // cannot leave the button held after the best-effort beacon arrives.
      // MU also clears any held keyboard keys used by the gamepad mode.
      releaseGamepadControls(false);
      enqueueRelease();
      releaseBeacon();
      dragActive = false;
      updateDragUI();
    } else {
      releaseGamepadControls(false);
    }
    if (motionTimer) { clearTimeout(motionTimer); motionTimer = null; }
    pendingX = pendingY = pendingScroll = pendingRailScroll = 0;
    clearRailGesture();
    for (let index = queue.length - 1; index >= 0; index--) {
      if (queue[index].kind === 'move' || queue[index].kind === 'scroll') queue.splice(index, 1);
    }
    pointers.clear(); gesture = null;
    cancelIndicator();
    pad.classList.remove('is-touching');
    $('touchIndicator').hidden = true;
  }
  function releaseBeacon() {
    if (releaseBeaconSent) return;
    try { releaseBeaconSent = navigator.sendBeacon('/api/command', new Blob([JSON.stringify({token: dragToken || token, command: 'MU'})], {type: 'application/json'})); } catch (_) {}
  }
  function suspendPage() {
    cancelStatusTimer(); statusVersion++; statusCheckQueued = false;
    if (statusController) statusController.abort();
    releaseDragOnLeave(); discardInput('notConnected', true);
    if (speechListening && speech) speech.stop();
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) suspendPage();
    else checkConnection();
  });
  window.addEventListener('pagehide', suspendPage);
  window.addEventListener('blur', releaseDragOnLeave);
  window.addEventListener('online', () => checkConnection());
  window.addEventListener('offline', () => { cancelStatusTimer(); statusVersion++; if (statusController) statusController.abort(); setConnection(false, 'networkOffline'); feedback(); });
  function syncViewport() {
    const viewport = window.visualViewport;
    const height = viewport ? viewport.height : window.innerHeight;
    const offset = viewport ? Math.max(0, viewport.offsetTop || 0) : 0;
    if (Number.isFinite(height) && height > 0) document.documentElement.style.setProperty('--viewport-height', height + 'px');
    document.documentElement.style.setProperty('--viewport-offset', offset + 'px');
    document.body.classList.toggle('compact-viewport', height < 400);
  }
  function viewportChanged() { releaseDragOnLeave(); syncViewport(); }
  window.addEventListener('resize', viewportChanged);
  window.addEventListener('orientationchange', viewportChanged);
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', viewportChanged);
    window.visualViewport.addEventListener('scroll', viewportChanged);
  }
  syncViewport();
  setMode(savedMode);
  applyLanguage();
  checkConnection();
})();
