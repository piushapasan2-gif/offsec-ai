// ═══════════════════════════════════════
//  OffSec AI 2025 — Frontend v2 (streaming)
// ═══════════════════════════════════════

// ─── Auth ───────────────────────────────
const JWT = localStorage.getItem('offsec_jwt');
if (!JWT) { location.href = '/login'; }

async function api(path, opts = {}) {
  const headers = Object.assign(
    { 'Authorization': 'Bearer ' + JWT, 'Content-Type': 'application/json' },
    opts.headers || {}
  );
  const r = await fetch(path, Object.assign({}, opts, { headers }));
  if (r.status === 401) {
    localStorage.removeItem('offsec_jwt');
    location.href = '/login';
    return null;
  }
  return r;
}

// ─── Matrix rain ────────────────────────
(function () {
  const cvs = document.getElementById('matrix');
  const ctx = cvs.getContext('2d');
  function R() { cvs.width = innerWidth; cvs.height = innerHeight; }
  R(); addEventListener('resize', R);
  const ch = 'アイウエオ01ABCDEF<>{}[]/\\#@!*+=';
  const cols = Math.floor(cvs.width / 14);
  const drops = Array(cols).fill(1);
  setInterval(() => {
    ctx.fillStyle = 'rgba(5,10,12,0.06)';
    ctx.fillRect(0, 0, cvs.width, cvs.height);
    ctx.fillStyle = '#00ff9c';
    ctx.font = '13px monospace';
    for (let i = 0; i < drops.length; i++) {
      ctx.fillText(ch[Math.floor(Math.random() * ch.length)], i * 14, drops[i] * 14);
      if (drops[i] * 14 > cvs.height && Math.random() > 0.975) drops[i] = 0;
      drops[i]++;
    }
  }, 60);
})();

// ─── Socket.IO ──────────────────────────
const socket = io({ auth: { token: JWT }, query: { token: JWT } });
const dot = document.getElementById('dot');
const statusText = document.getElementById('status-text');
socket.on('connect', () => {
  dot.classList.remove('off'); dot.classList.add('on');
  statusText.textContent = 'connected';
});
socket.on('disconnect', () => {
  dot.classList.remove('on'); dot.classList.add('off');
  statusText.textContent = 'disconnected';
});
socket.on('log', (d) => {
  const el = document.getElementById('console-output');
  if (el) el.textContent = `[${new Date().toLocaleTimeString()}] [${d.level}] ${d.msg}\n` + el.textContent;
});

// ─── State ──────────────────────────────
let SESSION_ID = localStorage.getItem('offsec_session') || null;
let CURRENT_USER = null;
let IS_STREAMING = false;

// ─── Markdown renderer ──────────────────
function renderMarkdown(text) {
  // Escape HTML first
  let html = text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  // Code blocks with syntax highlighting
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const highlighted = (lang && hljs.getLanguage(lang))
      ? hljs.highlight(code.trim(), { language: lang }).value
      : hljs.highlightAuto(code.trim()).value;
    return `<pre><code class="hljs language-${lang || 'plaintext'}">${highlighted}</code></pre>`;
  });

  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
  // Line breaks
  html = html.replace(/\n/g, '<br>');
  return html;
}

// ─── Message builder ────────────────────
function appendMsg(role, content, meta) {
  const wrap = document.createElement('div');
  wrap.className = 'msg ' + role;

  const body = document.createElement('div');
  body.className = 'msg-body';
  body.innerHTML = renderMarkdown(content);
  wrap.appendChild(body);

  if (meta) {
    const m = document.createElement('div');
    m.className = 'meta';
    m.textContent = meta;
    wrap.appendChild(m);
  }

  // Copy button for assistant messages
  if (role === 'assistant') {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'copy';
    btn.onclick = () => {
      navigator.clipboard.writeText(content).then(() => {
        btn.textContent = 'copied!';
        setTimeout(() => { btn.textContent = 'copy'; }, 1500);
      });
    };
    wrap.appendChild(btn);
  }

  const list = document.getElementById('messages');
  list.appendChild(wrap);
  list.scrollTop = list.scrollHeight;
  return body; // return body for streaming updates
}

