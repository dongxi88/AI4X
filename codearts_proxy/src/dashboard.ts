/**
 * Web Dashboard HTML & UI Provider
 */

export function renderDashboardHtml(): string {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>CodeArts Proxy - 交互日志与实时监控看板</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --accent: #818cf8;
      --code-bg: #0b0f19;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text-main); min-height: 100vh; padding: 24px; font-size: 14px; }
    .container { max-width: 1200px; margin: 0 auto; }
    header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid var(--card-border); }
    h1 { font-size: 22px; font-weight: 700; display: flex; align-items: center; gap: 10px; color: var(--primary); }
    .badge { padding: 4px 10px; border-radius: 9999px; font-size: 12px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; }
    .badge-live { background: rgba(16, 185, 129, 0.15); color: var(--success); border: 1px solid rgba(16, 185, 129, 0.3); }
    .pulse { width: 8px; height: 8px; border-radius: 50%; background: var(--success); box-shadow: 0 0 8px var(--success); animation: pulse 2s infinite; }
    @keyframes pulse { 0% { opacity: 1; transform: scale(1); } 50% { opacity: 0.4; transform: scale(1.2); } 100% { opacity: 1; transform: scale(1); } }
    
    /* Metrics Grid */
    .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
    .metric-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px 20px; }
    .metric-title { font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }
    .metric-value { font-size: 22px; font-weight: 700; color: var(--text-main); }
    .metric-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

    /* Controls */
    .controls { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 12px; flex-wrap: wrap; }
    .btn { background: #334155; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; font-weight: 600; display: inline-flex; align-items: center; gap: 6px; transition: 0.2s; }
    .btn:hover { background: #475569; }
    .btn-primary { background: #0284c7; }
    .btn-primary:hover { background: #0369a1; }
    .btn-danger { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid rgba(239, 68, 68, 0.3); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.3); }
    .search-box { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 8px; padding: 8px 14px; color: #fff; font-size: 13px; outline: none; width: 280px; }
    .search-box:focus { border-color: var(--primary); }

    /* Interaction Log Cards */
    .log-list { display: flex; flex-direction: column; gap: 16px; }
    .log-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; overflow: hidden; transition: 0.2s border-color; }
    .log-card:hover { border-color: #475569; }
    .log-header { padding: 14px 18px; display: flex; justify-content: space-between; align-items: center; background: rgba(255,255,255,0.02); cursor: pointer; user-select: none; }
    .log-meta { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
    .tag { padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; text-transform: uppercase; }
    .tag-openai { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .tag-anthropic { background: rgba(129, 140, 248, 0.2); color: #a5b4fc; }
    .tag-stream { background: rgba(56, 189, 248, 0.15); color: #38bdf8; }
    .tag-ok { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .tag-err { background: rgba(239, 68, 68, 0.2); color: #f87171; }
    .model-name { font-weight: 600; color: #e2e8f0; font-family: monospace; }
    .model-arrow { color: var(--text-muted); font-size: 12px; }
    .time-text { color: var(--text-muted); font-size: 12px; }
    .duration-badge { color: #cbd5e1; font-size: 12px; }

    .log-body { padding: 16px 18px; border-top: 1px solid var(--card-border); display: flex; flex-direction: column; gap: 14px; }
    .block-title { font-size: 12px; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
    .code-box { background: var(--code-bg); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 12px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; line-height: 1.5; color: #e2e8f0; white-space: pre-wrap; word-break: break-word; max-height: 280px; overflow-y: auto; }
    .thinking-box { border-left: 3px solid #f59e0b; background: rgba(245, 158, 11, 0.05); color: #fde68a; }
    .response-box { border-left: 3px solid #38bdf8; }
    
    .empty-state { text-align: center; padding: 60px 20px; color: var(--text-muted); background: var(--card-bg); border-radius: 12px; border: 1px dashed var(--card-border); }
    .empty-icon { font-size: 40px; margin-bottom: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>CodeArts Proxy 实时监控看板</h1>
        <p style="color: var(--text-muted); margin-top: 4px;">CodeArts 大模型反向代理与协议转译实时交互中心</p>
      </div>
      <div style="display: flex; gap: 12px; align-items: center;">
        <span class="badge badge-live"><span class="pulse"></span> 实时监听中</span>
        <button class="btn btn-primary" onclick="fetchData()">刷新</button>
      </div>
    </header>

    <!-- Metrics Grid -->
    <div class="metrics">
      <div class="metric-card">
        <div class="metric-title">代理服务状态</div>
        <div class="metric-value" style="color: var(--success);" id="m-status">就绪 (17129)</div>
        <div class="metric-sub" id="m-port">http://127.0.0.1:17129/v1</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">CodeArts 内核连接</div>
        <div class="metric-value" style="color: var(--primary);" id="m-kernel">检测中...</div>
        <div class="metric-sub" id="m-models">已就绪模型: 0 个</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">累计捕获交互</div>
        <div class="metric-value" id="m-count">0 次</div>
        <div class="metric-sub" id="m-avg-time">平均耗时: 0.0s</div>
      </div>
      <div class="metric-card">
        <div class="metric-title">Token 消耗总计</div>
        <div class="metric-value" style="color: var(--accent);" id="m-tokens">0</div>
        <div class="metric-sub" id="m-token-ratio">输入: 0 | 输出: 0</div>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls">
      <div style="display: flex; gap: 10px; align-items: center;">
        <input type="text" id="search-input" class="search-box" placeholder="过滤模型 / 提示词关键字..." oninput="renderLogs()">
        <span style="color: var(--text-muted); font-size: 13px;" id="record-summary">共 0 条交互记录</span>
      </div>
      <div style="display: flex; gap: 10px;">
        <button class="btn btn-danger" onclick="clearLogs()">清空记录</button>
      </div>
    </div>

    <!-- Log List -->
    <div class="log-list" id="log-container">
      <div class="empty-state">
        <div class="empty-icon">⏳</div>
        <h3>暂无交互记录</h3>
        <p style="margin-top: 8px;">请在 Cursor、Cline、Claude Code 中发送任意提问，本看板将实时更新完整请求与回复！</p>
      </div>
    </div>
  </div>

  <script>
    let allRecords = [];

    async function fetchData() {
      try {
        const [statusResp, logsResp] = await Promise.all([
          fetch('/health').then(r => r.json()),
          fetch('/api/interactions').then(r => r.json())
        ]);

        // Update metrics
        if (statusResp.status === 'ok') {
          document.getElementById('m-status').textContent = '运行中 (17129)';
          document.getElementById('m-kernel').textContent = '正常 (' + statusResp.kernel.port + ')';
          document.getElementById('m-models').textContent = '已挂载模型: ' + (statusResp.kernel.models?.length || 0) + ' 个';
        }

        allRecords = logsResp.records || [];
        updateStats();
        renderLogs();
      } catch (err) {
        console.error('Fetch error:', err);
      }
    }

    function updateStats() {
      document.getElementById('m-count').textContent = allRecords.length + ' 次';
      let totalTokens = 0;
      let totalInput = 0;
      let totalOutput = 0;
      let totalDuration = 0;

      for (const r of allRecords) {
        totalTokens += (r.tokens.total || 0);
        totalInput += (r.tokens.input || 0);
        totalOutput += (r.tokens.output || 0);
        totalDuration += (r.durationMs || 0);
      }

      document.getElementById('m-tokens').textContent = totalTokens.toLocaleString();
      document.getElementById('m-token-ratio').textContent = '输入: ' + totalInput.toLocaleString() + ' | 输出: ' + totalOutput.toLocaleString();
      const avg = allRecords.length ? (totalDuration / allRecords.length / 1000).toFixed(2) : '0.0';
      document.getElementById('m-avg-time').textContent = '平均耗时: ' + avg + 's';
    }

    function renderLogs() {
      const keyword = (document.getElementById('search-input').value || '').toLowerCase().trim();
      const container = document.getElementById('log-container');

      const filtered = allRecords.filter(r => {
        if (!keyword) return true;
        return (r.clientModel || '').toLowerCase().includes(keyword) ||
               (r.resolvedModel || '').toLowerCase().includes(keyword) ||
               (r.prompt || '').toLowerCase().includes(keyword) ||
               (r.response || '').toLowerCase().includes(keyword);
      });

      document.getElementById('record-summary').textContent = '共 ' + filtered.length + ' 条交互记录';

      if (filtered.length === 0) {
        container.innerHTML = \`
          <div class="empty-state">
            <div class="empty-icon">\${keyword ? '🔍' : '⏳'}</div>
            <h3>\${keyword ? '未找到匹配记录' : '暂无交互记录'}</h3>
            <p style="margin-top: 8px;">\${keyword ? '请尝试更换搜索关键字' : '请在 Cursor、Cline、Claude Code 中发送任意提问，本看板将实时捕获并展示！'}</p>
          </div>\`;
        return;
      }

      container.innerHTML = filtered.map((r, idx) => {
        const protoTag = r.protocol === 'OpenAI' ? '<span class="tag tag-openai">OpenAI</span>' : '<span class="tag tag-anthropic">Anthropic</span>';
        const streamTag = r.stream ? '<span class="tag tag-stream">SSE Stream</span>' : '<span class="tag">Block</span>';
        const statusTag = r.status >= 200 && r.status < 300 ? '<span class="tag tag-ok">' + r.status + ' OK</span>' : '<span class="tag tag-err">' + r.status + ' ERR</span>';
        const durationSec = (r.durationMs / 1000).toFixed(2) + 's';

        return \`
          <div class="log-card" id="card-\${r.id}">
            <div class="log-header" onclick="toggleCard('\${r.id}')">
              <div class="log-meta">
                \${protoTag}
                \${streamTag}
                \${statusTag}
                <span class="model-name">\${r.clientModel}</span>
                \${r.clientModel !== r.resolvedModel ? '<span class="model-arrow">➔</span> <span class="model-name" style="color: var(--primary)">' + r.resolvedModel + '</span>' : ''}
              </div>
              <div style="display: flex; align-items: center; gap: 14px;">
                <span class="duration-badge">⏱️ \${durationSec}</span>
                <span class="duration-badge">🔤 In: \${r.tokens.input ?? 0} | Out: \${r.tokens.output ?? 0}</span>
                <span class="time-text">\${r.time}</span>
              </div>
            </div>
            <div class="log-body" id="body-\${r.id}">
              <div>
                <div class="block-title">📥 客户端提示词 (Prompt)</div>
                <div class="code-box">\${escapeHtml(r.prompt)}</div>
              </div>
              \${r.reasoning ? \`
              <div>
                <div class="block-title" style="color: var(--warning)">🧠 深度思考过程 (Thinking / Reasoning)</div>
                <div class="code-box thinking-box">\${escapeHtml(r.reasoning)}</div>
              </div>\` : ''}
              <div>
                <div class="block-title" style="color: var(--primary)">📤 模型回答 (Response)</div>
                <div class="code-box response-box">\${escapeHtml(r.response || r.error || '(无回答内容)')}</div>
              </div>
            </div>
          </div>
        \`;
      }).join('');
    }

    function toggleCard(id) {
      const body = document.getElementById('body-' + id);
      if (body) {
        body.style.display = body.style.display === 'none' ? 'flex' : 'none';
      }
    }

    function escapeHtml(str) {
      if (!str) return '';
      return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    async function clearLogs() {
      if (confirm('确认清空所有历史交互记录吗？')) {
        await fetch('/api/interactions/clear', { method: 'POST' });
        fetchData();
      }
    }

    // Connect SSE for real-time live events
    function connectEventSource() {
      const es = new EventSource('/api/stream');
      es.onmessage = (e) => {
        try {
          const rec = JSON.parse(e.data);
          allRecords.unshift(rec);
          updateStats();
          renderLogs();
        } catch (err) {}
      };
      es.onerror = () => {
        es.close();
        setTimeout(connectEventSource, 3000);
      };
    }

    fetchData();
    connectEventSource();
    setInterval(fetchData, 4000);
  </script>
</body>
</html>`;
}
