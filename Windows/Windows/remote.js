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
      gamepadControls: 'Gamepad controls', gamepadLayout: 'Gamepad layout', gamepadHint: 'Keyboard mapping · single player only',
      gamepadHintNative: 'Native mode: the computer sees an Xbox controller',
      gamepadJoining: 'Connecting controller…', gamepad_full: 'Four players are connected.', gamepad_unavailable: 'Native controller unavailable.',
      gamepad_session_expired: 'Reconnecting controller…', gamepad_session_required: 'Update the computer receiver.', player: 'Player',
      padFullscreen: 'Fullscreen landscape', padRotateHint: 'Turn the phone sideways for a better grip',
      inputModeScancode: 'Keys are injected as hardware scancodes, so games that read raw input still see them',
      inputModeElevated: 'Receiver is not elevated: a game launched as administrator will ignore input',
      padTrackpad: 'Pad trackpad: drag to move the cursor, tap to click, hold still to right-click',
      padTrackpadLabel: 'Trackpad', padTrackpadHint: 'Drag to move · tap to click · hold to right-click',
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
      gamepadControls: '手柄控制', gamepadLayout: '手柄布局', gamepadHint: '键盘映射 · 仅单人',
      gamepadHintNative: '原生模式：电脑已识别为 Xbox 手柄',
      gamepadJoining: '正在连接手柄…', gamepad_full: '已有四位玩家', gamepad_unavailable: '原生手柄不可用',
      gamepad_session_expired: '正在重连手柄…', gamepad_session_required: '请更新电脑接收器', player: '玩家',
      padFullscreen: '全屏横屏游玩', padRotateHint: '横屏握持更顺手',
      inputModeScancode: '按键以硬件扫描码注入，读原始输入的游戏也能收到',
      inputModeElevated: '接收器未以管理员运行：游戏若以管理员启动会收不到按键',
      padTrackpad: '手柄触控板：拖动移动鼠标，轻点左键，长按右键',
      padTrackpadLabel: '触控板', padTrackpadHint: '拖动移动 · 轻点左键 · 长按右键',
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
    updatePadHint();
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
      leavePadActivation();
      if (dragMayBeHeld) { releaseBeacon(); enqueueRelease(); }
      discardInput(messageKey); setConnectionPanel(true);
    } else ensurePadActivation();
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
  // Settings-panel diagnostics: how keys reach the desktop, and whether the
  // receiver could drive an elevated game at all.
  function updateInputModeNote(result) {
    const note = $('inputModeNote');
    if (!note) return;
    const parts = [];
    if (result.keyboardMode === 'scancode') parts.push(t('inputModeScancode'));
    if (result.elevated === false) parts.push(t('inputModeElevated'));
    note.textContent = parts.join(' · ');
    note.hidden = parts.length === 0;
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
      // A receiver that reports a native pad backend switches the gamepad
      // panel from keyboard mapping to real controller input.
      const nativePad = result.nativeGamepad === true;
      if (nativePad !== padNative) {
        releaseDragOnLeave();
        leavePadActivation();
        padNative = nativePad;
        updatePadHint();
      }
      updateInputModeNote(result);
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

  // 每个指针手势都在这里登记一个复位函数。旋转、进出全屏、切后台、切换模式，
  // 甚至浏览器漏发 pointerup / pointercancel 时，都能把控件恢复到“没有手指”
  // 的状态，不会出现“横屏之后触控板再也点不动”这类粘住的问题。
  const gestureResets = new Set();
  function onGestureReset(reset) { gestureResets.add(reset); return reset; }
  function cancelAllGestures() {
    for (const reset of gestureResets) { try { reset(); } catch (_) {} }
  }

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
    // 上一次抬手事件如果丢了（旋转屏幕、弹系统手势、页面被遮挡），这里残留的
    // 指针会让后面的单指拖动被当成双指滚动，所以先把超时的旧指针清掉。
    const now = performance.now();
    for (const [id, point] of [...pointers]) if (now - point.at > 1500) pointers.delete(id);
    if (!pointers.size) gesture = null;
    try { pad.setPointerCapture(event.pointerId); } catch (_) {}
    padRect = pad.getBoundingClientRect();
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY, at: now});
    if (pointers.size === 1) gesture = {started: now, moved: 0, multi: false, center: centroid()};
    else { gesture.multi = true; gesture.center = centroid(); }
    pad.classList.add('is-touching');
    showPointer(event);
  });
  function movePointer(event) {
    const previous = pointers.get(event.pointerId);
    if (!previous || !gesture || !Number.isFinite(event.clientX) || !Number.isFinite(event.clientY)) return;
    const dx = event.clientX - previous.x, dy = event.clientY - previous.y;
    pointers.set(event.pointerId, {x: event.clientX, y: event.clientY, at: performance.now()});
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
  // 复位：任何一次布局变化都把鼠标触控板当作“手指已经离开”。
  onGestureReset(() => {
    pointers.clear();
    gesture = null;
    pendingScroll = 0;
    pad.classList.remove('is-touching');
    cancelIndicator();
    $('touchIndicator').hidden = true;
  });

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
    if (railPointer) {
      // 滚动条也是单指操作，残留即上次抬手丢失，先清掉再重新开始。
      clearRailGesture();
    }
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
    try { scrollSurface.setPointerCapture(event.pointerId); } catch (_) {}
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
  onGestureReset(() => { if (railPointer) clearRailGesture(); });

  const PAD_KEYS = {
    lt: '1', lb: 'q', rb: 'r', rt: '2', select: 'tab', start: 'enter',
    a: 'space', b: 'escape', x: 'f', y: 'e',
    dup: 'w', ddown: 's', dleft: 'a', dright: 'd'
  };
  const STICK_KEYS = {
    left: {up: 'w', down: 's', left: 'a', right: 'd'},
    right: {up: 'up', down: 'down', left: 'left', right: 'right'}
  };
// Pad buttons are tracked by pad id ('a', 'lb', 'lt', ...). Keyboard mode
  // maps them through PAD_KEYS; native mode sends them to the virtual pad.
  const heldPadKeys = new Map();
  const heldStickKeys = new Map();
  const activeKeys = new Set();
  const stickPointers = new Map();
  const stickHeld = {left: new Set(), right: new Set()};
  const stickAxes = {left: {x: 0, y: 0}, right: {x: 0, y: 0}};
  // A thumb resting on the ring drifts a little; ignore that much travel.
  const STICK_DEADZONE = 0.16;
  // Keyboard mapping needs a firmer push so a rolling thumb does not chatter.
  const STICK_KEY_THRESHOLD = 0.42;
  let gamepadLayout = storage.get('watchmouse_pad_layout') === 'ps' ? 'ps' : 'xbox';
  // Declared with var so the early language pass can read it safely.
  var padNative = false;
  let padActivation = null;

  function wantedPadKeys() {
    const wanted = new Set();
    for (const id of heldPadKeys.keys()) {
      const key = PAD_KEYS[id];
      if (key) wanted.add(key);
    }
    for (const key of heldStickKeys.keys()) wanted.add(key);
    return wanted;
  }
  function syncPadKeys() {
    if (padNative) { schedulePadSend(); return; }
    const wanted = wantedPadKeys();
    for (const key of Array.from(activeKeys)) {
      if (!wanted.has(key)) { activeKeys.delete(key); sendQuietly({key, state: 'up'}); }
    }
    for (const key of wanted) {
      if (!activeKeys.has(key)) { activeKeys.add(key); sendQuietly({key, state: 'down'}); }
    }
  }
  function holdPadKey(id) {
    const count = heldPadKeys.get(id) || 0;
    heldPadKeys.set(id, count + 1);
    if (!count) syncPadKeys();
  }
  function releasePadKey(id) {
    const count = heldPadKeys.get(id) || 0;
    if (count <= 1) {
      if (count === 1) { heldPadKeys.delete(id); syncPadKeys(); }
      return;
    }
    heldPadKeys.set(id, count - 1);
  }
  function refreshStickKeys() {
    heldStickKeys.clear();
    for (const side of ['left', 'right']) {
      for (const key of stickHeld[side]) heldStickKeys.set(key, (heldStickKeys.get(key) || 0) + 1);
    }
    syncPadKeys();
  }
  function syncStickKeys(side, nextKeys) {
    stickHeld[side] = nextKeys;
    refreshStickKeys();
  }
  function setStickInput(side, nx, ny) {
    if (stickAxes[side].x === nx && stickAxes[side].y === ny) return;
    stickAxes[side] = {x: nx, y: ny};
    if (padNative) { schedulePadSend(); return; }
    syncStickKeys(side, keysFromStick(side, nx, ny));
  }
  function roundAxis(value) { return Math.round(value * 100) / 100; }
  function padSnapshot() {
    const buttons = [];
    let lt = 0, rt = 0;
    for (const id of heldPadKeys.keys()) {
      if (id === 'lt') lt = 1;
      else if (id === 'rt') rt = 1;
      else buttons.push(id);
    }
    const left = stickAxes.left, right = stickAxes.right;
    return {
      lx: roundAxis(left.x), ly: roundAxis(left.y),
      rx: roundAxis(right.x), ry: roundAxis(right.y),
      lt, rt, buttons
    };
  }
  function activePadInput() {
    const l = stickAxes.left, r = stickAxes.right;
    return heldPadKeys.size > 0 || l.x !== 0 || l.y !== 0 || r.x !== 0 || r.y !== 0;
  }
  function canUseGamepad() {
    return connected && !document.hidden && mode === 'gamepad' && (!padNative || Boolean(padActivation && padActivation.session && !padActivation.closed));
  }
  function currentPadActivation(activation) {
    return activation === padActivation && !activation.closed && padNative && connected && mode === 'gamepad' && !document.hidden && activation.token === token;
  }
  function newPadRequestId() {
    const values = new Uint32Array(4);
    if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') crypto.getRandomValues(values);
    else for (let index = 0; index < values.length; index++) values[index] = Math.floor(Math.random() * 0x100000000);
    return Array.from(values, value => value.toString(16).padStart(8, '0')).join('');
  }
  function ensurePadActivation() {
    if (!padNative || !connected || mode !== 'gamepad' || document.hidden || navigator.onLine === false) return;
    if (padActivation && !padActivation.closed) return;
    clearPadState(); clearGamepadUi();
    const activation = {requestId: newPadRequestId(), token, session: '', player: 0, seq: 0, closed: false,
      joining: false, inFlight: false, dirty: false, mayHold: false, sendTimer: null, keepTimer: null, retryTimer: null,
      joinController: null, sendController: null, issue: '', leaveKeys: new Set()};
    padActivation = activation;
    updatePadHint();
    joinPadActivation(activation);
  }
  async function joinPadActivation(activation) {
    if (!currentPadActivation(activation) || activation.joining || activation.session) return;
    activation.joining = true;
    activation.issue = '';
    const controller = new AbortController(); activation.joinController = controller;
    try {
      const result = await request('/api/pad/join', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': activation.token},
        body: JSON.stringify({token: activation.token, requestId: activation.requestId})}, controller, 4000);
      if (typeof result.session !== 'string' || !result.session || !Number.isInteger(result.player) || result.player < 1 || result.player > 4) throw localError('invalidResponse');
      activation.session = result.session; activation.player = result.player;
      if (!currentPadActivation(activation)) { sendPadLeave(activation); return; }
      clearPadState(); clearGamepadUi();
      updatePadHint();
      schedulePadSend(true);
    } catch (error) {
      if (!currentPadActivation(activation)) return;
      const key = errorMessage(error);
      if (key === 'invalid_token') { retryBlocked = true; setConnection(false, key); return; }
      if (error.errorCode === 'gamepad_session_expired') { leavePadActivation(); ensurePadActivation(); return; }
      activation.issue = ['gamepad_full', 'gamepad_unavailable', 'gamepad_session_required'].includes(error.errorCode) ? error.errorCode : 'gamepad_unavailable';
      updatePadHint();
      // Join is idempotent. Retry the same request ID so a lost response never
      // allocates a second controller to one page.
      activation.retryTimer = setTimeout(() => {
        activation.retryTimer = null;
        if (currentPadActivation(activation)) joinPadActivation(activation);
      }, 5000);
    } finally { activation.joining = false; activation.joinController = null; }
  }
  function sendPadLeave(activation) {
    const key = activation.session || 'pending';
    if (activation.leaveKeys.has(key)) return;
    activation.leaveKeys.add(key);
    const payload = {token: activation.token, requestId: activation.requestId};
    if (activation.session) payload.session = activation.session;
    const body = JSON.stringify(payload);
    try { if (navigator.sendBeacon('/api/pad/leave', new Blob([body], {type: 'application/json'}))) return; } catch (_) {}
    try { fetch('/api/pad/leave', {method: 'POST', keepalive: true, headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': activation.token}, body}).catch(() => {}); } catch (_) {}
  }
  function leavePadActivation() {
    const activation = padActivation;
    if (!activation) return;
    padActivation = null; activation.closed = true;
    for (const timer of ['sendTimer', 'keepTimer', 'retryTimer']) { if (activation[timer]) clearTimeout(activation[timer]); activation[timer] = null; }
    if (activation.joinController) activation.joinController.abort();
    if (activation.sendController) activation.sendController.abort();
    clearPadState(); clearGamepadUi();
    sendPadLeave(activation);
    updatePadHint();
  }
  function schedulePadSend(immediate = false) {
    const activation = padActivation;
    if (!activation || !activation.session || !currentPadActivation(activation)) return;
    activation.dirty = true;
    if (activation.inFlight) return;
    if (immediate) {
      if (activation.sendTimer) { clearTimeout(activation.sendTimer); activation.sendTimer = null; }
      sendPadState(activation);
      return;
    }
    if (!activation.sendTimer) activation.sendTimer = setTimeout(() => { activation.sendTimer = null; sendPadState(activation); }, 33);
  }
  async function sendPadState(activation) {
    if (!activation || !activation.session || !currentPadActivation(activation) || activation.inFlight || activation.sendTimer) return;
    const snapshot = padSnapshot();
    const body = JSON.stringify({token: activation.token, session: activation.session, seq: ++activation.seq, pad: snapshot});
    activation.dirty = false; activation.inFlight = true;
    activation.mayHold = activation.mayHold || activePadInput();
    const controller = new AbortController(); activation.sendController = controller;
    try {
      await request('/api/pad', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-WatchMouse-Token': activation.token}, body}, controller, 4000);
      if (!currentPadActivation(activation)) return;
      if (!snapshot.buttons.length && !snapshot.lx && !snapshot.ly && !snapshot.rx && !snapshot.ry && !snapshot.lt && !snapshot.rt) activation.mayHold = false;
      lastInputAck = performance.now();
      feedback();
    } catch (error) {
      if (!currentPadActivation(activation)) return;
      const message = errorMessage(error);
      if (message === 'invalid_token') { retryBlocked = true; setConnection(false, message); }
      else {
        leavePadActivation();
        if (error.errorCode === 'gamepad_session_expired') ensurePadActivation();
        else checkConnection();
      }
    } finally {
      activation.inFlight = false; activation.sendController = null;
      if (!currentPadActivation(activation)) return;
      // Coalesce whatever arrived while the previous snapshot was in flight.
      if (activation.dirty) {
        if (activation.sendTimer) clearTimeout(activation.sendTimer);
        activation.sendTimer = setTimeout(() => { activation.sendTimer = null; sendPadState(activation); }, 16);
        return;
      }
      // A virtual pad holds its last state, so refresh a held input once a
      // second; the receiver drops a silent pad after five seconds.
      startPadKeepAlive(activation);
    }
  }
  function startPadKeepAlive(activation = padActivation) {
    if (!activation || !activation.session || !currentPadActivation(activation) || activation.keepTimer) return;
    activation.keepTimer = setTimeout(() => { activation.keepTimer = null; sendPadState(activation); }, 1000);
  }
  function stopPadKeepAlive() {
    if (padActivation && padActivation.keepTimer) { clearTimeout(padActivation.keepTimer); padActivation.keepTimer = null; }
  }
  function neutralPadActivation() {
    const activation = padActivation;
    if (!activation || !activation.session || !currentPadActivation(activation)) return;
    // A higher sequence fences an older held snapshot which might arrive
    // after this neutral beacon. The ordered sender follows with neutral too.
    const body = JSON.stringify({token: activation.token, session: activation.session, seq: ++activation.seq,
      pad: {lx: 0, ly: 0, rx: 0, ry: 0, lt: 0, rt: 0, buttons: []}});
    try { navigator.sendBeacon('/api/pad', new Blob([body], {type: 'application/json'})); } catch (_) {}
    schedulePadSend(true);
  }
  // Trackpad in the middle of the pad: drag moves the cursor, a short tap is a
  // left click, holding still is a right click. Same queue as the mouse panel,
  // so nothing is sent while the finger is still.
  const padTrackpad = $('padTrackpad');
  const padTrackKnob = padTrackpad.querySelector('.pad-trackpad-knob');
  let padTrackPointer = null;
  function movePadTrackKnob(event) {
    if (!padTrackKnob) return;
    const rect = padTrackpad.getBoundingClientRect();
    const x = Math.max(-1, Math.min(1, (event.clientX - (rect.left + rect.width / 2)) / (rect.width / 2)));
    const y = Math.max(-1, Math.min(1, (event.clientY - (rect.top + rect.height / 2)) / (rect.height / 2)));
    padTrackKnob.style.transform = `translate(${x * rect.width * 0.3}px, ${y * rect.height * 0.3}px)`;
  }
  function resetPadTrackpad() {
    padTrackPointer = null;
    padTrackpad.classList.remove('active');
    if (padTrackKnob) padTrackKnob.style.transform = '';
  }
  padTrackpad.addEventListener('pointerdown', event => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    event.preventDefault();
    event.stopPropagation();
    if (padTrackPointer) {
      // 触控板只认一根手指。这里还有残留说明上一条抬手事件丢了，
      // 直接复位，否则触控板会一直以为手指还按在上面。
      resetPadTrackpad();
    }
    if (!connected) { feedback('notConnected', true); setConnectionPanel(true); return; }
    try { padTrackpad.setPointerCapture(event.pointerId); } catch (_) {}
    padTrackPointer = {id: event.pointerId, x: event.clientX, y: event.clientY, moved: 0, started: performance.now()};
    padTrackpad.classList.add('active');
    movePadTrackKnob(event);
  });
  padTrackpad.addEventListener('pointermove', event => {
    if (!padTrackPointer || padTrackPointer.id !== event.pointerId) return;
    event.preventDefault();
    const dx = event.clientX - padTrackPointer.x, dy = event.clientY - padTrackPointer.y;
    padTrackPointer.x = event.clientX;
    padTrackPointer.y = event.clientY;
    padTrackPointer.moved += Math.hypot(dx, dy);
    pendingX += dx * sensitivity;
    pendingY += dy * sensitivity;
    scheduleMotion();
    movePadTrackKnob(event);
  });
  function finishPadTrack(event, cancelled) {
    if (!padTrackPointer || padTrackPointer.id !== event.pointerId) return;
    const gesture = padTrackPointer;
    if (padTrackpad.hasPointerCapture(event.pointerId)) { try { padTrackpad.releasePointerCapture(event.pointerId); } catch (_) {} }
    resetPadTrackpad();
    if (cancelled) { flushMotion(); return; }
    if (gesture.moved < 8) {
      // send() flushes the pending motion first, so the click lands where the
      // cursor actually is rather than where it started.
      sendQuietly({command: performance.now() - gesture.started >= 450 ? 'RC' : 'C'});
    } else {
      flushMotion();
    }
  }
  padTrackpad.addEventListener('pointerup', event => finishPadTrack(event, false));
  padTrackpad.addEventListener('pointercancel', event => finishPadTrack(event, true));
  padTrackpad.addEventListener('lostpointercapture', event => finishPadTrack(event, true));
  padTrackpad.addEventListener('contextmenu', event => event.preventDefault());
  onGestureReset(resetPadTrackpad);

  function clearPadState() {
    stopPadKeepAlive();
    heldPadKeys.clear();
    heldStickKeys.clear();
    activeKeys.clear();
    stickHeld.left = new Set();
    stickHeld.right = new Set();
    stickAxes.left = {x: 0, y: 0};
    stickAxes.right = {x: 0, y: 0};
  }
  function updatePadHint() {
    const hint = document.querySelector('#gamepadPanel .gamepad-hint');
    const activation = padActivation;
    const issue = padNative && activation && activation.issue;
    if (hint) {
      hint.textContent = t(!padNative ? 'gamepadHint' : issue || (activation && activation.session ? 'gamepadHintNative' : 'gamepadJoining'));
      hint.classList.toggle('has-error', Boolean(issue));
    }
    const badge = $('padPlayerBadge');
    if (badge) {
      const player = padNative && activation && activation.session && !activation.closed ? activation.player : 0;
      badge.hidden = !player;
      badge.textContent = player ? 'P' + player : '';
      badge.setAttribute('aria-label', player ? t('player') + ' ' + player : '');
    }
  }
  function keysFromStick(side, nx, ny) {
    const map = STICK_KEYS[side];
    const next = new Set();
    const dead = STICK_KEY_THRESHOLD;
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
    document.querySelectorAll('#gamepadPanel .is-pressed').forEach(button => {
      button.classList.remove('is-pressed');
      button.padPointer = undefined;
    });
    document.querySelectorAll('#gamepadPanel .stick').forEach(resetStickVisual);
    resetPadTrackpad();
  }
  function releaseGamepadControls(sendServer = true) {
    const hadKeys = heldPadKeys.size > 0 || heldStickKeys.size > 0;
    const activation = padActivation;
    const wasNative = padNative && activation && activation.session && (activePadInput() || activation.mayHold || activation.inFlight);
    clearPadState();
    for (const [pointerId, state] of stickPointers) {
      if (state.stick.hasPointerCapture(pointerId)) state.stick.releasePointerCapture(pointerId);
    }
    stickPointers.clear();
    clearGamepadUi();
    // A virtual pad keeps its last state, so queue a neutral snapshot even when
    // the page is going away; the beacon below is the best-effort backstop.
    if (padNative) {
      if (wasNative) neutralPadActivation();
      else startPadKeepAlive();
      return;
    }
    if (hadKeys && sendServer) { syncPadKeys(); enqueueRelease(); }
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
      if (!canUseGamepad()) return;
      const id = button.dataset.pad;
      if (!id) return;
      // 记下是哪个指针按着这个键：同一根手指重复按下说明上次的抬手丢了，
      // 先把它松开再重新按住，不会出现“按键一直按着”的假状态。
      if (button.padPointer === event.pointerId) return;
      if (button.padPointer !== undefined) { releasePadKey(id); button.classList.remove('is-pressed'); }
      button.padPointer = event.pointerId;
      button.classList.add('is-pressed');
      try { button.setPointerCapture(event.pointerId); } catch (_) {}
      holdPadKey(id);
    };
    const unbind = event => {
      if (button.padPointer !== event.pointerId) return;
      button.padPointer = undefined;
      button.classList.remove('is-pressed');
      const id = button.dataset.pad;
      if (id) releasePadKey(id);
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
      if (!canUseGamepad()) return;
      // 一根摇杆只跟一根手指。残留的旧指针说明上一次抬手事件丢了，
      // 直接作废，否则摇杆会停在“手指还按着”的那一档。
      for (const [id, point] of [...stickPointers]) if (point.stick === stick && id !== event.pointerId) stickPointers.delete(id);
      stickPointers.set(event.pointerId, {stick, side});
      try { stick.setPointerCapture(event.pointerId); } catch (_) {}
      stick.classList.add('active');
      moveStick(event);
    });
    function moveStick(event) {
      if (!stickPointers.has(event.pointerId)) return;
      const rect = stick.getBoundingClientRect();
      // Travel is measured from the ring centre: the knob can reach the rim
      // without the finger leaving the circle.
      const radius = Math.min(rect.width, rect.height) / 2;
      let nx = (event.clientX - (rect.left + radius)) / radius;
      let ny = (event.clientY - (rect.top + radius)) / radius;
      const magnitude = Math.hypot(nx, ny);
      if (magnitude > 1) { nx /= magnitude; ny /= magnitude; }
      if (magnitude < STICK_DEADZONE) { nx = 0; ny = 0; }
      if (knob) knob.style.transform = 'translate(calc(-50% + ' + (nx * 34) + '%), calc(-50% + ' + (ny * 34) + '%))';
      setStickInput(side, nx, ny);
    }
    function endStick(event) {
      if (!stickPointers.has(event.pointerId)) return;
      stickPointers.delete(event.pointerId);
      setStickInput(side, 0, 0);
      resetStickVisual(stick);
      try { if (stick.hasPointerCapture(event.pointerId)) stick.releasePointerCapture(event.pointerId); } catch (_) {}
    }
    stick.addEventListener('pointermove', moveStick);
    stick.addEventListener('pointerup', endStick);
    stick.addEventListener('pointercancel', endStick);
    stick.addEventListener('lostpointercapture', endStick);
    stick.addEventListener('contextmenu', event => event.preventDefault());
  });
  document.querySelectorAll('#gamepadPanel button, #gamepadPanel .stick, #padTrackpad').forEach(node => {
    node.addEventListener('pointerdown', event => event.preventDefault());
  });
  // 复位：摇杆和按住的键都回到中位/松开，避免旋转后摇杆卡在某个方向。
  onGestureReset(() => {
    const touched = new Set([...stickPointers.values()].map(point => point.stick));
    stickPointers.clear();
    touched.forEach(resetStickVisual);
    setStickInput('left', 0, 0);
    setStickInput('right', 0, 0);
    document.querySelectorAll('#gamepadPanel [data-pad]').forEach(button => {
      if (button.padPointer === undefined) return;
      button.padPointer = undefined;
      button.classList.remove('is-pressed');
      const id = button.dataset.pad;
      if (id) releasePadKey(id);
    });
  });

  // Fullscreen + landscape lock puts the grips under the thumbs and hides the
  // browser chrome. iOS Safari cannot lock orientation, so the CSS layout and
  // the rotate hint carry that case.
  function immersiveActive() {
    return document.body.classList.contains('pad-immersive');
  }
  function setPadImmersive(on) {
    const shell = document.querySelector('.app-shell');
    // 进/出全屏会改变可用高度，手上的手势必须作废，否则触控板会停在按下状态。
    cancelAllGestures();
    releaseDragOnLeave();
    document.body.classList.toggle('pad-immersive', on);
    const button = $('padFullscreenButton');
    if (button) button.setAttribute('aria-pressed', String(on));
    try {
      if (on) {
        const request = shell && (shell.requestFullscreen || shell.webkitRequestFullscreen);
        if (request) {
          const pending = request.call(shell, {navigationUI: 'hide'});
          if (pending && pending.catch) pending.catch(() => {});
        }
        if (typeof screen !== 'undefined' && screen.orientation && screen.orientation.lock) {
          const locked = screen.orientation.lock('landscape');
          if (locked && locked.catch) locked.catch(() => {});
        }
      } else {
        if (typeof screen !== 'undefined' && screen.orientation && screen.orientation.unlock) {
          try { screen.orientation.unlock(); } catch (_) {}
        }
        if (document.fullscreenElement || document.webkitFullscreenElement) {
          const exit = document.exitFullscreen || document.webkitExitFullscreen;
          if (exit) exit.call(document);
        }
      }
    } catch (_) {}
    if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function' && typeof setTimeout === 'function') {
      setTimeout(() => {
        try { window.dispatchEvent(new Event('resize')); } catch (_) {}
      }, 120);
    }
  }
  if ($('padFullscreenButton')) {
    $('padFullscreenButton').addEventListener('click', () => setPadImmersive(!immersiveActive()));
  }
  document.querySelectorAll('.pad-rotate-hint').forEach(node => {
    node.addEventListener('click', () => setPadImmersive(true));
  });
  ['fullscreenchange', 'webkitfullscreenchange'].forEach(name => {
    document.addEventListener(name, () => {
      const active = document.fullscreenElement || document.webkitFullscreenElement;
      if (!active && immersiveActive()) setPadImmersive(false);
    });
  });

  function setMode(nextMode, focusInput = false) {
    if (!['douyin', 'mouse', 'keyboard', 'gamepad'].includes(nextMode)) nextMode = 'mouse';
    if (mode === 'gamepad' && nextMode !== 'gamepad') leavePadActivation();
    if (mode === 'gamepad' && nextMode !== 'gamepad' && immersiveActive()) setPadImmersive(false);
    if (mode && mode !== nextMode) { releaseDragOnLeave(); cancelAllGestures(); }
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
    ensurePadActivation();
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
    const hadPadKeys = !padNative && (heldPadKeys.size > 0 || activePadInput());
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
    leavePadActivation();
    releaseDragOnLeave(); discardInput('notConnected', true);
    cancelAllGestures();
    if (speechListening && speech) speech.stop();
  }
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) suspendPage();
    else checkConnection();
  });
  window.addEventListener('pagehide', suspendPage);
  window.addEventListener('blur', () => { releaseDragOnLeave(); cancelAllGestures(); });
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
  let lastLayout = '';
  function layoutChanged(force = false) {
    // 只在宽高比真的变了（旋转屏幕 / 进出全屏）时复位手势；地址栏收起这类
    // 纯高度变化不打断正在进行的拖动。orientationchange 一律强制复位。
    const layout = (window.matchMedia && window.matchMedia('(orientation: portrait)').matches ? 'p' : 'l') + window.innerWidth;
    if (!force && layout === lastLayout) return;
    lastLayout = layout;
    releaseDragOnLeave();
    cancelAllGestures();
  }
  window.addEventListener('resize', () => { viewportChanged(); layoutChanged(); });
  window.addEventListener('orientationchange', () => { viewportChanged(); layoutChanged(true); });
  document.addEventListener('fullscreenchange', () => { releaseDragOnLeave(); cancelAllGestures(); });
  // iOS 上有时只发 touchcancel / touchend，没有 pointercancel（旋转屏幕、系统
  // 手势抢走触点都会这样）。所有手指都离开时统一收尾，避免控件卡在按下状态。
  ['touchend', 'touchcancel'].forEach(name => window.addEventListener(name, event => {
    if (!event || !event.touches || event.touches.length === 0) cancelAllGestures();
  }, {passive: true, capture: true}));
  if (window.visualViewport) {
    window.visualViewport.addEventListener('resize', viewportChanged);
    window.visualViewport.addEventListener('scroll', viewportChanged);
  }
  syncViewport();
  layoutChanged();
  setMode(savedMode);
  applyLanguage();
  checkConnection();
})();