// Create a streaming message bubble (returns updater fn)
function createStreamingMsg() {
  const wrap = document.createElement('div');
  wrap.className = 'msg assistant streaming';

  const body = document.createElement('div');
  body.className = 'msg-body';
  wrap.appendChild(body);

  const meta = document.createElement('div');
  meta.className = 'meta';
  meta.textContent = 'streaming…';
  wrap.appendChild(meta);

  const list = document.getElementById('messages');
  list.appendChild(wrap);
  list.scrollTop = list.scrollHeight;

  let fullText = '';

  return {
    append(token) {
      fullText += token;
      body.innerHTML = renderMarkdown(fullText);
      list.scrollTop = list.scrollHeight;
    },
    finish(metaText, rawContent) {
      wrap.classList.remove('streaming');
      meta.textContent = metaText;

      // Add copy button
      const btn = document.createElement('button');
      btn.className = 'copy-btn';
      btn.textContent = 'copy';
      btn.onclick = () => {
        navigator.clipboard.writeText(rawContent || fullText).then(() => {
          btn.textContent = 'copied!';
          setTimeout(() => { btn.textContent = 'copy'; }, 1500);
        });
      };
      wrap.appendChild(btn);
    },
  };
}

// ─── Streaming chat submit ───────────────
document.getElementById('chat-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  if (IS_STREAMING) return;

  const prompt = document.getElementById('prompt').value.trim();
  if (!prompt) return;
  const prefer = document.getElementById('prefer').value || null;
  const target = document.getElementById('target').value.trim() || null;

  appendMsg('user', prompt);
  document.getElementById('prompt').value = '';

  const thinking = document.getElementById('thinking');
  thinking.classList.remove('hidden');
  document.getElementById('thinking-text').textContent =
    `routing… ${prefer ? '[' + prefer + ']' : '[auto]'}`;

  IS_STREAMING = true;
  document.getElementById('send-btn').disabled = true;

  let streamingMsg = null;
  let metaInfo = {};
  let fullContent = '';

  try {
    const r = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Authorization': 'Bearer ' + JWT, 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, session_id: SESSION_ID, prefer, target }),
    });

    if (!r.ok || !r.body) {
      const err = await r.json().catch(() => ({ error: 'stream failed' }));
      thinking.classList.add('hidden');
      appendMsg('assistant', `[!] ${err.error || 'error'}`);
      return;
    }

    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // keep incomplete line

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();
        if (data === '[DONE]') break;

        let chunk;
        try { chunk = JSON.parse(data); } catch { continue; }

        if (chunk.type === 'meta') {
          thinking.classList.add('hidden');
          metaInfo = chunk;
          SESSION_ID = chunk.session_id;
          localStorage.setItem('offsec_session', SESSION_ID);
          streamingMsg = createStreamingMsg();
        } else if (chunk.type === 'token') {
          fullContent += chunk.text;
          if (streamingMsg) streamingMsg.append(chunk.text);
        } else if (chunk.type === 'done') {
          const elapsed = chunk.elapsed_ms ? `${chunk.elapsed_ms}ms` : '';
          if (streamingMsg) {
            streamingMsg.finish(
              `via ${metaInfo.provider} (${metaInfo.model}) · ${metaInfo.task_type} · ${elapsed}`,
              fullContent
            );
          }
          refreshSessions();
        } else if (chunk.type === 'error') {
          thinking.classList.add('hidden');
          if (streamingMsg) {
            streamingMsg.finish('error', '');
          } else {
            appendMsg('assistant', `[!] ${chunk.error}`);
          }
        }
      }
    }
  } catch (err) {
    thinking.classList.add('hidden');
    appendMsg('assistant', '[!] network error: ' + err.message);
  } finally {
    thinking.classList.add('hidden');
    IS_STREAMING = false;
    document.getElementById('send-btn').disabled = false;
  }
});

document.getElementById('prompt').addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    document.getElementById('chat-form').requestSubmit();
  }
});

// ─── Sessions ───────────────────────────
async function refreshSessions() {
  try {
    const r = await api('/api/sessions');
    if (!r) return;
    const sessions = await r.json();
    const list = document.getElementById('session-list');
    list.innerHTML = '';
    sessions.forEach(s => {
      const row = document.createElement('div');
      row.className = 'provider-row session-row' + (s.id === SESSION_ID ? ' active-session' : '');
      row.style.cursor = 'pointer';
      row.title = s.title;
      row.innerHTML = `<span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px;">${s.title || 'Untitled'}</span>`;
      row.onclick = () => loadSession(s.id, s.title);
      list.appendChild(row);
    });
  } catch (e) { /* silent */ }
}

