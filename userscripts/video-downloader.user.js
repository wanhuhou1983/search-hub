// ==UserScript==
// @name         Video Downloader (PornHub / XVideos / MissAV)
// @namespace    https://github.com/search-hub
// @version      1.1.0
// @description  在 PornHub / XVideos / MissAV 页面添加下载按钮，通过 search-hub streaming 推流到本地浏览器
// @author       UHUH
// @match        https://www.pornhub.com/*
// @match        https://www.xvideos.com/*
// @match        https://missav.live/*
// @match        https://missav.ws/*
// @grant        GM_xmlhttpRequest
// @grant        GM_notification
// @grant        GM_addStyle
// @grant        GM_setValue
// @grant        GM_getValue
// @grant        GM_download
// @connect      localhost
// @connect      127.0.0.1
// @connect      *
// @run-at       document-idle
// @license      MIT
// ==/UserScript==

(function () {
  'use strict';

  // ═══════════════════════════════════════════════
  //  配置
  // ═══════════════════════════════════════════════
  const DEFAULT_SERVER = 'http://localhost:18081';

  // ═══════════════════════════════════════════════
  //  样式
  // ═══════════════════════════════════════════════
  GM_addStyle(`
    .uhuh-dl-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      z-index: 99999;
      padding: 12px 20px;
      background: linear-gradient(135deg, #ff6b6b, #ee5a24);
      color: #fff;
      border: none;
      border-radius: 12px;
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      box-shadow: 0 4px 15px rgba(238, 90, 36, 0.4);
      transition: all 0.2s ease;
      display: flex;
      align-items: center;
      gap: 8px;
      user-select: none;
    }
    .uhuh-dl-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(238, 90, 36, 0.5);
    }
    .uhuh-dl-btn:active {
      transform: translateY(0);
    }
    .uhuh-dl-btn.downloading {
      background: linear-gradient(135deg, #6c5ce7, #a29bfe);
      box-shadow: 0 4px 15px rgba(108, 92, 231, 0.4);
      pointer-events: none;
    }
    .uhuh-dl-btn.success {
      background: linear-gradient(135deg, #00b894, #00cec9);
      box-shadow: 0 4px 15px rgba(0, 184, 148, 0.4);
    }
    .uhuh-dl-btn.error {
      background: linear-gradient(135deg, #d63031, #e17055);
    }
    .uhuh-dl-spinner {
      width: 16px;
      height: 16px;
      border: 2px solid rgba(255,255,255,0.3);
      border-top-color: #fff;
      border-radius: 50%;
      animation: uhuh-spin 0.6s linear infinite;
    }
    @keyframes uhuh-spin {
      to { transform: rotate(360deg); }
    }
    .uhuh-panel {
      position: fixed;
      bottom: 80px;
      right: 24px;
      z-index: 99998;
      background: #1a1a2e;
      color: #eee;
      border-radius: 12px;
      padding: 16px;
      width: 320px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      font-size: 13px;
    }
    .uhuh-panel h3 {
      margin: 0 0 12px;
      font-size: 15px;
      color: #fff;
    }
    .uhuh-panel .uhuh-info {
      background: rgba(255,255,255,0.08);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 12px;
    }
    .uhuh-panel .uhuh-info .title {
      font-weight: 600;
      margin-bottom: 4px;
      word-break: break-all;
    }
    .uhuh-panel .uhuh-info .meta {
      font-size: 12px;
      color: #aaa;
    }
    .uhuh-panel select, .uhuh-panel input {
      width: 100%;
      padding: 8px;
      border: 1px solid #333;
      border-radius: 6px;
      background: #16213e;
      color: #eee;
      font-size: 13px;
      margin-bottom: 8px;
      box-sizing: border-box;
    }
    .uhuh-panel .uhuh-actions {
      display: flex;
      gap: 8px;
    }
    .uhuh-panel .uhuh-actions button {
      flex: 1;
      padding: 8px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      font-weight: 500;
    }
    .uhuh-panel .btn-primary {
      background: #ee5a24;
      color: #fff;
    }
    .uhuh-panel .btn-secondary {
      background: #333;
      color: #eee;
    }
    .uhuh-panel .uhuh-log {
      margin-top: 10px;
      font-size: 12px;
      color: #aaa;
      max-height: 120px;
      overflow-y: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
    .uhuh-settings {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid #333;
    }
    .uhuh-settings label {
      font-size: 12px;
      color: #aaa;
      display: block;
      margin-bottom: 4px;
    }
  `);

  // ═══════════════════════════════════════════════
  //  工具函数
  // ═══════════════════════════════════════════════
  const host = location.hostname;

  function getServer() {
    const el = document.getElementById('uhuh-server');
    if (el && el.value) {
      GM_setValue('searchHubUrl', el.value);
      return el.value;
    }
    return GM_getValue('searchHubUrl', 'http://localhost:18081');
  }

  function apiGet(serverUrl, endpoint) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'GET',
        url: `${serverUrl}${endpoint}`,
        responseType: 'json',
        timeout: 45000,
        onload: (resp) => {
          if (resp.status >= 200 && resp.status < 300) {
            resolve(typeof resp.response === 'string' ? JSON.parse(resp.response) : resp.response);
          } else {
            reject(new Error(`HTTP ${resp.status}`));
          }
        },
        onerror: () => reject(new Error('网络错误，请确认 search-hub 服务已启动')),
        ontimeout: () => reject(new Error('解析请求超时 (45s)')),
      });
    });
  }

  function notify(title, text, highlight) {
    GM_notification({ title, text, highlight: highlight || 'error', timeout: 3000 });
  }

  // ═══════════════════════════════════════════════
  //  站点检测
  // ═══════════════════════════════════════════════
  function detectSite() {
    if (host.includes('pornhub')) return 'pornhub';
    if (host.includes('xvideos')) return 'xvideos';
    if (host.includes('missav')) return 'missav';
    return null;
  }

  function getVideoUrl() { return location.href; }

  function getVideoTitle() {
    if (detectSite() === 'pornhub') {
      const el = document.querySelector('.video-title-text, h1.title span, .video-title-container .title');
      return el ? el.textContent.trim() : document.title.replace(' - Pornhub.com', '').trim();
    }
    if (detectSite() === 'xvideos') {
      const el = document.querySelector('.page-title, h2.page-title, #video-title');
      return el ? el.textContent.trim() : document.title.replace(' - XVIDEOS.COM', '').trim();
    }
    if (detectSite() === 'missav') {
      const el = document.querySelector('.video-title, h2.title, [class*="title"]');
      return el ? el.textContent.trim() : document.title.trim();
    }
    return document.title;
  }

  // ═══════════════════════════════════════════════
  //  UI
  // ═══════════════════════════════════════════════
  let panel = null;
  let btn = null;
  let _parseData = null;

  function createUI() {
    btn = document.createElement('button');
    btn.className = 'uhuh-dl-btn';
    btn.innerHTML = '⬇ 下载';
    btn.onclick = togglePanel;
    document.body.appendChild(btn);

    panel = document.createElement('div');
    panel.className = 'uhuh-panel';
    panel.style.display = 'none';
    let qualityHtml = '';
    if (detectSite() === 'pornhub') qualityHtml = `<select id="uhuh-quality"><option value="1080p">1080p</option><option value="720p" selected>720p</option><option value="480p">480p</option></select>`;
    if (detectSite() === 'missav') qualityHtml = `<select id="uhuh-quality"><option value="1080p">1080p</option><option value="720p" selected>720p</option><option value="480p">480p</option><option value="360p">360p</option></select>`;
    panel.innerHTML = '<h3>📥 Video Downloader</h3>' +
      '<div class="uhuh-info"><div class="title" id="uhuh-title">' + getVideoTitle() + '</div><div class="meta">' + location.href + '</div></div>' +
      qualityHtml +
      '<div class="uhuh-actions"><button class="btn-primary" onclick="window._uhuhDownload()">⬇ 下载</button><button class="btn-secondary" onclick="window._uhuhCopyUrl()">📋 复制链接</button></div>' +
      '<div class="uhuh-log" id="uhuh-log"></div>' +
      '<div class="uhuh-settings"><label>Search-Hub 地址:</label><input type="text" id="uhuh-server" value="' + GM_getValue('searchHubUrl', DEFAULT_SERVER) + '"></div>';
    document.body.appendChild(panel);

    window._uhuhDownload = doDownload;
    window._uhuhCopyUrl = copyUrl;
  }

  function togglePanel() {
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    if (panel.style.display === 'block' && !_parseData) autoParse();
  }

  function log(msg) {
    var el = document.getElementById('uhuh-log');
    if (el) el.textContent += msg + '\n';
    console.log('[UHUH-DL]', msg);
  }

  function setBtnState(state, text) {
    if (!btn) return;
    btn.className = 'uhuh-dl-btn' + (state ? ' ' + state : '');
    if (state === 'downloading') {
      btn.innerHTML = '<span class="uhuh-dl-spinner"></span>' + (text || '处理中...');
    } else {
      btn.innerHTML = text || '⬇ 下载';
    }
  }

  // ═══════════════════════════════════════════════
  //  解析
  // ═══════════════════════════════════════════════
  async function autoParse() {
    setBtnState('downloading', '解析中...');
    var site = detectSite();
    var serverUrl = getServer();
    log('解析: ' + getVideoUrl());
    try {
      var endpoint = '/api/' + site + '/parse';
      var resp = await apiGet(serverUrl, endpoint + '?url=' + encodeURIComponent(getVideoUrl()));
      if (resp.error) throw new Error(resp.error);
      _parseData = resp;
      log('成功: ' + (resp.title || ''));
      if (resp.qualities) log('画质: ' + resp.qualities.join(', '));
      setBtnState('', '⬇ 下载');
    } catch (e) {
      setBtnState('error', '❌ 解析失败');
      log('错误: ' + e.message);
      setTimeout(function() { setBtnState('', '⬇ 下载'); }, 5000);
    }
  }

  // ═══════════════════════════════════════════════
  //  流式下载
  // ═══════════════════════════════════════════════
  async function doDownload() {
    if (!_parseData) {
      await autoParse();
      if (!_parseData) return;
    }

    setBtnState('downloading', '流式下载中...');

    try {
      var site = detectSite();
      var serverUrl = getServer();
      var title = _parseData.title || getVideoTitle() || 'video';
      var streamUrl = '';

      if (site === 'missav') {
        var quality = (document.getElementById('uhuh-quality') && document.getElementById('uhuh-quality').value) || '720p';
        if (!_parseData.hls_url) throw new Error('未获取到视频流地址');
        var qUrl = _parseData.hls_url.replace('/720p/', '/' + quality + '/');
        streamUrl = serverUrl + '/api/stream/download?url=' + encodeURIComponent(qUrl) + '&filename=' + encodeURIComponent(title + '.mp4') + '&referer=' + encodeURIComponent('https://missav.live/');
      } else if (site === 'pornhub' || site === 'xvideos') {
        if (!_parseData.hls_url) throw new Error('未获取到视频流地址');
        streamUrl = serverUrl + '/api/stream/download?url=' + encodeURIComponent(_parseData.hls_url) + '&filename=' + encodeURIComponent(title + '.mp4') + '&referer=' + encodeURIComponent(getVideoUrl());
      } else {
        throw new Error('不支持的站点');
      }

      log('流式下载: ' + streamUrl.substring(0, 100) + '...');

      // 开新标签页下载
      var w = window.open(streamUrl, '_blank');
      if (!w) {
        log('⚠️ 弹窗被拦截，请允许此站点弹窗');
        notify('弹窗被拦截', '请允许此站点弹窗以触发下载');
        setBtnState('', '⬇ 下载');
      } else {
        setBtnState('success', '✅ 已发起');
        log('下载已发起，请查看新标签页');
        notify('下载已发起', title + '.mp4', 'info');
        setTimeout(function() { setBtnState('', '⬇ 下载'); }, 5000);
      }
    } catch (e) {
      setBtnState('error', '❌ 失败');
      log('错误: ' + e.message);
      notify('下载失败', e.message);
      setTimeout(function() { setBtnState('', '⬇ 下载'); }, 5000);
    }
  }

  function copyUrl() {
    var url = getVideoUrl();
    navigator.clipboard.writeText(url).then(function() {
      notify('已复制', url, 'info');
      log('URL 已复制');
    })['catch'](function() {
      var input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      log('URL 已复制');
    });
  }

  // ═══════════════════════════════════════════════
  //  启动
  // ═══════════════════════════════════════════════
  if (detectSite()) {
    if (document.readyState === 'complete') {
      createUI();
    } else {
      window.addEventListener('load', createUI);
    }
  }
})();
