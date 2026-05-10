// ==UserScript==
// @name         Video Downloader (PornHub / XVideos / MissAV)
// @namespace    https://github.com/search-hub
// @version      1.0.0
// @description  在 PornHub / XVideos / MissAV 页面添加下载按钮，一键发送到本地 search-hub 服务下载
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
        timeout: 30000,
        onload: (resp) => {
          if (resp.status >= 200 && resp.status < 300) {
            resolve(typeof resp.response === 'string' ? JSON.parse(resp.response) : resp.response);
          } else {
            reject(new Error(`HTTP ${resp.status}`));
          }
        },
        onerror: () => reject(new Error(`网络错误，请确认 search-hub 服务已启动`)),
        ontimeout: () => reject(new Error('请求超时 (30s)')),
      });
    });
  }

  function apiPost(serverUrl, endpoint, body) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: 'POST',
        url: `${serverUrl}${endpoint}`,
        data: JSON.stringify(body),
        headers: { 'Content-Type': 'application/json' },
        responseType: 'json',
        timeout: 300000,
        onload: (resp) => {
          if (resp.status >= 200 && resp.status < 300) {
            resolve(typeof resp.response === 'string' ? JSON.parse(resp.response) : resp.response);
          } else {
            const msg = resp.response?.error || `HTTP ${resp.status}`;
            reject(new Error(msg));
          }
        },
        onerror: () => reject(new Error(`网络错误，请确认 search-hub 服务已启动`)),
        ontimeout: () => reject(new Error('请求超时 (300s)，下载可能仍在进行')),
      });
    });
  }

  function notify(title, text, highlight = 'error') {
    GM_notification({ title, text, highlight, timeout: 3000 });
  }

  // ═══════════════════════════════════════════════
  //  站点检测 & 视频信息提取
  // ═══════════════════════════════════════════════
  function detectSite() {
    if (host.includes('pornhub')) return 'pornhub';
    if (host.includes('xvideos')) return 'xvideos';
    if (host.includes('missav')) return 'missav';
    return null;
  }

  function getVideoUrl() {
    return location.href;
  }

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
  //  UI 创建
  // ═══════════════════════════════════════════════
  let panel = null;
  let btn = null;

  function createUI() {
    // 下载按钮
    btn = document.createElement('button');
    btn.className = 'uhuh-dl-btn';
    btn.innerHTML = '⬇ 下载';
    btn.onclick = togglePanel;
    document.body.appendChild(btn);

    // 面板
    panel = document.createElement('div');
    panel.className = 'uhuh-panel';
    panel.style.display = 'none';
    panel.innerHTML = `
      <h3>📥 Video Downloader</h3>
      <div class="uhuh-info">
        <div class="title" id="uhuh-title">${getVideoTitle()}</div>
        <div class="meta" id="uhuh-meta">${location.href}</div>
      </div>
      ${detectSite() === 'pornhub' ? `
        <select id="uhuh-quality">
          <option value="1080p">1080p</option>
          <option value="720p" selected>720p</option>
          <option value="480p">480p</option>
        </select>
      ` : ''}
      ${detectSite() === 'missav' ? `
        <select id="uhuh-quality">
          <option value="1080p">1080p</option>
          <option value="720p" selected>720p</option>
          <option value="480p">480p</option>
          <option value="360p">360p</option>
        </select>
      ` : ''}
      <div class="uhuh-actions">
        <button class="btn-primary" id="uhuh-dl-action" onclick="window._uhuhDownload()">⬇ 下载</button>
        <button class="btn-secondary" onclick="window._uhuhCopyUrl()">📋 复制链接</button>
      </div>
      <div class="uhuh-log" id="uhuh-log"></div>
      <div class="uhuh-settings">
        <label>Search-Hub 地址:</label>
        <input type="text" id="uhuh-server" value="${GM_getValue('searchHubUrl', DEFAULT_SERVER)}">
      </div>
    `;
    document.body.appendChild(panel);

    // 暴露到 window
    window._uhuhDownload = doDownload;
    window._uhuhCopyUrl = copyUrl;
  }

  function togglePanel() {
    if (!panel) return;
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
  }

  function log(msg) {
    const el = document.getElementById('uhuh-log');
    if (el) el.textContent += msg + '\n';
    console.log('[UHUH-DL]', msg);
  }

  function setBtnState(state, text) {
    if (!btn) return;
    btn.className = 'uhuh-dl-btn' + (state ? ` ${state}` : '');
    if (state === 'downloading') {
      btn.innerHTML = `<span class="uhuh-dl-spinner"></span>${text || '下载中...'}`;
    } else {
      btn.innerHTML = text || '⬇ 下载';
    }
  }

  // ═══════════════════════════════════════════════
  //  下载动作
  // ═══════════════════════════════════════════════
  async function doDownload() {
    const site = detectSite();
    const url = getVideoUrl();
    const serverUrl = getServer();

    setBtnState('downloading', '解析中...');
    log(`开始解析: ${url}`);

    try {
      let result;

      if (site === 'pornhub') {
        const quality = document.getElementById('uhuh-quality')?.value || '720p';
        log(`调用 search-hub 解析 PornHub...`);
        const parseResp = await apiGet(serverUrl, `/api/pornhub/parse?url=${encodeURIComponent(url)}`);
        if (parseResp.error) throw new Error(parseResp.error);
        log(`标题: ${parseResp.title || '未知'} | 时长: ${parseResp.duration_str || '未知'}`);

        setBtnState('downloading', '下载中...');
        log(`开始下载 (${quality})...`);
        result = await apiPost(serverUrl, '/api/pornhub/download', { url, quality });

      } else if (site === 'xvideos') {
        log(`调用 search-hub 解析 XVideos...`);
        const parseResp = await apiGet(serverUrl, `/api/xvideos/parse?url=${encodeURIComponent(url)}`);
        if (parseResp.error) throw new Error(parseResp.error);
        log(`标题: ${parseResp.title || '未知'}`);

        setBtnState('downloading', '下载中...');
        log(`开始下载...`);
        result = await apiPost(serverUrl, '/api/xvideos/download', { url });

      } else if (site === 'missav') {
        const quality = document.getElementById('uhuh-quality')?.value || '720p';
        log(`调用 search-hub 解析 MissAV...`);
        const parseResp = await apiGet(serverUrl, `/api/missav/parse?url=${encodeURIComponent(url)}`);
        if (parseResp.error) throw new Error(parseResp.error);
        log(`UUID: ${parseResp.uuid || '未知'} | 画质: ${parseResp.qualities?.join(',') || '未知'}`);

        if (!parseResp.uuid) throw new Error('解析成功但未获取到 UUID');
        setBtnState('downloading', '下载中...');
        log(`开始下载 (${quality})...`);
        result = await apiPost(serverUrl, '/api/missav/download', { uuid: parseResp.uuid, quality });
      }

      if (result && result.error) {
        throw new Error(result.error);
      }

      if (result && result.success) {
        setBtnState('success', '✅ 完成');
        log(`下载完成! 文件: ${result.file || result.path || '未知'}`);
        if (result.size_mb) log(`文件大小: ${result.size_mb} MB`);
        notify('下载完成', `${result.file || result.path}`, 'success');
        setTimeout(() => setBtnState('', '⬇ 下载'), 5000);
      } else {
        throw new Error('未知返回: ' + JSON.stringify(result));
      }

    } catch (err) {
      setBtnState('error', '❌ 失败');
      log(`错误: ${err.message}`);
      notify('下载失败', err.message);
      setTimeout(() => setBtnState('', '⬇ 下载'), 5000);
    }
  }

  function copyUrl() {
    const url = getVideoUrl();
    navigator.clipboard.writeText(url).then(() => {
      notify('已复制', url, 'info');
      log('URL 已复制到剪贴板');
    }).catch(() => {
      // fallback
      const input = document.createElement('input');
      input.value = url;
      document.body.appendChild(input);
      input.select();
      document.execCommand('copy');
      document.body.removeChild(input);
      log('URL 已复制到剪贴板');
    });
  }

  // ═══════════════════════════════════════════════
  //  启动
  // ═══════════════════════════════════════════════
  if (detectSite()) {
    // 等页面加载完毕
    if (document.readyState === 'complete') {
      createUI();
    } else {
      window.addEventListener('load', createUI);
    }
  }
})();