async function loadSession(sid, title) {
  SESSION_ID = sid;
  localStorage.setItem('offsec_session', sid);
  const r = await api(`/api/sessions/${sid}`);
  if (!r) return;
  const data = await r.json();
  const list = document.getElementById('messages');
  list.innerHTML = '';
  (data.messages || []).forEach(m => appendMsg(m.role, m.content));
  refreshSessions();
}

document.getElementById('new-chat-btn').addEventListener('click', () => {
  SESSION_ID = null;
  localStorage.removeItem('offsec_session');
  document.getElementById('messages').innerHTML = '';
  refreshSessions();
});

// ─── Boot ───────────────────────────────
async function boot() {
  // Identity
  try {
    const meR = await api('/api/auth/me');
    if (!meR) return;
    CURRENT_USER = (await meR.json()).user;
  } catch (e) { console.warn('auth/me:', e); }

  // LLMs
  try {
    const llm = await (await api('/api/llm/status')).json();
    const llmList = document.getElementById('llm-list');
    const prefer = document.getElementById('prefer');
    llmList.innerHTML = '';
    for (const [name, ok] of Object.entries(llm.all_keys)) {
      const row = document.createElement('div');
      row.className = 'provider-row';
      row.innerHTML = `<span>${name}</span><span class="${ok ? 'ok' : 'ko'}">${ok ? '✔' : '✘'}</span>`;
      llmList.appendChild(row);
      if (ok) {
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name;
        prefer.appendChild(opt);
      }
    }
    document.getElementById('provider-info').textContent =
      `${(CURRENT_USER && CURRENT_USER.email) || 'user'} · ${llm.configured.length} LLMs`;
  } catch (e) { console.warn('llm/status:', e); }

  // Intel
  try {
    const intel = await (await api('/api/intel/status')).json();
    const intelList = document.getElementById('intel-list');
    const intelProv = document.getElementById('intel-provider');
    intelList.innerHTML = '';
    for (const [name, ok] of Object.entries(intel)) {
      const row = document.createElement('div');
      row.className = 'provider-row';
      row.innerHTML = `<span>${name}</span><span class="${ok ? 'ok' : 'ko'}">${ok ? '✔' : '✘'}</span>`;
      intelList.appendChild(row);
      if (ok && INTEL_ACTIONS[name]) {
        const opt = document.createElement('option');
        opt.value = name; opt.textContent = name;
        intelProv.appendChild(opt);
      }
    }
    updateIntelActions();
    intelProv.addEventListener('change', updateIntelActions);
  } catch (e) { console.warn('intel/status:', e); }

  // Scope
  try {
    const scope = await (await api('/api/scope')).json();
    document.getElementById('scope-info').innerHTML =
      `mode: <b>${scope.mode}</b><br>engagement: ${scope.current || '<i>none</i>'}`;
  } catch (e) { document.getElementById('scope-info').textContent = 'unavailable'; }

  // Quotas
  try {
    const q = await (await api('/api/quotas')).json();
    document.getElementById('quotas').innerHTML =
      Object.entries(q).map(([k, v]) => `${k}: ${v.used}/${v.limit}`).join('<br>') || '<i>no usage yet</i>';
  } catch (e) { document.getElementById('quotas').textContent = '—'; }

  // Sessions
  await refreshSessions();

  // Restore last session messages
  if (SESSION_ID) {
    try {
      const r = await api(`/api/sessions/${SESSION_ID}`);
      if (r) {
        const data = await r.json();
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(m => appendMsg(m.role, m.content));
        }
      }
    } catch (e) { /* silent */ }
  }
}

// ─── Intel tab ──────────────────────────
const INTEL_ACTIONS = {
  shodan:     ['host', 'search', 'info', 'myip'],
  virustotal: ['ip', 'domain', 'hash', 'url_scan'],
  otx:        ['ip', 'domain', 'hash', 'pulses'],
  abuseipdb:  ['check'],
  urlscan:    ['submit', 'result', 'search'],
  ipinfo:     ['lookup', 'myip'],
  cve:        ['lookup', 'search', 'critical'],
  github:     ['code', 'repo', 'commits', 'org'],
  fullhunt:   ['domain', 'subdomains'],
  leakix:     ['host', 'search'],
};

function updateIntelActions() {
  const p = document.getElementById('intel-provider').value;
  const sel = document.getElementById('intel-action');
  sel.innerHTML = '';
  (INTEL_ACTIONS[p] || []).forEach(a => {
    const o = document.createElement('option');
    o.value = a; o.textContent = a;
    sel.appendChild(o);
  });
}

document.getElementById('intel-run').addEventListener('click', async () => {
  const provider = document.getElementById('intel-provider').value;
  const action = document.getElementById('intel-action').value;
  const arg = document.getElementById('intel-arg').value.trim();
  if (!provider || !arg) return;
  const out = document.getElementById('intel-output');
  out.textContent = 'querying…';
  const argMap = {
    host: 'ip', ip: 'ip', domain: 'domain', hash: 'hash_', search: 'query',
    code: 'query', repo: 'query', commits: 'query', org: 'org', lookup: 'cve_id',
    check: 'ip', submit: 'url', result: 'uuid', pulses: 'query',
    critical: 'days', subdomains: 'domain',
  };
  const argName = argMap[action] || 'query';
  let args;
  if (action === 'lookup' && provider === 'ipinfo') args = { ip: arg };
  else if (action === 'critical') args = { days: parseInt(arg) || 7 };
  else args = { [argName]: arg };
  try {
    const r = await api(`/api/intel/${provider}`, {
      method: 'POST',
      body: JSON.stringify({ action, args }),
    });
    const data = await r.json();
    out.textContent = JSON.stringify(data, null, 2);
  } catch (err) { out.textContent = 'error: ' + err; }
});

// ─── Tabs ───────────────────────────────
document.querySelectorAll('.tab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-pane').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('tab-' + t.dataset.tab).classList.add('active');
    if (t.dataset.tab === 'audit') refreshAudit();
  });
});

// ─── Audit ──────────────────────────────
async function refreshAudit() {
  try {
    const r = await api('/api/audit');
    const data = await r.json();
    document.getElementById('audit-output').textContent =
      data.map(e => {
        const ts = typeof e.ts === 'number'
          ? new Date(e.ts * 1000).toLocaleTimeString()
          : new Date(e.ts).toLocaleTimeString();
        const p = typeof e.payload === 'string' ? e.payload : JSON.stringify(e.payload);
        return `[${ts}] ${e.event}  ${p.slice(0, 80)}`;
      }).join('\n');
  } catch (e) { /* silent */ }
}
document.getElementById('audit-refresh').addEventListener('click', refreshAudit);

// ─── Logout ─────────────────────────────
function logout() {
  localStorage.removeItem('offsec_jwt');
  localStorage.removeItem('offsec_refresh');
  localStorage.removeItem('offsec_session');
  location.href = '/login';
}
window.offsecLogout = logout;

boot();


// ─── Intel sub-tabs ──────────────────────
document.querySelectorAll('.itab').forEach(t => {
  t.addEventListener('click', () => {
    document.querySelectorAll('.itab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.itab-pane').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById('itab-' + t.dataset.itab).classList.add('active');
    if (t.dataset.itab === 'history') loadIntelHistory();
  });
});

// ─── Bulk scan ───────────────────────────
document.getElementById('bulk-run').addEventListener('click', runBulkScan);
document.getElementById('bulk-target').addEventListener('keydown', e => {
  if (e.key === 'Enter') runBulkScan();
});

async function runBulkScan() {
  const target = document.getElementById('bulk-target').value.trim();
  if (!target) return;

  const status = document.getElementById('bulk-status');
  const results = document.getElementById('bulk-results');
  status.textContent = `scanning ${target} across all configured intel APIs…`;
  results.innerHTML = '<div class="muted" style="font-size:11px;padding:8px;">running parallel queries…</div>';

  try {
    const r = await api('/api/intel/bulk', {
      method: 'POST',
      body: JSON.stringify({ target }),
    });
    const data = await r.json();
    if (!data.ok) {
      status.textContent = '[!] ' + (data.error || 'scan failed');
      results.innerHTML = '';
      return;
    }

    const count = Object.keys(data.results).length;
    status.textContent = `${count} provider${count !== 1 ? 's' : ''} returned results for ${target} (${data.type})`;
    results.innerHTML = '';

    if (count === 0) {
      results.innerHTML = '<div class="muted" style="padding:8px;font-size:11px;">No configured intel APIs matched this target type.</div>';
      return;
    }

    for (const [provider, result] of Object.entries(data.results)) {
      results.appendChild(buildCard(provider, result, target, data.type));
    }
  } catch (e) {
    status.textContent = '[!] network error: ' + e.message;
    results.innerHTML = '';
  }
}

function buildCard(provider, result, target, targetType) {
  const card = document.createElement('div');
  card.className = 'intel-card';

  const ok = result.ok;
  const summary = ok ? summariseResult(provider, result.data) : result.error;

  card.innerHTML = `
    <div class="intel-card-header">
      <span class="intel-provider-name">${provider.toUpperCase()}</span>
      <span class="intel-card-status ${ok ? 'ok' : 'ko'}">${ok ? '✔' : '✘ error'}</span>
    </div>
    <div class="intel-card-summary">${summary}</div>
    <div class="intel-card-actions">
      <button class="btn-sm toggle-raw">show raw</button>
      ${ok ? `<button class="btn-sm send-ai-btn">send to AI ▶</button>` : ''}
    </div>
    <pre class="intel-card-raw hidden">${ok ? JSON.stringify(result.data, null, 2) : result.error}</pre>
  `;

  card.querySelector('.toggle-raw').addEventListener('click', (e) => {
    const pre = card.querySelector('.intel-card-raw');
    const btn = e.target;
    pre.classList.toggle('hidden');
    btn.textContent = pre.classList.contains('hidden') ? 'show raw' : 'hide raw';
  });

  if (ok) {
    card.querySelector('.send-ai-btn').addEventListener('click', () => {
      sendIntelToAI(provider, target, targetType, result.data);
    });
  }

  return card;
}

function summariseResult(provider, data) {
  if (!data) return '<span class="muted">no data</span>';
  try {
    switch (provider) {
      case 'shodan': {
        const ports = (data.ports || []).join(', ') || 'none';
        const org = data.org || data.isp || '—';
        const country = data.country_name || '—';
        return `<b>Org:</b> ${org} · <b>Country:</b> ${country} · <b>Ports:</b> ${ports}`;
      }
      case 'virustotal': {
        const stats = data.data?.attributes?.last_analysis_stats || data.attributes?.last_analysis_stats || {};
        const mal = stats.malicious || 0;
        const total = Object.values(stats).reduce((a, b) => a + b, 0) || '?';
        const rep = data.data?.attributes?.reputation ?? data.attributes?.reputation ?? '—';
        return `<b>Malicious:</b> ${mal}/${total} · <b>Reputation:</b> ${rep}`;
      }
      case 'abuseipdb': {
        const d = data.data || data;
        const score = d.abuseConfidenceScore ?? '—';
        const reports = d.totalReports ?? '—';
        const country = d.countryCode || '—';
        return `<b>Abuse score:</b> ${score}% · <b>Reports:</b> ${reports} · <b>Country:</b> ${country}`;
      }
      case 'ipinfo': {
        const org = data.org || '—';
        const city = data.city || '—';
        const country = data.country || '—';
        return `<b>Org:</b> ${org} · <b>Location:</b> ${city}, ${country}`;
      }
      case 'otx': {
        const pulses = data.pulse_info?.count ?? data.count ?? '—';
        const rep = data.reputation ?? '—';
        return `<b>Pulses:</b> ${pulses} · <b>Reputation:</b> ${rep}`;
      }
      case 'urlscan': {
        const results = data.results?.length ?? '—';
        return `<b>Scan results:</b> ${results} entries found`;
      }
      case 'fullhunt': {
        const subs = data.hosts?.length ?? data.subdomains?.length ?? '—';
        return `<b>Subdomains/hosts:</b> ${subs} found`;
      }
      case 'leakix': {
        const events = Array.isArray(data) ? data.length : '—';
        return `<b>Leak events:</b> ${events} found`;
      }
      default:
        return `<span class="muted">${JSON.stringify(data).slice(0, 120)}…</span>`;
    }
  } catch {
    return '<span class="muted">parse error — see raw</span>';
  }
}

function sendIntelToAI(provider, target, targetType, data) {
  const prompt = `Analyze this ${provider.toUpperCase()} result for ${target} (${targetType}):\n\n${JSON.stringify(data, null, 2).slice(0, 3000)}\n\nWhat are the key security findings? What should I investigate next?`;
  document.getElementById('prompt').value = prompt;
  document.getElementById('prompt').focus();
  // Switch to chat pane on mobile
  document.getElementById('chat-pane').scrollIntoView({ behavior: 'smooth' });
}

// ─── Intel history ───────────────────────
async function loadIntelHistory() {
  const container = document.getElementById('intel-history-list');
  container.innerHTML = '<div class="muted" style="font-size:11px;padding:4px;">loading…</div>';
  try {
    const r = await api('/api/intel/history');
    const rows = await r.json();
    if (!rows.length) {
      container.innerHTML = '<div class="muted" style="font-size:11px;padding:4px;">No intel history yet.</div>';
      return;
    }
    container.innerHTML = '';
    rows.forEach(e => {
      const ts = typeof e.ts === 'number'
        ? new Date(e.ts * 1000).toLocaleString()
        : new Date(e.ts).toLocaleString();
      const p = typeof e.payload === 'string' ? JSON.parse(e.payload) : e.payload;
      const div = document.createElement('div');
      div.className = 'history-row';
      div.innerHTML = `<span class="muted" style="font-size:10px;">${ts}</span><br>
        <b>${e.event}</b> · ${p.target || (p.args ? JSON.stringify(p.args).slice(0, 60) : '')}`;
      container.appendChild(div);
    });
  } catch (ex) {
    container.innerHTML = `<div class="ko" style="font-size:11px;">${ex.message}</div>`;
  }
}
document.getElementById('intel-history-refresh').addEventListener('click', loadIntelHistory);


// ─── Agents tab ──────────────────────────
async function loadAgents() {
  try {
    const r = await api('/api/agents/list');
    if (!r) return;
    const agents = await r.json();
    const sel = document.getElementById('agent-select');
    sel.innerHTML = '';
    agents.forEach(a => {
      const opt = document.createElement('option');
      opt.value = a.name;
      opt.textContent = `${a.name.toUpperCase()} — ${a.description}`;
      sel.appendChild(opt);
    });
  } catch (e) { console.warn('agents/list:', e); }
}

document.getElementById('agent-run').addEventListener('click', async () => {
  const task = document.getElementById('agent-task').value.trim();
  if (!task) return;
  const agent = document.getElementById('agent-select').value;
  const status = document.getElementById('agent-status');
  const stepsEl = document.getElementById('agent-steps');
  const resultEl = document.getElementById('agent-result');

  status.textContent = `Running ${agent} agent…`;
  stepsEl.innerHTML = '';
  resultEl.innerHTML = '';
  document.getElementById('agent-run').disabled = true;

  try {
    const r = await api('/api/agents/run', {
      method: 'POST',
      body: JSON.stringify({ task, agent }),
    });
    const data = await r.json();

    // Show steps
    (data.steps || []).forEach(s => {
      const div = document.createElement('div');
      div.className = 'agent-step';
      div.innerHTML = `<span class="step-name">${s.step}</span> ` +
        Object.entries(s)
          .filter(([k]) => k !== 'step')
          .map(([k, v]) => `<span class="muted">${k}:</span> <b>${String(v).slice(0, 60)}</b>`)
          .join(' · ');
      stepsEl.appendChild(div);
    });

    if (data.ok) {
      status.textContent = `✔ ${data.agent} agent completed`;
      // Render result in a card
      resultEl.innerHTML = `
        <div class="agent-result-card">
          <div class="agent-result-header">
            <span>${(data.agent || 'agent').toUpperCase()} RESULT</span>
            <button class="btn-sm" onclick="sendAgentToChat('${encodeURIComponent(data.result || '')}')">send to chat ▶</button>
          </div>
          <div class="agent-result-body">${renderMarkdown(data.result || '')}</div>
        </div>`;
    } else {
      status.textContent = `✘ Error: ${data.error || 'unknown'}`;
    }
  } catch (e) {
    status.textContent = `✘ Network error: ${e.message}`;
  } finally {
    document.getElementById('agent-run').disabled = false;
  }
});

function sendAgentToChat(encoded) {
  const text = decodeURIComponent(encoded);
  // Switch to chat tab view and pre-fill a summary prompt
  document.getElementById('prompt').value =
    `Summarize and expand on this agent finding:\n\n${text.slice(0, 1000)}`;
  document.getElementById('prompt').focus();
}

// Load agents list when AGENTS tab clicked
document.querySelectorAll('.tab').forEach(t => {
  if (t.dataset.tab === 'agents') {
    t.addEventListener('click', loadAgents);
  }
});
